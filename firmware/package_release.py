"""Package only Git-index source plus explicit validated public artifacts (Linux)."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import zipfile

REPO = Path(__file__).resolve().parents[1]
CORE = ['ti04-25.12.6-ram-installer.itb', 'ti04-25.12.6-first32m.ubi', 'kernel-stock-uboot.itb',
        'root.squashfs', 'manifest.json', 'RAM_BOOT.json', 'SHA256SUMS', 'packages.txt']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def add(archive, name, data):
    entry = zipfile.ZipInfo(name, date_time=(2026, 10, 29, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o100644 << 16
    archive.writestr(entry, data)


def package(artifacts, packages, output):
    subprocess.run(['python3', str(REPO/'firmware/verify_images.py'), str(artifacts)], check=True)
    output.mkdir(parents=True, exist_ok=False)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=REPO).decode().split('\0')
    assert 'scripts/run_uart_experiment.ps1' not in tracked and 'scripts/generate_ps1.py' not in tracked
    with zipfile.ZipFile(output/'ti04-openwrt-25.12.6-r1-install.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for name in filter(None, tracked):
            assert not name.startswith(('dump/', 'extracted/', 'openwrt/')) or name.endswith('/.gitkeep')
            data = subprocess.check_output(['git', 'show', ':'+name], cwd=REPO)
            add(z, name, data)
        for name in CORE:
            add(z, name, (artifacts/name).read_bytes())
    for name in ('ti04-25.12.6-ram-installer.itb', 'ti04-25.12.6-first32m.ubi', 'manifest.json', 'RAM_BOOT.json'):
        (output/name).write_bytes((artifacts/name).read_bytes())
    apks = sorted(packages.glob('*.apk'))
    assert apks
    checks = ''.join(sha(p)+'  packages/'+p.name+'\n' for p in apks)
    with zipfile.ZipFile(output/'ti04-25.12.6-package-cache.zip', 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for path in apks: add(z, 'packages/'+path.name, path.read_bytes())
        add(z, 'PACKAGE_SHA256SUMS', checks.encode())
        add(z, 'README.txt', b'Public APK build inputs only. No private signing key. See firmware/BUILD.md in the install package.\n')
    (output/'SHA256SUMS').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(output.iterdir())))
    for path in output.glob('*.zip'):
        with zipfile.ZipFile(path) as z: assert z.testzip() is None
    print('Packaged and CRC-checked install ZIP, build cache, images, metadata, checksums.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifacts', type=Path, required=True)
    p.add_argument('--packages', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    package(a.artifacts, a.packages, a.out)
