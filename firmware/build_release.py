"""Linux: repack a CLEAN official 25.12.6 ImageBuilder root for TI04 stock U-Boot.

First run ImageBuilder as documented in BUILD.md. Never use a router backup as input.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import subprocess
import sys
import zlib

RELEASE = '25.12.6-ti04-r1'
KERNEL_SHA = '05767f8cece8c5106458df3293534f1ae0b063ab57ae6241678ea91c89301d97'
EPOCH = '1793232000'
REPO = Path(__file__).resolve().parents[1]


def run(*args, **kw):
    env = {**os.environ, 'SOURCE_DATE_EPOCH': EPOCH}
    if str(args[0]) == 'mksquashfs':
        env.pop('SOURCE_DATE_EPOCH', None)  # Explicit -all-time/-mkfs-time below.
    return subprocess.run(list(map(str, args)), check=True, env=env, **kw)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def putfile(root, name, data, mode=0o644):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data)
    path.chmod(mode)


def clean_root(source, root):
    shutil.copytree(source, root, symlinks=True)
    assert 'boot_hook_add preinit_main do_mount_root' in (root / 'lib/preinit/80_mount_root').read_text()
    assert "DISTRIB_RELEASE='25.12.6'" in (root / 'etc/openwrt_release').read_text()
    # Explicit public defaults, never copy installed-device configurations.
    putfile(root, 'etc/config/network', """config interface 'loopback'
 option device 'lo'
 option proto 'static'
 option ipaddr '127.0.0.1'
 option netmask '255.0.0.0'
config device
 option name 'br-lan'
 option type 'bridge'
 list ports 'lan1'
 list ports 'lan2'
 list ports 'lan3'
 list ports 'lan4'
config interface 'lan'
 option device 'br-lan'
 option proto 'static'
 option ipaddr '192.168.1.1'
 option netmask '255.255.255.0'
config interface 'wan'
 option device 'wan'
 option proto 'dhcp'
""")
    putfile(root, 'etc/config/system', """config system
 option hostname 'TI04-708H'
 option timezone 'KST-9'
 option zonename 'Asia/Seoul'
 option ttylogin '0'
 option log_size '128'
config timeserver 'ntp'
 option enabled '1'
 option enable_server '0'
 list server '0.openwrt.pool.ntp.org'
 list server '1.openwrt.pool.ntp.org'
 list server '2.openwrt.pool.ntp.org'
 list server '3.openwrt.pool.ntp.org'
config led 'led_ti04_wan'
 option name 'WAN link and activity'
 option sysfs 'green:wan'
 option trigger 'netdev'
 option dev 'wan'
 option mode 'link tx rx'
config led 'led_ti04_wlan'
 option name 'Wi-Fi activity'
 option sysfs 'green:wlan'
 option trigger 'none'
""")
    putfile(root, 'etc/config/wireless', """config wifi-device 'radio0'
 option type 'mac80211'
 option path 'platform/soc/a000000.wifi'
 option band '2g'
 option channel '1'
 option htmode 'HT20'
 option country 'KR'
 option disabled '1'
config wifi-device 'radio1'
 option type 'mac80211'
 option path 'platform/soc/a800000.wifi'
 option band '5g'
 option channel '36'
 option htmode 'VHT80'
 option country 'KR'
 option disabled '1'
