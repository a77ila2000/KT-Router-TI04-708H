# OpenWrt 25.12.6 RAM 시험 — 2026-10-26

> 처음 설치하는 사용자는 [설치 안내](../INSTALLATION.md)를 먼저 읽으세요. 이 문서는 검증 근거·개발 이력이며 실행 순서가 아닙니다.

> 이 문서는 NAND 설치 전 RAM 시험의 역사적 기록이다. 이후 [25.12.6 NAND 설치·실제 무선 송수신·Argon/언어 설정](OPENWRT_25_12_6_NAND_WIFI_UI_20261026.md)까지 완료했다. 아래 ‘미시험’은 이 RAM 단계의 범위다.

**TI04-708H 한 대에서 OpenWrt25.12.6 / Linux6.12.112의 RAM 부팅과 기본 유선 관리 시험을 통과했다.** 시험 후 기존 NAND23.05.3으로 자동 부팅해 복귀했다. **25.12.6을 NAND에 설치한 결과는 아니다.**

## 확인한 범위

| 항목 | 실기 결과 |
|---|---|
| 버전 | `25.12.6`, `r33311-981c978eff`, kernel `6.12.112`, CPU4개 |
| 부팅 | 순정 U-Boot에서 TFTP 전송, 전체 CRC 및 FIT payload CRC32/SHA1 통과, 비압축 kernel + 외부 CPIO 실행 |
| 저장 격리 | `/`는 tmpfs, `rootfs_type=initramfs`, UBI 미attach. 노출된 NOR8개 및 NAND2개 파티션 모두 쓰기 비활성 flags |
| 유선 PHY | 첫 후보의 QCA8075 probe 오류 수정 후 다섯 PHY에 `Qualcomm QCA8075` 드라이버 정상 연결 |
| 연결 포트 | 기존 실물 LAN1, DTB 이름 `lan4`에서 1Gbps Full 링크. 다른 실물 포트 매핑은 미시험 |
| DHCP | PC에 DHCP 주소 할당. 공유기 DHCPACK와 Windows의 DHCPServer/임대 취득을 함께 확인 |
| 관리 통신 | PC ping5회 성공, `TI04-RAM2512` LuCI 로그인 HTML 수신. HTTP403와 `x-luci-login-required: yes`는 로그인 요구 응답 |
| 무선 초기화 | PHY2개, 2.4/5GHz 기능 및 `pre-cal-nvmem` 보정값 읽기 확인. 라디오 disabled, 실제 송수신·출력 미시험 |
| 제한된 관찰 | 약176초 시점까지 실행 확인. 두 번째 후보의 검사 구간에서 kernel probe 실패/panic 미관측. 장기 안정성 증명 아님 |
| 플래시 보존 | RAM 시험 전후 노출된10개 MTD 파티션의 SHA256 모두 동일. NAND 앞32MiB와 뒤96MiB도 각각 일치 |
| 복귀 | ESC/TFTP 없는 기존 NAND23.05.3 부팅, SquashFS/UBIFS overlay와 기존 저장 파일 유지. RAM에서만 만든 시험 파일은 사라짐 |

## 공식 구성요소와 TI04용 변경

