"""Patch only bootdelay in YOUR verified 2MiB TI04 NOR dump; no hardware access."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import zlib

OFFSET, SIZE, SECTOR, NOR_SIZE = 0xE0000, 0x10000, 0x1000, 0x200000


def sha(data):
    return hashlib.sha256(data).hexdigest()


def entries(block):
    if len(block) != SIZE or struct.unpack_from('<I', block)[0] != zlib.crc32(block[4:]):
        raise ValueError('Environment length/CRC mismatch; unsupported layout')
    payload = block[4:]
    end = payload.find(b'\0\0')
    if end < 0 or any(payload[end + 2:]):
        raise ValueError('Missing terminator or unknown nonzero trailing data')
    result = []
    for item in payload[:end].split(b'\0'):
        key, sep, value = item.partition(b'=')
        if not sep or not re.fullmatch(rb'[A-Za-z_][A-Za-z0-9_.-]*', key):
            raise ValueError('Malformed environment entry')
        result.append((key, value))
    if len(dict(result)) != len(result):
        raise ValueError('Duplicate environment key')
    return result


def patch(image):
    if len(image) != NOR_SIZE or len(set(image)) < 2:
        raise ValueError('Expected a nonblank 2,097,152-byte NOR dump')
    # This layout is supported only with the observed vendor U-Boot family.
    boot = image[0xF0000:0x170000]
    if b'U-Boot 2012.07' not in boot:
        raise ValueError('Vendor U-Boot 2012.07 signature missing')
    old = image[OFFSET:OFFSET + SIZE]
    values = entries(old)
    if dict(values).get(b'bootdelay') != b'0':
        raise ValueError('Expected bootdelay=0; already patched/other modes need inspection')
    new_values = [(k, b'2012' if k == b'bootdelay' else v) for k, v in values]
    payload = b'\0'.join(k + b'=' + v for k, v in new_values) + b'\0\0'
    if len(payload) > SIZE - 4:
        raise ValueError('Environment overflow')
    payload = payload.ljust(SIZE - 4, b'\0')
    new = struct.pack('<I', zlib.crc32(payload)) + payload
    if entries(new) != new_values or new[SECTOR:] != old[SECTOR:]:
        raise ValueError('Change would exceed first environment 4KiB; stop')
    candidate = image[:OFFSET] + new[:SECTOR] + image[OFFSET + SECTOR:]
    assert candidate[:OFFSET] == image[:OFFSET]
    assert candidate[OFFSET + SECTOR:] == image[OFFSET + SECTOR:]
    return candidate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--read2', required=True, type=Path)
    p.add_argument('--read3', required=True, type=Path)
    p.add_argument('--out', type=Path)
    p.add_argument('--check-candidate', type=Path, help='Offline check of an existing candidate')
    p.add_argument('--verify-readback', type=Path,
                   help='Compare programmer full readback with generated candidate')
    a = p.parse_args()
    paths = [a.source, a.read2, a.read3]
    if any(os.path.samefile(path, previous) for i, path in enumerate(paths) for previous in paths[:i]):
        p.error('Use three separate independent programmer reads')
    original = a.source.read_bytes()
    if any(x.read_bytes() != original for x in paths[1:]):
        p.error('Independent NOR reads differ')
    candidate = patch(original)
    if a.check_candidate:
        if a.check_candidate.read_bytes() != candidate:
            raise SystemExit('FAIL: candidate is not the exact bootdelay-only patch of own source')
        print('PASS: candidate semantics, CRC and single-sector boundary')
        return
    if a.verify_readback:
        if a.verify_readback.read_bytes() != candidate:
            raise SystemExit('FAIL: full NOR readback mismatch; do not power router')
        print('PASS: full 2MiB readback equals own candidate; outside 4KiB unchanged; CRC valid')
        return
    if not a.out:
        p.error('--out required unless verifying')
    a.out.mkdir(parents=True, exist_ok=False)
    files = {'own-nor-esc2012.bin': candidate,
             'own-env-sector-e0000-1000.bin': candidate[OFFSET:OFFSET + SECTOR],
             'original-env-sector-e0000-1000.bin': original[OFFSET:OFFSET + SECTOR]}
    for name, data in files.items():
        (a.out / name).write_bytes(data)
    report = {'source_sha256': sha(original), 'change': 'bootdelay=0 -> 2012',
              'write_offset': OFFSET, 'write_bytes': SECTOR,
              'changed_bytes': sum(x != y for x, y in zip(original, candidate)),
              'outside_write_sector_unchanged': True,
              'files': {n: {'bytes': len(d), 'sha256': sha(d)} for n, d in files.items()}}
    (a.out / 'own-patch-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print('Prepared YOUR candidate. Write only 4KiB at 0xE0000; verify whole NOR before power-on.')
    print('Private dumps/candidates/reports must not be uploaded or used on another router.')


if __name__ == '__main__':
    main()
