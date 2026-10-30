# TI04-708H OpenWrt 설치

allRadio **TI04-708H / WGHE010100**에 OpenWrt를 설치하기 위한 자료입니다. 처음 설치하는 사용자는 **[설치 안내](INSTALLATION.md)**에서 준비 조건부터 순서대로 확인하세요.

**[⬇ 설치 이미지·도구 ZIP 다운로드](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/download/v25.12.6-ti04-r1/ti04-openwrt-25.12.6-r1-install.zip)** · **[OpenWrt 릴리스](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/v25.12.6-ti04-r1)** · **[순정 롬/덤프 다운로드](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/stock-dump-v1.4.0)** · **[설치 순서](INSTALLATION.md)**

> **실제 TI04 공유기 1대에 설치·기능 테스트 완료 — 공개 r1은 추가 실기 검증 전**
>
> OpenWrt25.12.6을 실제 공유기 NAND에 설치하고 정상 부팅3회·설정 유지·LAN4/WAN·2.4GHz/5GHz 통신을 확인했습니다. Argon/한글·영문 선택과 LED 후속 시험도 완료했습니다. [실기 시험 완료 항목](docs/PUBLIC_RELEASE_R1.md#공유기-실기-설치테스트-완료)을 확인하세요.
>
> 공개 r1은 개인 계정/키/고정 MAC을 제거해 새로 만든 배포 이미지입니다. RAM FIT·NAND UBI·환경 패처/4KiB 기록기·백업/검증·전송/설치 도구·SHA256과 소스를 제공합니다. **새 공개 파일 자체의 재설치·부팅 시험은 아직 확인 전**입니다. Code → Download ZIP은 소스만 받으므로 위 설치 패키지를 받으세요.

## 처음 방문한 사용자의 읽는 순서

1. **[대상 보드·준비물 확인](INSTALLATION.md)** — allRadio TI04와 다른 KT 모델을 구분합니다.
2. **[설치 안내](INSTALLATION.md)** — 자기 백업, UART 진입, RAM 설치 환경, 앞32MiB 기록, 부팅/저장 판정 순서입니다.
3. **[설치 후 최신 검증·설정](docs/POST_INSTALL_SETTINGS_20261027.md)** — WAN 통신, LED, NTP와 화면 표시의 확인 범위를 봅니다. 이전 [NAND·Wi-Fi·UI 검증](docs/OPENWRT_25_12_6_NAND_WIFI_UI_20261026.md)도 보존합니다.
4. 문제가 생기면 **[증상별 조치](INSTALLATION.md#문제가-생기면)**와 필요한 실패 기록만 확인합니다.

## 설치 경로

| 순서 | 작업 | 다음 단계로 가는 조건 |
|---|---|---|
| 1 | 보드·칩·geometry 식별 | 지원 대상과 일치 |
| 2 | 자기 NOR 독립3회 백업 | 크기/내용/SHA 일치, 원본 별도 보관 |
| 3 | 자기 환경의 `bootdelay=2012` 패치 | CRC 유효, 기록 전후 범위 검사, 전체 NOR readback 일치 |
| 4 | ESC U-Boot 진입·NAND 전체 백업 | 프롬프트/명령 응답, ECC main·raw/OOB 검증 |
| 5 | 검증된 설치용 RAM 부팅 | tmpfs root, 앞32MiB만 쓰기 가능, NOR/뒤96MiB 보호 |
| 6 | 최종25.12.6 UBI 기록 | 파일/범위 guard, kernel/rootfs readback, 보존 해시 일치 |
| 7 | NAND 자동 부팅·저장·통신 검사 | ESC/TFTP 없이 부팅, 재부팅 후 설정 유지, 필요한 통신 시험 |
| 8 | 초기 암호·Wi-Fi·테마/언어 설정 | 자기 암호/키 사용, 패키지 포함 여부 확인 |

공개 패키지는 **25.12.6 RAM 설치 환경 → 최종25.12.6 NAND 기록** 경로입니다.23.05.3 NAND 중간 설치는 넣지 않습니다. 개발 실기는23.05.3을 거쳐 업그레이드했으며, 다른 순정 장비에서 새 공개 파일로 전체 순서를 재현하는 시험은 남아 있습니다.

## 기존 개인용 이미지의 실기 검증 결과

| 항목 | 확인된 결과 |
|---|---|
| 버전·저장 | OpenWrt25.12.6 / Linux6.12.112, NAND 앞32MiB, SquashFS + UBIFS overlay |
| 정상 부팅 | 순정 bootipq `config@5`, ESC/TFTP 없는 정상 부팅3회, 저장 파일·UI 설정 유지 |
| 보존 | 노출된 NOR8개 파티션 및 NAND 뒤96MiB의 설치 전후 SHA 일치 |
| 유선·무선 | 실제 LAN4와 WAN 각각1Gbps, DHCP·DNS·NAT/인터넷 통신. 두 무선 대역 실제 인터넷 송수신 확인 |
| UI | Argon3.1.0, 한글 기본, English 선택 및 재부팅 유지. 설정/HTTP 검사, 시각적 렌더링은 미확인 |
| LED·시간 | WAN·실물 LAN4 LED 반응 사용자 확인, 두 대역 공용 Wi-Fi LED 소프트웨어 반응 검사, 누락 NTP 기본값 보완 |
| 미검증 | 물리 전원 재인가, 나머지 LAN 케이블 시험, RF 출력·최대 처리량·장기 안정성·실제 복원 |

기존 실기의 무선은 시험 전 disabled 상태로 복구했습니다. 당시 Argon/한글은 별도 설치했으며, **새 공개 r1에는 처음부터 포함**했습니다. 새 배포본에도 일반 sysupgrade 차단을 유지합니다.

관리자의 **네트워크 → 최대 송신 출력**은 두 대역의 **최대 출력(자동) / 수동 상한**을 기존 무선 설정과 연동합니다. 현재 드라이버 허용 범위를 사용하며 구형35dBm 패치는 포함하지 않습니다. [확장 소스](luci/README.md), LED/NTP, 대역 이름 표시도 공개 r1에 포함했습니다.

2026-10-27의 **[LED·시간 설정 소스와 적용/복원 방법](device-settings/README.md)**도 별도로 제공합니다. 무선 목록의 **2.4GHz Wi-Fi / 5GHz Wi-Fi** 표시는 별도 화면 리소스로 보완한 뒤 사용자 화면 확인까지 마쳤습니다. [적용/복원](luci/README.md#대역-표시-적용)과 최초 실패 기록을 함께 제공합니다.

## 자료 찾기

| 자료 | 용도 |
|---|---|
| **[설치 안내](INSTALLATION.md)** | 처음 설치하는 사용자용 기준 문서 |
| **[다운로드 파일·새 배포본 검증 범위](docs/PUBLIC_RELEASE_R1.md)** | RAM FIT·UBI·도구와 실기 미검증 항목 |
| [재현 빌드](firmware/BUILD.md) | 공식 kernel/패키지, 소스·캐시·이미지 생성 |
| [최신 설정·통신 검증](docs/POST_INSTALL_SETTINGS_20261027.md) | WAN·LED·NTP·화면 표시·실패 수정 결과 |
| [LED·NTP 적용/복원](device-settings/README.md) | 실제 적용한 소스, 빌드 및 별도 적용 절차 |
| [최종 NAND·Wi-Fi·UI 검증](docs/OPENWRT_25_12_6_NAND_WIFI_UI_20261026.md) | 결과와 기능별 검증 범위 |
| [실패·수정 이력](docs/EXPERIMENT_LOG_20261026.md) | 오류가 발생했을 때 원인 대조 |
| [RAM/PHY 시험](docs/OPENWRT_25_12_6_RAM_TEST_20261026.md) | 포팅 과정의 기술 근거 |
| [설치 제약 분석](OPENWRT_INSTALLATION_ANALYSIS_REPORT.md) | 제조사 U-Boot/FIT/파티션 설명 |
| [하드웨어·미검증 아이디어](RESEARCH_NOTES.md) | 기존 README 원문 보존, 설치 순서와 구분 |
| [개발 인수인계](docs/HANDOFF.md) | 배포 작업을 이어갈 개발자용 |
| **[순정 관리자 정적 검증·남은 과제](docs/STOCK_FIRMWARE_ADMIN_ANALYSIS_UNVERIFIED.md)** | 2026-10-30 인증·암호화·포트·제조사 업그레이드 형식 오류 정정. 순정 실기 로그인·웹 OpenWrt 설치는 미검증 |
| **[순정 롬/펌웨어 덤프 안내](dumps/README.md)** | 온보드 NOR 부트로더, NAND 128MB 전체 덤프(xz), Rootfs, Kernel 다운로드 및 언팩 가이드 |

미검증 실험 아이디어와 분석 기록을 보존합니다. 순정 롬 덤프 원본은 외부 분석 및 복구를 위해 [GitHub Releases: stock-dump-v1.4.0](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/stock-dump-v1.4.0)에서 제공하며, 공개 OpenWrt 설치 이미지는 공식 구성요소에서 새로 제작되었습니다.
