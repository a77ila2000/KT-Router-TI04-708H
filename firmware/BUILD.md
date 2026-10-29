# TI04 25.12.6-ti04-r1 배포본 빌드

Linux x86-64 / Python 3.11 이상, GNU make, zstd, dtc/fdtget/fdtput, U-Boot mkimage/dumpimage, squashfs-tools, mtd-utils, ARM hard-float 정적 GCC가 필요하다. Ubuntu에서는 `build-essential zstd device-tree-compiler u-boot-tools squashfs-tools mtd-utils gcc-arm-linux-gnueabihf`와 ImageBuilder가 요구하는 라이브러리를 설치한다.

## 입력과 출처

- [공식 25.12.6 ipq40xx/generic 배포 디렉터리](https://downloads.openwrt.org/releases/25.12.6/targets/ipq40xx/generic/)
- `openwrt-imagebuilder-25.12.6-ipq40xx-generic.Linux-x86_64.tar.zst`
- ImageBuilder SHA256: `9e377a6c51ad667b6aa277934714174467b44723b1456153317d7a4aef3f1fd2`
- 비압축 공식 Linux 6.12.112 `Image` SHA256: `05767f8cece8c5106458df3293534f1ae0b063ab57ae6241678ea91c89301d97`
- [Argon v3.1.0](https://github.com/jerrykuku/luci-theme-argon/releases/tag/v3.1.0): `luci-theme-argon-3.1.0-r1.apk` SHA256 `82c36abe5dbd958f733b620c4c66b160f1b3470feaf248921baae77b2b5d0f44`.
- Argon 한글 APK SHA256: `783ee1650bfb5641764d3e8cdb5c95fa95cb6a36a1f7af0abdd5ea7e1537a4d3`.
- [릴리스](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/v25.12.6-ti04-r1)의 `ti04-25.12.6-package-cache.zip`에 실제 사용한 APK들과 개별 SHA256이 있다. 개인 설정이나 ImageBuilder 서명용 개인 키는 포함하지 않는다.

## 깨끗한 ImageBuilder에서 root 생성

기존 개인용 root나 플래시 백업을 입력으로 사용하지 않는다. 새 작업 폴더에 공식 아카이브를 풀고, 캐시 ZIP의 `packages/` 파일을 ImageBuilder의 `packages/`로 복사한다. 캐시 안 `PACKAGE_SHA256SUMS`부터 검증한다. 캐시가 필요한 이유는 피드 갱신과 다운로드 실패에 영향을 받지 않고 이번 패키지 버전을 재사용하기 위해서다.

```sh
# 작업 폴더 예시. 실제 압축 해제한 ImageBuilder 경로로 이동한다.
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
cd openwrt-imagebuilder-25.12.6-ipq40xx-generic.Linux-x86_64
# 원격 피드 대신 해시를 검증한 로컬 packages/만 사용하는 오프라인 빌드
: > repositories
make package_index
make image PROFILE=8dev_jalapeno PACKAGES="luci luci-i18n-base-ko luci-i18n-firewall-ko luci-i18n-package-manager-ko luci-theme-argon luci-i18n-argon-config-ko -mtd -uboot-envtools"
```

`8dev_jalapeno`는 공식 kernel/패키지를 얻기 위한 빌드 프로필이다. **그 프로필이 생성한 factory/sysupgrade 파일을 TI04에 기록하지 않는다.** 다음 단계가 TI04 DTB·루트·순정 U-Boot FIT·UBI를 만든다.

```sh
# 저장소 루트에서 실행. --out은 존재하지 않는 새 디렉터리여야 한다.
python3 firmware/build_release.py --imagebuilder /absolute/path/to/imagebuilder --out /absolute/path/to/new-artifacts
python3 firmware/verify_images.py /absolute/path/to/new-artifacts
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_radio_power.cjs
node tests/test_wireless_band_labels.cjs
```

빌더는 원래의 공식 `mount_root` preinit hook과 kernel SHA를 검사한 뒤 동작한다. 완성 root에는 표준 LAN DHCP/WAN NAT, Argon/한국어, LED, NTP, 출력 프로필, 별도 대역 표시 화면을 넣는다. NOR·보정값·고정 MAC·기존 비밀번호·host key를 읽거나 입력받지 않는다. 새 장비의 Ethernet MAC은 첫 부팅 시 자기 ART 해시로 만든 로컬 주소이며 Wi-Fi는 자기 ART를 읽는다.

`kernel-stock-uboot.itb`, `root.squashfs`, `ti04-25.12.6-first32m.ubi`, `ti04-25.12.6-ram-installer.itb`, `manifest.json`, `RAM_BOOT.json`, `SHA256SUMS`가 주요 산출물이다. UBI kernel/rootfs payload 재구성, FIT CRC32/SHA1, CPIO와 RAM 주소 범위를 검사한다. 최신 도구가 `config@5`/`hash@1`의 `@`를 경고하는 것은 구형 순정 bootipq 호환 이름 때문이다. 이 FIT는 서명 부팅을 구현한 이미지가 아니다.

## 소스와 라이선스

OpenWrt·Linux·BusyBox 등 각 구성요소의 라이선스가 적용된다. [OpenWrt v25.12.6 소스](https://github.com/openwrt/openwrt/tree/v25.12.6), 공식 배포 디렉터리의 `feeds.buildinfo`/`config.buildinfo`/`version.buildinfo`, [OpenWrt 소스 아카이브](https://sources.openwrt.org/), [Linux 6.12.112 소스](https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.112.tar.xz)를 함께 참고한다. Argon은 [Apache-2.0 및 프로젝트 소스](https://github.com/jerrykuku/luci-theme-argon/tree/v3.1.0)를 따른다. TI04 DTB는 `ti04-base.dts`, LED와 UI 변경은 이 저장소에서 소스를 제공한다. CH341 DLL/드라이버는 재배포하지 않으며 [AsProgrammer 공식 프로젝트](https://github.com/nofeletru/UsbAsp-flash/releases/tag/v2.1.2)에서 받는다.

이번 릴리스는 **오프라인 검증한 새 공개 빌드**다. 이전 개인용 이미지의 실기 성공과 구분한다. 다른 순정 장비 재현·새 공개 빌드 RAM/NAND 실기 부팅·물리 전원 재인가·복원 검증을 마치기 전에는 안정판으로 올리지 않는다.
