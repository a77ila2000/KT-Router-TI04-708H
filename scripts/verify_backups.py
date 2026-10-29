"""Verify U-Boot CRC + PC SHA for all chunks; create OWN private install receipt."""
import argparse
import hashlib
import json
from pathlib import Path
import zlib
from patch_nor_env import OFFSET, SIZE, entries

NOR_PARTS = [('SBL1', 0, 0x40000), ('MIBIB', 0x40000, 0x20000),
             ('QSEE', 0x60000, 0x60000), ('CDT', 0xC0000, 0x10000),
             ('DDRPARAMS', 0xD0000, 0x10000), ('APPSBLENV', 0xE0000, 0x10000),
             ('APPSBL', 0xF0000, 0x80000), ('ART', 0x170000, 0x10000)]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_chunks(folder):
    expected = {f'nand-{kind}-{n * 1048576:08x}.bin': size
                for kind, size in [('main', 1048576), ('raw', 1081344)] for n in range(128)}
    if {p.name for p in folder.glob('nand-*.bin')} != expected.keys() or any(folder.glob('*.part')):
        raise ValueError('Incomplete/unexpected chunk set or partial transfers')
    crc = json.loads((folder / 'uboot-crc.json').read_text(encoding='utf-8-sig'))
    transfer = [json.loads(x) for x in (folder / 'manifest.jsonl').read_text().splitlines()]
    for records in (crc, transfer):
        if len(records) != 256 or {r['file'] for r in records} != expected.keys():
            raise ValueError('Incomplete/duplicate CRC or TFTP manifest')
        for r in records:
            data = (folder / r['file']).read_bytes()
            if len(data) != expected[r['file']] or r['bytes'] != len(data) or r['sha256'] != sha(data):
                raise ValueError('Chunk size/SHA mismatch: ' + r['file'])
            if records is crc and r['crc32'] != f'{zlib.crc32(data):08x}':
                raise ValueError('U-Boot-to-PC CRC mismatch: ' + r['file'])
    return expected


def verify(folder, nor_path, output):
    nor = nor_path.read_bytes()
    if len(nor) != 2097152 or dict(entries(nor[OFFSET:OFFSET + SIZE])).get(b'bootdelay') != b'2012':
        raise ValueError('Use YOUR verified programmer readback after ESC2012 patch')
    check_chunks(folder)
    output.mkdir(parents=True, exist_ok=False)
    totals = {}
    tail = hashlib.sha256()
    for kind in ('main', 'raw'):
        digest = hashlib.sha256()
        target = output / ('nand-main-ecc.bin' if kind == 'main' else 'nand-raw-oob.bin')
        with target.open('xb') as stream:
            for n in range(128):
                block = (folder / f'nand-{kind}-{n * 1048576:08x}.bin').read_bytes()
                stream.write(block); digest.update(block)
                if kind == 'main' and n >= 32:
                    tail.update(block)
        # Re-read assembled output, independently of streaming assembly.
        with target.open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != digest.hexdigest():
            raise ValueError('Assembled backup readback mismatch')
        totals[kind] = {'file': target.name, 'bytes': target.stat().st_size, 'sha256': actual}
    receipt = {'format': 'TI04_BACKUP_V1', 'main_ecc_bytes': totals['main']['bytes'],
               'raw_oob_bytes': totals['raw']['bytes'], 'backups': totals,
               'all_chunk_crc_verified': True, 'nand_tail_sha256': tail.hexdigest(),
               'nor_full_sha256': sha(nor),
               'nor': [{'name': n, 'offset': o, 'bytes': s, 'sha256': sha(nor[o:o+s])}
                       for n, o, s in NOR_PARTS]}
    (output / 'own-backup-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: 256 chunk CRC/SHA checks, assembled ECC+raw backups, own NOR receipt.')
    print('Keep all backups and receipt PRIVATE, on another storage device too. Restore not tested.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--chunks', type=Path, required=True)
    p.add_argument('--nor-readback', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    verify(a.chunks, a.nor_readback, a.out)
