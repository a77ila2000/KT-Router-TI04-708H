import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
from patch_nor_env import entries, patch, OFFSET, SIZE, NOR_SIZE
from verify_backups import check_chunks, sha


def synthetic_nor(extra=b''):
    payload = b'baudrate=115200\0bootdelay=0\0private=KEEP\0\0'
    payload = (payload + extra).ljust(SIZE - 4, b'\0')
    data = bytearray(b'\xff' * NOR_SIZE)
    data[OFFSET:OFFSET + SIZE] = struct.pack('<I', zlib.crc32(payload)) + payload
    data[0xF0000:0xF0010] = b'U-Boot 2012.07\0\0'
    return bytes(data)


class PublicTools(unittest.TestCase):
    def test_nor_only_bootdelay_and_crc_in_single_sector(self):
        before = synthetic_nor()
        after = patch(before)
        self.assertEqual(before[:OFFSET], after[:OFFSET])
        self.assertEqual(before[OFFSET + 4096:], after[OFFSET + 4096:])
        old, new = entries(before[OFFSET:OFFSET+SIZE]), entries(after[OFFSET:OFFSET+SIZE])
        self.assertEqual([(k, v) for k, v in old if k != b'bootdelay'], [(k, v) for k, v in new if k != b'bootdelay'])
        self.assertEqual(dict(new)[b'bootdelay'], b'2012')
        with self.assertRaises(ValueError): patch(after)

    def test_nor_crc_unknown_tail_and_wrong_bootloader_fail(self):
        for offset in (OFFSET, OFFSET + 25, 0xF0000):
            data = bytearray(synthetic_nor()); data[offset] ^= 0x20
            with self.assertRaises(ValueError): patch(data)
        with self.assertRaises(ValueError): patch(synthetic_nor(b'unknown'))
        with self.assertRaises(ValueError): patch(b'\xff' * NOR_SIZE)

    def test_complete_backup_crc_and_tftp_sha_crosscheck(self):
        # Full production geometry, deterministic test-only bytes; no device access.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); crc = []; transfers = []
            for kind, size in [('main', 1048576), ('raw', 1081344)]:
                block = bytes([73 if kind == 'main' else 94]) * size
                for n in range(128):
                    name = f'nand-{kind}-{n*1048576:08x}.bin'
                    (root/name).write_bytes(block)
                    record = {'file': name, 'bytes': size, 'sha256': sha(block), 'crc32': f'{zlib.crc32(block):08x}'}
                    crc.append(record)
                    transfers.append({k: v for k, v in record.items() if k != 'crc32'})
            (root/'uboot-crc.json').write_text(json.dumps(crc))
            (root/'manifest.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in transfers))
            self.assertEqual(len(check_chunks(root)), 256)
            crc[0]['crc32'] = '00000000'
            (root/'uboot-crc.json').write_text(json.dumps(crc))
            with self.assertRaisesRegex(ValueError, 'CRC mismatch'): check_chunks(root)
            (root/'interrupted.part').write_bytes(b'')
            with self.assertRaisesRegex(ValueError, 'partial'): check_chunks(root)


if __name__ == '__main__': unittest.main()
