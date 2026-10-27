"""Select a separate wireless view URL while preserving menu permissions."""
import json
from pathlib import Path
import sys

def patch(source):
    menu = json.loads(source)
    action = menu['admin/network/wireless']['action']
    if action != {'type': 'view', 'path': 'network/wireless'}:
        raise ValueError('Unexpected existing wireless route; inspect before changing')
    action['path'] = 'network/ti04-wireless-bands'
    return json.dumps(menu, ensure_ascii=False, indent=2) + '\n'

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit('usage: route_wireless_bands.py ORIGINAL.json OUTPUT.json')
    original, output = map(Path, sys.argv[1:])
    if original.resolve() == output.resolve():
        raise SystemExit('Keep the original in a separate file')
    output.write_bytes(patch(original.read_text(encoding='utf-8')).encode('utf-8'))
