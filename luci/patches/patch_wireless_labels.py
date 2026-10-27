"""Patch only the radio badge in the inspected LuCI 25.12 wireless view."""
from pathlib import Path
import sys


def patch(source: str) -> str:
    start = source.index('function render_radio_badge(radioDev)')
    end = source.index('\nfunction buildSVGQRCode(', start)
    old = source[start:end]
    if 'radioDev.getName()' not in old or 'ifacebadge' not in old:
        raise ValueError('Unexpected radio badge implementation; inspect before patching')
    replacement = Path(__file__).with_name('render_radio_badge.js').read_text(encoding='utf-8').strip()
    return source[:start] + replacement + source[end:]


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_wireless_labels.py ORIGINAL.js OUTPUT.js')
    original, output = map(Path, sys.argv[1:])
    if original.resolve() == output.resolve():
        raise SystemExit('Use a separate output file to preserve the original')
    output.write_bytes(patch(original.read_bytes().decode('utf-8')).encode('utf-8'))