""")
    putfile(root, 'etc/board.d/02_network', '#!/bin/sh\n. /lib/functions/uci-defaults.sh\nboard_config_update\nucidef_set_interfaces_lan_wan "lan1 lan2 lan3 lan4" "wan"\nboard_config_flush\n', 0o755)
    putfile(root, 'etc/inittab', '::sysinit:/etc/init.d/rcS S boot\n::shutdown:/etc/init.d/rcS K shutdown\nttyMSM0::askfirst:/bin/ash -l\n')
    shadow = root / 'etc/shadow'
    shadow.write_text(re.sub(r'^root:[^:]*:', 'root::', shadow.read_text(), flags=re.M))
    shadow.chmod(0o600)
    # No host identity, admin key, web TLS private key, random seed or sessions.
    for name in ('etc/dropbear', 'root/.ssh'):
        path = root / name
        if path.exists():
            shutil.rmtree(path)
    (root / 'etc/dropbear').mkdir(mode=0o700)
    for name in ('etc/uhttpd.key', 'etc/uhttpd.crt', 'etc/urandom.seed'):
        (root / name).unlink(missing_ok=True)
    for link in (root / 'etc/rc.d').iterdir():
        if re.fullmatch(r'[SK]\d+(bootcount|ubihealthd)', link.name):
            link.unlink()
    assert not (root / 'sbin/mtd').exists() and not (root / 'usr/sbin/fw_setenv').exists()
    platform = root / 'lib/upgrade/platform.sh'
    text = platform.read_text()
    assert 'platform_check_image() {' in text
    platform.write_text(text.replace('platform_check_image() {', 'platform_check_image() {\n echo "TI04 stock U-Boot: use this release RAM installer; generic sysupgrade disabled" >&2\n return 1\n', 1))
    for overlay in (REPO / 'firmware/root', REPO / 'device-settings/root', REPO / 'luci/root'):
        shutil.copytree(overlay, root, dirs_exist_ok=True)
    for path in (root / 'etc/uci-defaults').iterdir():
        if path.name.startswith('98-ti04'):
            path.chmod(0o755)
    for name in ('etc/init.d/ti04-leds', 'usr/sbin/ti04-wifi-led'):
        (root / name).chmod(0o755)
    run('arm-linux-gnueabihf-gcc', '-static', '-O2', '-Wall', '-Wextra', '-Werror',
        '-o', root / 'usr/sbin/ti04-phy-led', REPO / 'device-settings/src/ti04-phy-led.c')
    for name, target in [('S97ti04-leds', '../init.d/ti04-leds'), ('K10ti04-leds', '../init.d/ti04-leds')]:
        (root / 'etc/rc.d' / name).symlink_to(target)
    sys.path.insert(0, str(REPO / 'luci/patches'))
    from patch_wireless_labels import patch as patch_badge
    from route_wireless_bands import patch as patch_menu
    resources = root / 'www/luci-static/resources/view/network'
    (resources / 'ti04-wireless-bands.js').write_text(patch_badge((resources / 'wireless.js').read_text()))
    menu = root / 'usr/share/luci/menu.d/luci-mod-network.json'
    menu.write_text(patch_menu(menu.read_text()))
    luci = root / 'etc/config/luci'
    text = luci.read_text()
    text = re.sub(r'option lang \S+', "option lang 'ko'", text)
    text = re.sub(r'option mediaurlbase \S+', "option mediaurlbase '/luci-static/argon'", text)
    luci.write_text(text)
    putfile(root, 'etc/ti04-port-version', RELEASE + '\n')


def cpio(root):
    archive = bytearray()
    count = 0
    def add(name, mode, data=b'', major=0, minor=0):
        nonlocal count
        count += 1
        filename = name.encode() + b'\0'
        fields = [count, mode, 0, 0, 2 if stat.S_ISDIR(mode) else 1, int(EPOCH), len(data), 0, 0, major, minor, len(filename), 0]
        archive.extend(b'070701' + b''.join(f'{v:08x}'.encode() for v in fields))
        archive.extend(filename); archive.extend(bytes(-len(archive) % 4))
        archive.extend(data); archive.extend(bytes(-len(archive) % 4))
    for p in sorted(root.rglob('*'), key=lambda p: (len(p.relative_to(root).parts), str(p))):
        meta = p.lstat()
        data = p.read_bytes() if stat.S_ISREG(meta.st_mode) else os.readlink(p).encode() if p.is_symlink() else b''
        add(str(p.relative_to(root)), meta.st_mode, data, os.major(meta.st_rdev), os.minor(meta.st_rdev))
    for name, major, minor in [('console', 5, 1), ('null', 1, 3), ('zero', 1, 5), ('tty', 5, 0), ('random', 1, 8), ('urandom', 1, 9)]:
        if not (root / 'dev' / name).exists():
            add('dev/' + name, stat.S_IFCHR | 0o600, major=major, minor=minor)
    add('TRAILER!!!', 0)
    archive.extend(bytes(-len(archive) % 512))
    return archive


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--imagebuilder', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    ib = a.imagebuilder.resolve(); out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    target = next((ib / 'build_dir').glob('target-arm_*/root-ipq40xx')).parent
    linux = target / 'linux-ipq40xx_generic'
    kernel = (linux / 'Image').read_bytes()
    assert sha(kernel) == KERNEL_SHA
    (out / 'kernel.bin').write_bytes(kernel)
    root = out / 'root'
    clean_root(target / 'root-ipq40xx', root)
    assert not list((root / 'etc/dropbear').iterdir())
    assert (root / 'www/luci-static/argon').is_dir()
    assert 'root::' in (root / 'etc/shadow').read_text()
    run('mksquashfs', root, out / 'root.squashfs', '-noappend', '-comp', 'xz', '-b', '262144',
        '-processors', '2', '-all-root', '-all-time', EPOCH, '-mkfs-time', EPOCH, '-no-progress', stdout=subprocess.DEVNULL)
    spi = '/soc/spi@78b5000'
    def make_dtb(name, ram):
        dtb = out / name
        run('dtc', '-q', '-I', 'dts', '-O', 'dtb', '-o', dtb, REPO / 'firmware/ti04-base.dts')
        def put(node, prop, *values): run('fdtput', '-t', 's', dtb, node, prop, *values)
        first = spi + '/spi-nand@1/partitions/partition@0'
        put(first, 'label', 'install-target' if ram else 'rootfs')
        run('fdtput', '-d', dtb, first, 'read-only')
        put(spi + '/spi-nand@1/partitions/partition@2000000', 'label', 'stock-reserved')
        args = 'console=ttyMSM0,115200 rdinit=/init root=/dev/ram0 loglevel=6' if ram else 'console=ttyMSM0,115200 ubi.mtd=rootfs root=/dev/ubiblock0_1 rootfstype=squashfs rootwait'
        put('/chosen', 'bootargs', args)
        put('/chosen', 'bootargs-append', ' ' + args)
        put('/', 'model', 'TI04-708H RAM installer' if ram else 'TI04-708H')
        return dtb
    boot_dtb, ram_dtb = make_dtb('boot.dtb', False), make_dtb('installer.dtb', True)
    def make_fit(name, dtb, ram=False):
        images = '''kernel-1 { data=/incbin/("kernel.bin"); type="kernel"; arch="arm"; os="linux"; compression="none"; load=<0x80208000>; entry=<0x80208000>; hash@1 {algo="crc32";}; hash@2 {algo="sha1";}; };
fdt-1 { data=/incbin/("DTB"); type="flat_dt"; arch="arm"; compression="none"; hash@1 {algo="crc32";}; hash@2 {algo="sha1";}; };'''.replace('DTB', dtb.name)
        if ram:
            images += 'ramdisk-1 { data=/incbin/("root.cpio"); type="ramdisk"; arch="arm"; os="linux"; compression="none"; load=<0x81000000>; hash@1 {algo="crc32";}; hash@2 {algo="sha1";}; };'
        config = 'kernel="kernel-1"; fdt="fdt-1";' + ('ramdisk="ramdisk-1";' if ram else '')
        its = '/dts-v1/; / { description="TI04 public ' + RELEASE + '"; #address-cells=<1>; images {' + images + '}; configurations { default="config@5";' + ''.join(n + ' {' + config + '};' for n in ('config@1', 'config@5', 'config@ap.dk01.1-c2')) + '}; };'
        (out / (name + '.its')).write_text(its)
        run('mkimage', '-f', name + '.its', name, cwd=out, stdout=subprocess.DEVNULL)
        for node, path in [('kernel-1', out / 'kernel.bin'), ('fdt-1', dtb)] + ([('ramdisk-1', out / 'root.cpio')] if ram else []):
            for prop, expected in [('hash@1', zlib.crc32(path.read_bytes()).to_bytes(4, 'big')), ('hash@2', hashlib.sha1(path.read_bytes()).digest())]:
                actual = bytes(int(x, 16) for x in subprocess.check_output(['fdtget', '-t', 'bx', str(out / name), '/images/' + node + '/' + prop, 'value']).split())
                assert actual == expected
    make_fit('kernel-stock-uboot.itb', boot_dtb)
    leb, peb = 126976, 131072
    ksize, rsize = (out / 'kernel-stock-uboot.itb').stat().st_size, (out / 'root.squashfs').stat().st_size
    kl, rl = math.ceil(ksize / leb), math.ceil(rsize / leb)
    assert kl + rl + 32 < 256
    config = ''
    for n, name, path, size, flag in [(0, 'kernel', out / 'kernel-stock-uboot.itb', kl * leb, ''), (1, 'rootfs', out / 'root.squashfs', rl * leb, ''), (2, 'rootfs_data', None, leb, 'vol_flags=autoresize\n')]:
        config += f'[{name}]\nmode=ubi\nvol_id={n}\nvol_type=dynamic\nvol_name={name}\nvol_size={size}\n' + (f'image={path}\n' if path else '') + flag
    (out / 'ubinize.cfg').write_text(config)
    run('ubinize', '-o', out / 'ti04-25.12.6-first32m.ubi', '-m', '2048', '-p', str(peb), '-s', '2048', '-O', '2048', '-Q', '20261029', out / 'ubinize.cfg')
    ubi = (out / 'ti04-25.12.6-first32m.ubi').read_bytes()
    assert len(ubi) < 33554432 and len(ubi) % peb == 0
    volumes = {0: {}, 1: {}}
    for start in range(0, len(ubi), peb):
        ec, vid = ubi[start:start + 64], ubi[start + 2048:start + 2112]
        assert ec[:4] == b'UBI#' and vid[:4] == b'UBI!'
        assert struct.unpack_from('>II', ec, 16) == (2048, 4096)
        for header in (ec, vid): assert zlib.crc32(header[:60]) ^ 0xFFFFFFFF == int.from_bytes(header[60:], 'big')
        v, l = struct.unpack_from('>II', vid, 8)
        if v in volumes: volumes[v][l] = ubi[start + 4096:start + peb]
    for n, name in [(0, 'kernel-stock-uboot.itb'), (1, 'root.squashfs')]:
        expected = (out / name).read_bytes()
        assert b''.join(volumes[n][i] for i in sorted(volumes[n]))[:len(expected)] == expected
    def info(name):
        data = (out / name).read_bytes()
        return {'name': name, 'bytes': len(data), 'sha256': sha(data), 'crc32': f'{zlib.crc32(data):08x}'}
    manifest = {'release': RELEASE, 'status': 'prerelease-offline-validated-new-public-build-not-hardware-tested',
                'openwrt': '25.12.6', 'kernel': '6.12.112', 'model': 'allRadio TI04-708H / WGHE010100',
                'nand': {'page': 2048, 'oob': 64, 'erase': peb, 'leb': leb, 'write_range': [0, 33554432], 'preserve_range': [33554432, 134217728], 'kernel_lebs': kl, 'rootfs_lebs': rl},
                'auth': 'root initially empty; set own password locally; host keys generated per device',
                'mac': 'No fixed MAC; local Ethernet identities derived from own ART on first boot',
                'features': ['Argon 3.1.0', 'Korean default / English selectable', 'NTP', 'WAN/LAN/WiFi LED services', 'band names', 'driver-supported power profile'],
                'files': {'ubi': info('ti04-25.12.6-first32m.ubi'), 'kernel': info('kernel-stock-uboot.itb'), 'rootfs': info('root.squashfs')}}
    text = json.dumps(manifest, indent=2) + '\n'
    (out / 'manifest.json').write_text(text)
    ram_root = out / 'ram-root'
    shutil.copytree(root, ram_root, symlinks=True)
    shutil.copyfile(ib / 'target/linux/generic/other-files/init', ram_root / 'init')
    (ram_root / 'init').chmod(0o755)
    putfile(ram_root, 'lib/preinit/80_mount_root', '# RAM installer: do not mount persistent storage.\n')
    for name in ('sbin/mount_root', 'sbin/sysupgrade'):
        putfile(ram_root, name, '#!/bin/sh\necho "Persistent operation disabled in RAM installer" >&2\nexit 1\n', 0o755)
    for link in (ram_root / 'etc/rc.d').glob('*ti04-leds'):
        link.unlink()
    putfile(ram_root, 'etc/ti04-installer-release', RELEASE + '\n')
    putfile(ram_root, 'etc/ti04-release-manifest.json', text)
    putfile(ram_root, 'usr/sbin/ti04-install', (REPO / 'firmware/ti04-install.sh').read_text(), 0o755)
    archive = cpio(ram_root)
    assert 0x81000000 + len(archive) < 0x83E00000
    elf = (linux / 'vmlinux.elf').read_bytes()
    phoff = struct.unpack_from('<I', elf, 28)[0]
    phsize, phcount = struct.unpack_from('<HH', elf, 42)
    segments = [struct.unpack_from('<8I', elf, phoff + i * phsize) for i in range(phcount)]
    assert max(x[3] + x[5] - 0x40000000 for x in segments if x[0] == 1) + 0x10000 < 0x81000000
    (out / 'root.cpio').write_bytes(archive)
    make_fit('ti04-25.12.6-ram-installer.itb', ram_dtb, True)
    assert 0x84000000 + (out / 'ti04-25.12.6-ram-installer.itb').stat().st_size < 0x87300000
    ram_info = info('ti04-25.12.6-ram-installer.itb')
    ram_info.update({'load_hex': '84000000', 'size_hex': format(ram_info['bytes'], 'x'),
                     'boot_command': 'bootm 84000000#config@1', 'initrd_high': '83f00000', 'fdt_high': '83e00000'})
    (out / 'RAM_BOOT.json').write_text(json.dumps(ram_info, indent=2) + '\n')
    files = [out / n for n in ('manifest.json', 'RAM_BOOT.json', 'ti04-25.12.6-ram-installer.itb', 'ti04-25.12.6-first32m.ubi', 'kernel-stock-uboot.itb', 'root.squashfs')]
    (out / 'SHA256SUMS').write_text(''.join(sha(f.read_bytes()) + '  ' + f.name + '\n' for f in files))
    packages = sorted((root / 'lib/apk/packages').glob('*.list'))
    (out / 'packages.txt').write_text(''.join(x.stem + '\n' for x in packages))
    print(json.dumps({'release': RELEASE, 'rootfs_bytes': rsize, 'kernel_lebs': kl, 'rootfs_lebs': rl, 'ram_cpio_bytes': len(archive), 'ubi_bytes': len(ubi), 'status': manifest['status']}))


if __name__ == '__main__':
    main()
