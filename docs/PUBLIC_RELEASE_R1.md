# 공개 설치 패키지 25.12.6-ti04-r1

2026-10-29, 다른 사용자가 내려받을 파일이 없던 문제를 보완한 첫 공개 시험판이다.

## 다운로드

**[설치 패키지 ZIP 다운로드](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/download/v25.12.6-ti04-r1/ti04-openwrt-25.12.6-r1-install.zip)** · **[릴리스와 개별 파일](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/v25.12.6-ti04-r1)** · **[처음부터 설치하기](../INSTALLATION.md)**

| 파일 | 역할 |
|---|---|
| `ti04-openwrt-25.12.6-r1-install.zip` | 이미지·도구·안내를 모은 설치 패키지. 처음 방문한 사용자는 이것을 받는다 |
| `ti04-25.12.6-ram-installer.itb` | 순정 U-Boot TFTP로 RAM 부팅하는 설치 환경. 첫32MiB NAND만 쓰기 가능 |
| `ti04-25.12.6-first32m.ubi` | RAM 설치기가 기록하는 최종 NAND 이미지. LuCI 업로드용 파일 아님 |
| `manifest.json`, `RAM_BOOT.json`, `SHA256SUMS` | 대상·geometry·포함 기능·파일 크기/해시·RAM 부팅 값 |
| `ti04-25.12.6-package-cache.zip` | 동일 패키지 버전으로 빌드하기 위한 APK 캐시와 SHA256 |

ZIP에는 `patch_nor_env.py`, `ch341_nor.ps1`과 C# 전송 소스, `backup_nand.ps1`, `verify_backups.py`, TFTP/HTTP 서버, 릴리스 검증기, 설치기 및 빌드 소스가 들어 있다. 다른 기기의 NOR 원본·패치 NOR·ART·계정·SSH 키는 들어 있지 않다.

## 이미지 기본값

- OpenWrt25.12.6 / Linux6.12.112, 순정 U-Boot2012.07용 비압축 FIT, NAND 앞32MiB UBI.
- LAN `192.168.1.1/24`·DHCP 서버, WAN DHCP·방화벽/NAT. 설치 중에는 WAN을 분리한다.
- `root` 초기 암호는 비어 있다. UART/분리된 LAN에서 자기 암호를 바로 설정한다. SSH host key와 웹 인증서는 새 장비에서 생성한다.
- Wi-Fi 두 대역은 꺼져 있고 AP/SSID/암호는 없다. 국가 기본 KR이며 실제 사용 국가·SSID·WPA 암호를 직접 설정한다.
- Ethernet에 고정 MAC을 복제하지 않는다. 자기 ART에서 유도한 로컬 MAC을 첫 설정 때 저장하고, 무선 보정값은 자기 NOR의 ART를 읽는다.
- Argon3.1.0·한국어 기본·English 선택, LED/NTP, 대역 이름 표시와 현재 드라이버의 출력 프로필 포함. 구형35dBm 패치는 포함하지 않는다.
- 일반 sysupgrade는 차단한다. 초기화 버튼 GPIO는 미확정이므로 비활성화돼 있다. USB/모든 부가 기능의 완전 시험을 뜻하지 않는다.

## 검증과 한계

공식 kernel 바이트 일치, FIT 내부 CRC32/SHA1, UBI header CRC/geometry와 kernel/rootfs payload 재구성, CPIO·SquashFS 추출, 플래시 read-only 범위, 개인 인증 정보/고정 MAC 제거, 공개 기본 설정/UI 파일 포함 여부를 검사했다. NOR 패치의 CRC/범위/다른 환경값 보존, CH341 프레임·단일 섹터 제한, TFTP 전송, NAND 조각 CRC/SHA 검증을 오프라인 테스트했다.

**새 공개 이미지·범용화한 설치 도구는 아직 실기에서 기록/부팅하지 않았다.** 기존 장비의 개인용25.12.6 이미지로 확인한 정상 NAND 부팅·LAN4/WAN·두 대역 통신·테마/LED 결과는 [기존 검증 기록](POST_INSTALL_SETTINGS_20261027.md)이다. 새 공개 이미지의 성공으로 바꾸어 쓰지 않는다. 다른 순정 장비에서 전체 절차 재현, 물리 전원 재인가, LAN1~3 실물 케이블, 장기 안정성·RF·실제 복원도 남아 있다.

이 릴리스는 지원 대상 동일 보드·동일 칩·동일 geometry·불량 NAND 블록이 없는 경우로 제한한다. 불일치하면 설치기가 중단하며, 그 제한을 지우고 강행하는 절차는 제공하지 않는다. 버그 보고에는 비공개 백업·receipt·MAC·SSID·비밀번호·전체 로그를 첨부하지 않는다.