- [공식25.12.6 ipq40xx/generic 배포물](https://downloads.openwrt.org/releases/25.12.6/targets/ipq40xx/generic/)의 ImageBuilder와 같은 버전의 패키지를 사용했다. TI04 전용 공식 프로필은 없으며, `8dev_jalapeno` 프로필은 기본 패키지/rootfs 구성용으로 사용했다. 그 보드의 DTB나 factory 이미지를 TI04에 설치하지 않았다.
- 공식 kernel `Image`와 해당 프로필 FIT의 압축 해제 payload가 byte 단위로 같은지 확인했다. kernel을 소스 수정한 결과는 아니다.
- 작동하던 TI04 DTB에 `qcom,ipq4018` compatible과 RAM 부팅 인자를 추가하고, 모든 노출 파티션을 read-only로 설정했다. NAND 이름에서 `rootfs`/`ubi` 자동 attach 대상을 제거했다.
- 유선 MDIO 아래의 PHY들을 최신 `ethernet-phy-package@0` 구조로 옮겼다. 기존 phandle을 보존해 switch/PHY 연결을 유지하고, 공식 ImageBuilder에 포함된 `qcom-ipq4019.dtsi`의 package 속성을 대조했다. 드라이버의 부모 package 요구는 [Linux QCA807x probe](https://github.com/torvalds/linux/blob/v6.12/drivers/net/phy/qcom/qca807x.c)에서 확인했다.
- 공식 `/init`의 `INITRAMFS=1`과 tmpfs 전환을 사용했다. 시험용 mount_root/sysupgrade 진입을 차단하고 bootcount/ubihealthd 시작을 비활성화했다. GPIO 버튼은 시험 DTB에서 비활성화했다.
- rootfs에는 TI04용 LAN bridge와 시험 hostname, 두 라디오 disabled 설정을 적용했다. 암호나 기존 NAND 설정을 복사하지 않았다. WAN 인터페이스는 이 RAM 시험에 구성하지 않았다.
- 공식 kernel은 외부 압축 initrd decoder가 비활성이라 CPIO를 비압축으로 사용했다. kernel의 ELF LOAD/BSS 끝까지 확인해 initrd와 겹치지 않음을 검증했다. FIT staging과 부트로더 영역도 분리했다.

## 산출물 식별

바이너리는 비공개 로컬에 보관한다. **RAM FIT는 NAND 설치 이미지가 아니다.**

| 파일/역할 | 바이트 | SHA256 |
|---|---:|---|
| 공식 ImageBuilder archive | 482217776 | `9e377a6c51ad667b6aa277934714174467b44723b1456153317d7a4aef3f1fd2` |
| 공식 비압축 kernel | 13201280 | `05767f8cece8c5106458df3293534f1ae0b063ab57ae6241678ea91c89301d97` |
| 최종 RAM 시험 FIT, v2 | 28144844 | `15be4ec2313ebe9c8919994491428f7104ece7728ea8e372225372fe1eebfc28` |

## 실패와 수정

| 시도 | 결과와 조치 |
|---|---|
| 첫 ImageBuilder 실행 | Windows PATH에 섞인 상대 경로 때문에 `find -execdir`가 거절. Linux PATH로 다시 실행해 완료. 장비 작업 전의 PC 빌드 실패 |
| 첫 패키징 검사 | `Image`와 ELF 변환 `vmlinux`가 같다는 검사 실패. GNU build-id note 등43바이트 차이를 확인하고, 공식 FIT payload를 압축 해제해 `Image`와 직접 대조하는 검사로 수정 |
| 실패한 작업 디렉터리 재사용 | 기존 symlink 때문에 copytree가 중단. Linux 파일시스템의 별도 작업 루트에서 다시 구성. 장비 기록 없음 |
| 첫 TFTP 전송 | 재부팅 중 PC의 DHCP 주소가 해제돼 서버 bind 주소가 사라짐. 전송 제한 시간 후 중단하고, 부트로더 단계에서 유지되는 PC 주소를 확인해 재전송 |
| 첫 RAM 후보 | kernel/사용자 환경은 부팅했지만 QCA8075 probe가 `-22`로 실패해 Generic PHY로 동작. 최신 드라이버가 요구하는 PHY-package 부모가 없던 것이 원인 |
| 두 번째 RAM 후보 | PHY-package와 TI04 board network 기본값 반영. 다섯 QCA8075 probe 성공, 유선/DHCP/LuCI 및 두 무선 PHY 초기화 확인 |

## 영구 설치 전 남은 사항

25.12.6의 비압축 kernel만13,201,280바이트다. **현재 NAND kernel 볼륨은96 LEB =12,189,696바이트이므로 kernel 볼륨만 덮어쓰는 업그레이드는 불가능하다.** kernel/DTB와 rootfs/overlay를 포함한 앞32MiB UBI 구성을 별도로 만들어 용량·부팅·복구를 검증해야 한다. 이번에는 해당 재구성이나 NAND 기록을 실행하지 않았다.

실제 RF 송수신·출력, WAN 인터넷, 다른 실물 포트, 장기 안정성, 물리 전원 재인가는 미시험이다. 현재 장비는 시험 전의 NAND23.05.3으로 복귀한 상태다. 원본 보정값·비밀 값·전체 UART/HTML 로그·장비별 이미지는 공개하지 않는다.
