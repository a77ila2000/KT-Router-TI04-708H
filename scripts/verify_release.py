"""Cross-platform release checksum check; no device access."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def verify(folder):
    records = (folder / 'SHA256SUMS').read_text().splitlines()
    names = set()
    for record in records:
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)', record)
        if not match or match[2] in names:
            raise ValueError('Malformed/duplicate checksum entry')
        names.add(match[2])
        with (folder / match[2]).open('rb') as stream:
            actual = hashlib.file_digest(stream, 'sha256').hexdigest()
        if actual != match[1]:
            raise ValueError('Checksum mismatch: ' + match[2])
    required = {'manifest.json', 'RAM_BOOT.json', 'ti04-25.12.6-ram-installer.itb', 'ti04-25.12.6-first32m.ubi', 'kernel-stock-uboot.itb', 'root.squashfs'}
    if not required <= names:
        raise ValueError('Missing required release checksums')
    m = json.loads((folder / 'manifest.json').read_text())
    if m['release'] != '25.12.6-ti04-r1' or m['nand']['write_range'] != [0, 33554432]:
        raise ValueError('Wrong release/target scope')
    for f in m['files'].values():
        if f['name'] not in names or (folder / f['name']).stat().st_size != f['bytes']:
            raise ValueError('Manifest/checksum set or length mismatch')
        if hashlib.sha256((folder / f['name']).read_bytes()).hexdigest() != f['sha256']:
            raise ValueError('Manifest SHA mismatch')
    ram = json.loads((folder / 'RAM_BOOT.json').read_text())
    image = folder / 'ti04-25.12.6-ram-installer.itb'
    if ram['sha256'] != hashlib.sha256(image.read_bytes()).hexdigest() or ram['bytes'] != image.stat().st_size:
        raise ValueError('RAM boot metadata mismatch')
    print(f'PASS: {len(names)} checked files; release {m["release"]}; NAND first32MiB only.')
    print('Checksums prove file integrity, not successful installation on your hardware.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path)
    verify(p.parse_args().folder)
