"""Independent Linux FIT/CPIO/rootfs/DTB audit of the public build."""
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from verify_release import verify


def get(file, node, prop, kind='s'):
    return subprocess.check_output(['fdtget', '-t', kind, str(file), node, prop]).decode().strip()


def cpio(data):
    result = {}; offset = 0
    while True:
        assert data[offset:offset+6] == b'070701'
        values = [int(data[i:i+8], 16) for i in range(offset+6, offset+110, 8)]
        offset += 110
        name = data[offset:offset+values[11]-1].decode()
        assert data[offset+values[11]-1] == 0
        offset = (offset + values[11] + 3) & ~3
        payload = data[offset:offset+values[6]]
        assert len(payload) == values[6]
        offset = (offset + values[6] + 3) & ~3
        assert name not in result and not name.startswith('/') and '..' not in Path(name).parts
        result[name] = (values[1], payload)
        if name == 'TRAILER!!!': break
    assert not any(data[offset:])
    return result


def audit(folder):
    verify(folder)
    # Read UBI independently of build_release.py, including volume-table CRCs.
    manifest = json.loads((folder/'manifest.json').read_text())
    ubi = (folder/'ti04-25.12.6-first32m.ubi').read_bytes()
    payloads = {0: {}, 1: {}}
    tables = []
    for offset in range(0, len(ubi), 131072):
        ec = ubi[offset:offset+64]; vid = ubi[offset+2048:offset+2112]
        assert ec[:4] == b'UBI#' and vid[:4] == b'UBI!'
        assert struct.unpack_from('>II', ec, 16) == (2048, 4096)
        for h in (ec, vid): assert zlib.crc32(h[:60]) ^ 0xFFFFFFFF == int.from_bytes(h[60:], 'big')
        volume, logical = struct.unpack_from('>II', vid, 8)
        data = ubi[offset+4096:offset+131072]
        if volume in payloads:
            assert logical not in payloads[volume]
            payloads[volume][logical] = data
        elif volume == 0x7FFFEFFF:
            tables.append(data[:516])
    assert len(tables) == 2 and tables[0] == tables[1]
    for n, name in enumerate(('kernel', 'rootfs', 'rootfs_data')):
        r = tables[0][n*172:(n+1)*172]
        assert zlib.crc32(r[:168]) ^ 0xFFFFFFFF == int.from_bytes(r[168:], 'big')
        assert r[16:16+int.from_bytes(r[14:16], 'big')].decode() == name
        assert r[12] == 1 and r[144] == (1 if n == 2 else 0)
        if n < 2:
            wanted = manifest['files'][name]
            result = b''.join(payloads[n][i] for i in range(len(payloads[n])))[:wanted['bytes']]
            assert hashlib.sha256(result).hexdigest() == wanted['sha256']
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        packed = None
        for name, ram in [('kernel-stock-uboot.itb', False), ('ti04-25.12.6-ram-installer.itb', True)]:
            fit = folder / name
            assert get(fit, '/images/kernel-1', 'compression') == 'none'
            assert get(fit, '/images/kernel-1', 'load', 'x') == '80208000'
            for config in ('config@1', 'config@5', 'config@ap.dk01.1-c2'):
                assert get(fit, '/configurations/'+config, 'kernel') == 'kernel-1'
                if ram: assert get(fit, '/configurations/'+config, 'ramdisk') == 'ramdisk-1'
            for index, node in enumerate(['kernel-1', 'fdt-1'] + (['ramdisk-1'] if ram else [])):
                output = temp / f'{ram}-{index}'
                subprocess.run(['dumpimage', '-T', 'flat_dt', '-p', str(index), '-o', str(output), str(fit)], check=True, stdout=subprocess.DEVNULL)
                data = output.read_bytes()
                for h, expected in [('hash@1', zlib.crc32(data).to_bytes(4, 'big')), ('hash@2', hashlib.sha1(data).digest())]:
                    assert bytes(int(x, 16) for x in get(fit, '/images/'+node+'/'+h, 'value', 'bx').split()) == expected
                if node == 'kernel-1':
                    assert hashlib.sha256(data).hexdigest() == '05767f8cece8c5106458df3293534f1ae0b063ab57ae6241678ea91c89301d97'
                if node == 'fdt-1':
                    dts = subprocess.check_output(['dtc', '-q', '-I', 'dtb', '-O', 'dts', str(output)]).decode()
                    assert 'local-mac-address' not in dts and 'mac-address =' not in dts and 'serial-number' not in dts
                    assert dts.count('read-only;') == 9
                    assert get(output, '/soc/spi@78b5000/spi-nand@1/partitions/partition@0', 'reg', 'x') == '0 2000000'
                    assert get(output, '/soc/spi@78b5000/spi-nand@1/partitions/partition@0', 'label') == ('install-target' if ram else 'rootfs')
                    assert get(output, '/soc/mdio@90000/ethernet-phy-package@0', 'compatible') == 'qcom,qca8075-package'
                    assert get(output, '/keys', 'status') == 'disabled'
                if node == 'ramdisk-1': packed = cpio(data)
        assert packed and stat.S_ISCHR(packed['dev/console'][0])
        assert packed['etc/ti04-installer-release'][1] == b'25.12.6-ti04-r1\n'
        assert packed['etc/ti04-release-manifest.json'][1] == (folder/'manifest.json').read_bytes()
        assert b'Persistent operation disabled' in packed['sbin/mount_root'][1]
        assert b'boot_hook_add' not in packed['lib/preinit/80_mount_root'][1]
        assert b'export INITRAMFS=1' in packed['init'][1]
        extracted = temp / 'squashfs'
        subprocess.run(['unsquashfs', '-no-progress', '-d', str(extracted), str(folder/'root.squashfs')], check=True, stdout=subprocess.DEVNULL)
        assert not list((extracted/'etc/dropbear').iterdir())
        assert b'root::' in (extracted/'etc/shadow').read_bytes()
        assert 'boot_hook_add preinit_main do_mount_root' in (extracted/'lib/preinit/80_mount_root').read_text()
        assert (extracted/'www/luci-static/argon').is_dir()
        assert (extracted/'usr/sbin/ti04-phy-led').read_bytes()[:4] == b'\x7fELF'
        wireless = (extracted/'etc/config/wireless').read_text()
        assert wireless.count("option disabled '1'") == 2 and 'wifi-iface' not in wireless and 'key ' not in wireless
        assert "option lang 'ko'" in (extracted/'etc/config/luci').read_text()
        menu = json.loads((extracted/'usr/share/luci/menu.d/luci-mod-network.json').read_text())
        assert menu['admin/network/wireless']['action']['path'] == 'network/ti04-wireless-bands'
        for path in extracted.rglob('*'):
            if path.is_symlink() or not path.is_file(): continue
            data = path.read_bytes()
            # Crypto binaries contain PEM marker literals; reject actual encoded keys.
            assert not re.search(rb'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=\r\n]{80,}-----END', data), str(path.relative_to(extracted))
            assert path.name not in ('authorized_keys', 'dropbear_rsa_host_key', 'dropbear_ed25519_host_key', 'uhttpd.key')
        for name in ('etc/config/network', 'etc/config/wireless', 'etc/shadow'):
            assert packed[name][1] == (extracted/name).read_bytes()
        print('PASS: extracted FIT hashes, official kernel identity, readonly scope, CPIO, clean credentials/MAC, defaults/UI.')


if __name__ == '__main__':
    audit(Path(sys.argv[1]))
