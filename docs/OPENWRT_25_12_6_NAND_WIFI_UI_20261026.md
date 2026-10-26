# OpenWrt 25.12.6 NAND 설치·무선 시험·Argon 설정

> 처음 설치하는 사용자는 [설치 안내](../INSTALLATION.md)를 먼저 읽으세요. 이 문서는 검증 근거·개발 이력이며 실행 순서가 아닙니다.

기록: **2026-10-26, 한국 시간**. 사용자 소유 allRadio TI04-708H 한 대의 결과다. 앞선 [RAM 시험](OPENWRT_25_12_6_RAM_TEST_20261026.md) 뒤 NAND 설치까지 진행했으며, 현재 실행 버전은 **OpenWrt 25.12.6 / Linux 6.12.112**다. 공식 TI04 프로필이나 다른 리비전의 설치 보증을 뜻하지 않는다.

## 현재 판정

| 항목 | 확인 결과 |
|---|---|
| 실행 버전 | `25.12.6`, `r33311-981c978eff`, kernel `6.12.112`, board `giga,kt-9200`, model `TI04-708H` |
| 영구 설치 | NAND 앞32MiB에 kernel/rootfs/rootfs_data 구성. 순정 bootipq의 `config@5`로 정상 부팅 |
| 재부팅 | 설치 후 정상 NAND 부팅, 저장 확인용 재부팅, 테마 설치 후 재부팅까지 **3회** 확인. 자동 ESC 송신0, TFTP 없이 부팅 |
| 저장 유지 | `/rom` SquashFS + `/overlay` UBIFS. 확인 파일, Argon 패키지, 한글/영문 옵션이 재부팅 후 유지 |
| 보존 | 노출된 NOR8개 파티션 및 NAND 뒤96MiB의 SHA256이 설치 전과 일치. 25.12 설치 중 NOR 기록 없음 |
| 유선·DHCP | 기존 PC–실물 LAN1 연결 유지. 1Gbps 관리 경로와 실제 DHCP 클라이언트 동작 확인 |
| 2.4/5GHz | PC 무선 어댑터로 각 대역 연결 및 8MiB 다운로드·8MiB 업로드 성공 |
| 관리 UI | Argon **3.1.0**, 한글 기본. LuCI 기본 언어 선택기에 English 제공 |
| 최종 무선 상태 | 시험 전 설정으로 복구, 두 라디오 disabled. 임시 AP·HTTP 시험 도구 제거, PC 원래 Wi-Fi 프로필 복귀 |
| 미시험 | 물리 전원 재인가, WAN 인터넷/NAT 실통신, 나머지 실물 포트 매핑, 보정된 RF 출력·최대 성능·장기 안정성, 실제 백업 복원 |

사용자가 자리를 비운 상태여서 케이블 이동이나 물리 전원 조작은 하지 않았다. 한 가닥의 Ethernet 케이블은 PC–TI04 LAN1 관리 연결에 유지했다.

## 설치 전 백업과 기록 범위

기존 23.05.3의 현재 NAND 앞32MiB를 ECC 처리 읽기로 새로 백업했다. 1MiB 조각32개에 U-Boot CRC와 PC 파일 CRC를 대조하고, 조립한 파일 SHA256을 Linux의 같은 범위 읽기와 비교했다. 인증·설정 백업과 이전 순정 ECC/raw+OOB 전체 백업도 비공개 보관했다.

| 보관 산출물 | 바이트 | SHA256 |
|---|---:|---|
| 설치 직전 23.05.3 NAND 앞32MiB ECC 백업 | 33554432 | `b74b93596c9286523ec2153da0509eaba816cb95569375cbfc2239dfc154f880` |
| 25.12.6 kernel FIT | 13220620 | `f649a082fad2d533fa025ae001b2a9f8d2fac4abde0c8d7c6fce2b7abbdf3c8f` |
| 25.12.6 root SquashFS | 4591616 | `1cb64149ac20dde13cc08dcace4b5b6a3166b7eacec2b9672c1c81f09cd38c25` |
| 기록한 25.12.6 UBI | 18874368 | `d1210a4889bd0ed175080fb4f580889358fb3cc816addd9162ee716234abba04` |
| 수정된 23.05.3 kernel을 포함한 복귀용 UBI 후보 | 20447232 | `cf9f8ec1a0c8ee24d559848365e1c962e6ab7e0aed22396bdeb6856cb831f3d5` |

