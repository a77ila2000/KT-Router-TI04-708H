"""Patch safety checks with synthetic LuCI fixtures and no device data."""
from pathlib import Path
import importlib.util
import json
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'luci/patches/patch_wireless_labels.py'
spec = importlib.util.spec_from_file_location('wireless_patch', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ROUTE_SCRIPT = SCRIPT.with_name('route_wireless_bands.py')
route_spec = importlib.util.spec_from_file_location('wireless_route', ROUTE_SCRIPT)
route_module = importlib.util.module_from_spec(route_spec)
route_spec.loader.exec_module(route_module)


class WirelessLabelPatchTests(unittest.TestCase):
    def test_preserves_everything_outside_badge_and_is_repeatable(self):
        prefix = "'use strict';\r\n// untouched 한글\r\n"
        old = "function render_radio_badge(radioDev){return E('span',{'class':'ifacebadge'},radioDev.getName());}"
        suffix = '\nfunction buildSVGQRCode(){}\r\nreturn view.extend({});'
        result = module.patch(prefix + old + suffix)
        self.assertTrue(result.startswith(prefix))
        self.assertTrue(result.endswith(suffix))
        self.assertIn('2.4GHz Wi-Fi', result)
        self.assertEqual(module.patch(result), result)

    def test_unknown_view_fails_before_producing_output(self):
        for text in ['return view.extend({});',
                     'function render_radio_badge(radioDev){return 1;}\nfunction buildSVGQRCode(){}']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                module.patch(text)

    def test_route_preserves_menu_permissions_and_other_pages(self):
        original = {'admin/network/wireless': {
            'title': 'Wireless', 'order': 15,
            'action': {'type': 'view', 'path': 'network/wireless'},
            'depends': {'acl': ['luci-mod-network-config'], 'uci': {'wireless': {'@wifi-device': True}}}},
            'admin/network/network': {'action': {'type': 'view', 'path': 'network/interfaces'}}}
        patched = json.loads(route_module.patch(json.dumps(original)))
        self.assertEqual(patched['admin/network/wireless']['action']['path'], 'network/ti04-wireless-bands')
        patched['admin/network/wireless']['action']['path'] = 'network/wireless'
        self.assertEqual(patched, original)

    def test_unexpected_existing_route_is_preserved_by_refusal(self):
        with self.assertRaises(ValueError):
            route_module.patch(json.dumps({'admin/network/wireless': {
                'action': {'type': 'view', 'path': 'network/custom-wireless'}}}))


if __name__ == '__main__':
    unittest.main()