복귀용 이미지는 준비·오프라인 검사까지 했으며 실제 복원 시험은 하지 않았다. 바이너리·개별 인증 데이터·원본 로그는 공개하지 않는다. 해시만으로 복원 성공을 보장하지 않는다.

새 kernel은 기존23.05.3의96 LEB kernel 볼륨보다 커서 앞32MiB UBI를 재구성했다. kernel105 LEB, rootfs37 LEB, 나머지는 rootfs_data이며 마지막 확인에서 rootfs_data90 LEB였다. 기록 직전 보드·MTD 경계·쓰기 flags·파일 크기/SHA를 검사한 후 **앞32MiB만** 포맷했다. 기록 뒤 kernel/rootfs SHA를 대조하고, NOR8개 파티션과 뒤96MiB 해시 불변을 확인했다. 테마 적용 후 재부팅에서도 같은 kernel/rootfs와 보존 해시를 다시 확인했다.

NOR8개 노출 파티션은 물리2MiB NOR 중1.5MiB를 덮는다. 이번25.12 검증의 파티션 해시를 새로운 전체2MiB readback이라고 표현하지 않는다. 전체 NOR의 프로그래머 readback은 이전 환경 패치 검증 기록이다.

## TI04용 부팅 구성

- [공식25.12.6 ipq40xx/generic 배포물](https://downloads.openwrt.org/releases/25.12.6/targets/ipq40xx/generic/)의 kernel·ImageBuilder·동일 버전 패키지를 사용했다. 다른 보드의 factory 이미지를 통째로 설치하지 않았다.
- RAM 시험에서 수정한 QCA8075 PHY package/MDIO 구조를 반영했다. 기존 실물 LAN1은 DTB의 `lan4`로 관측되며, 나머지 실물 포트 이름 매핑은 확정하지 않았다.
- rootfs는 공식 영구 부팅용 preinit을 사용했다. RAM 시험용 mount_root 우회 파일을 영구 설치에 남기지 않았다.
- 앞32MiB 파티션 이름 `rootfs`, `/chosen/bootargs-append`의 `root=/dev/ubiblock0_1`을 유지해 순정 bootipq의 legacy root 인자를 보완했다. 23.05 첫 설치의 root mount 실패와 수정은 [종합 보고서8절](../OPENWRT_INSTALLATION_ANALYSIS_REPORT.md#8-23053-nand-설치와-첫-부팅-실패-수정)에 남겼다.
- NOR 및 NAND 뒤96MiB는 쓰기 비활성, 앞32MiB만 쓰기 가능하다. MTD 번호는 이 환경의 관측값이므로 다른 부팅 환경에 복사하지 않는다.
- 기존 root 인증 정보와 Dropbear host key는 유지했다. 현재 root 암호는 비어 있어 사용자가 로컬에서 설정해야 한다. 일반 sysupgrade는 원래 압축/config/파티션 제약을 다시 만들 수 있어 차단 상태다.

## 실제 무선 송수신 시험

WPA2 임시 AP를 대역별로 순차 구동했다. 2.4GHz는 채널1/HT20, 5GHz는 채널36/VHT80, 소프트웨어 TX power 설정은10dBm이었다. 이는 보정된 실제 출력 측정값이 아니다.

PC의 Wi-Fi 주소를 전송 소스로 지정하고 해당 주소의 경로를 확인했다. 실제 Wi-Fi 어댑터의 수신·송신 바이트 증가 및 공유기의 hostapd 연결/해제와 station 카운터를 함께 확인했다. Ethernet 관리 연결을 계속 유지한 상태에서도 시험 트래픽의 무선 경로를 확인했다.

| 대역 | 다운로드 | 업로드 | 각 방향 데이터 |
|---|---:|---:|---:|
| 2.4GHz | 약18.24Mbps | 약33.72Mbps | 8MiB |
| 5GHz | 약106.20Mbps | 약36.45Mbps | 8MiB |

다운로드 payload의 SHA256과 업로드 수신 바이트/해시를 검사했다. 이는 짧은 HTTP 전송 관측값이며 최대 무선 처리량 벤치마크나 WAN 인터넷 속도가 아니다. PC의 원래 Wi-Fi 연결로 복귀했고 임시 프로필은 삭제했다. 공유기 wireless 설정도 시험 전 값으로 복원해 두 라디오가 disabled인 것을 재부팅 후 확인했다. 임시 CGI·payload도 제거했다.

이전 NAND 부팅의 uptime1488초 시점까지 약25분 동안 작업·시험이 이어졌다. 확인한 로그 구간에서 panic/관련 probe 실패를 보지 못했지만 장기 안정성 판정은 아니다.

## Argon과 한글·영문 전환

[Argon 공식 v3.1.0 릴리스](https://github.com/jerrykuku/luci-theme-argon/releases/tag/v3.1.0)의 APK와 한국어 설정 번역을 사용했다. 릴리스는25.12.5 stable SDK로 만든 APK v3 및 소스 템플릿을 제공한다. 별도 예전 설정 플러그인은 필요하지 않았다. 번역·의존 패키지는 공식25.12.6 배포물에서 준비했다.

- theme APK SHA256: `82c36abe5dbd958f733b620c4c66b160f1b3470feaf248921baae77b2b5d0f44`
- Argon 한국어 APK SHA256: `783ee1650bfb5641764d3e8cdb5c95fa95cb6a36a1f7af0abdd5ea7e1537a4d3`
- 공식 base/firewall/package-manager 한국어 번역, coreutils/timeout/flock 및 필요한 라이브러리를 함께 설치했다.
- HTTPS 출처와 파일 크기/SHA, 장비에 전달한 파일 SHA를 대조했다. 서명 신뢰 오류는 해당 로컬 설치 명령에만 `--allow-untrusted`를 사용했다. 전역 검증 해제나 의존성 강제 무시는 하지 않았다.
- `luci.main.lang=ko`, `luci.main.mediaurlbase=/luci-static/argon`, English 선택 항목을 저장했다.

영문 변경은 **시스템 → 시스템 → 언어 및 스타일 → 언어 → English → 저장 및 적용**에서 할 수 있다. 영문 UI에서는 **System → System → Language and Style**다. LuCI 기본 선택기를 사용하며 별도 전환 코드를 추가하지 않았다.

CLI로 영문을 선택한 뒤 웹 응답의 `lang=en`과 Username/Password를 확인하고 한글로 되돌렸다. 마지막 재부팅 후 `lang=ko`, 한글 로그인 문구, Argon3.1.0 표시, CSS/이미지 HTTP200, 설치 패키지 및 설정 유지를 확인했다. 로그인 HTML의 HTTP403와 `x-luci-login-required: yes`는 인증 요구 응답이다.

브라우저 제어가 Work 설정에서 비활성이라 화면 렌더링·메뉴 클릭은 확인하지 않았다. 위 판정은 실제 장비의 설정·패키지·HTTP 응답 및 LuCI 시스템 화면 소스의 기본 선택기 확인에 근거한다. 마지막 overlay 여유는 약7.1MiB다.

## 실패·중단과 해결

| 시도 | 결과와 후속 조치 |
|---|---|
| 최초 Wi-Fi 시험기의 어댑터 제어 | 지원하지 않는 `-InterfaceIndex` 인자, 이어진 비활성화는 Windows 권한 오류. 원래 Wi-Fi로 복귀하고 중단 |
| Wi-Fi 경로 검증 수정 | 어댑터 비활성화 대신 소스 주소·경로·실제 Wi-Fi 바이트 카운터로 검증. 이후 두 대역 송수신 성공 |
| 로컬 APK 첫 설치 | 서명 신뢰 오류로 중단. 출처/해시 확인 후 해당 설치에만 명시적 허용 |
| 의존 패키지 누락 | coreutils/timeout/flock, 이어서 librt/libpthread 필요로 transaction 거절. 공식 패키지 준비 후 정상 설치 |
| 도중 대화 중단 | 재개 시 저장 로그와 실제 설치 상태를 먼저 확인. 의존 패키지 설치는 이미 완료돼 있어 반복하지 않음 |
| 브라우저 제어 | Work 설정에서 비활성. 설정 우회 없이 backend/HTTP 검사로 확인 범위 제한 |
| 최종 `ubiinfo` 조회 | 영구 rootfs에 도구가 없어 조회 실패. sysfs의 볼륨 이름/LEB 수와 실제 volume SHA로 확인 |

앞선 QCA8075 RAM 후보 실패와 수정, 23.05.3 첫 NAND 부팅 실패 등은 별도 [실험 이력](EXPERIMENT_LOG_20261026.md)과 RAM 보고서를 유지한다. README의 미검증 실험 아이디어를 성공 사례로 바꾸거나 삭제하지 않았다.
