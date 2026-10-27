# TI04-708H 다음 작업 인수인계

> 이 문서는 개발자 인수인계입니다. 사용자용 기준 문서는 [설치 안내](../INSTALLATION.md)입니다. 다음 배포 작업은 [공개 릴리스 완료 조건](../INSTALLATION.md#8-공개-릴리스-완료-조건)을 기준으로 진행합니다.

정리 기준: **2026-10-27, 한국 시간**. 최신 결과는0절과 [설치 후 기록](POST_INSTALL_SETTINGS_20261027.md)을 우선합니다.1~7절은2026-10-22 당시의 조사·준비 기록을 보존한 것으로, ‘아직 미확인/미수행’은 당시 상태입니다. IP·COM·프로세스·케이블 상태는 재개할 때 다시 확인합니다. 기존 README 3~6절의 실험 아이디어는 [보존본](../RESEARCH_NOTES.md)에 원문 보존했습니다.

## 0. 최신 상태와 다음 작업

**현재 OpenWrt25.12.6 / Linux6.12.112가 NAND에서 실행됩니다.** 정상 NAND 부팅·저장 유지·두 대역 송수신에 이어 WAN DHCP/DNS/NAT·인터넷과 실물 LAN4 관리를 확인했습니다. 앞선 ‘실물 LAN1’ 표현은 번호 미확정 당시 기록이며 사용자 확인으로 실제 케이블 위치는 LAN4입니다. Argon3.1.0·한글 기본·English 선택은 이전 재부팅 후 유지됩니다.

**미검증:** 물리 전원 재인가, 나머지 LAN 케이블 시험, 보정된 RF 출력·최대 처리량·장기 안정성, 실제 백업 복원. 브라우저 화면 클릭·렌더링은 직접 검증하지 않았습니다. 무선 대역 표시는 별도 리소스 `network/ti04-wireless-bands`와 실행 band fallback 적용 후 사용자 화면 확인을 마쳤습니다. 원래 vendor 무선 view는 복원했고 메뉴 action 경로만 변경했습니다.

- WAN·LAN4 LED 실물 확인, 공용 Wi-Fi LED 두 대역의 밝기/활동 시험을 마쳤습니다. LAN1~4 표시등은 PHY4/3/2/1에 매핑합니다. [소스와 적용/제거](../device-settings/README.md)는 별도 overlay이며 기존 UBI에 포함되지 않았습니다.
- NTP 기본 구성 누락을 보완하고 서비스·시각 일치를 확인했습니다. 두 라디오는 시험 전 비활성 상태로 복원했습니다. 개인 인증·세션·키는 공개하지 않습니다.

- 현재 결과는 [25.12.6 NAND·Wi-Fi·UI 기록](OPENWRT_25_12_6_NAND_WIFI_UI_20261026.md), 이전 단계는 [RAM 시험](OPENWRT_25_12_6_RAM_TEST_20261026.md), 과거23.05 첫 설치 실패·수정은 [종합 보고서8절](../OPENWRT_INSTALLATION_ANALYSIS_REPORT.md#8-23053-nand-설치와-첫-부팅-실패-수정)과 [실험 이력](EXPERIMENT_LOG_20261026.md)을 확인합니다.
- 설치 직전23.05.3 앞32MiB를 새로 백업하고 CRC/SHA를 대조했습니다.25.12.6 kernel이 기존96 LEB보다 커 앞32MiB UBI를 재구성했습니다. kernel105/rootfs37 LEB, 나머지는 rootfs_data입니다.
- 현재 kernel FIT SHA256은 `f649a082fad2d533fa025ae001b2a9f8d2fac4abde0c8d7c6fce2b7abbdf3c8f`, root SquashFS는 `1cb64149ac20dde13cc08dcace4b5b6a3166b7eacec2b9672c1c81f09cd38c25`입니다. 기록한 UBI는18,874,368바이트, SHA `d1210a4889bd0ed175080fb4f580889358fb3cc816addd9162ee716234abba04`입니다. 바이너리·로그·인증 백업은 비공개 보관합니다.
- 마지막 root는 NAND kernel + SquashFS /rom + UBIFS /overlay입니다. `TI04_2512_NAND_verified` 파일과 UI 설정이 유지됐습니다. 재개 시 MTD 이름·경계·flags를 다시 확인합니다. 현재 앞32MiB 이름은 `rootfs`, 뒤96MiB는 `stock-reserved`입니다.
- NOR 전부 및 뒤96MiB는 쓰기 비활성, 앞32MiB만 쓰기 가능입니다. 이번 마지막 SHA 검사 대상은 NOR8개 노출 파티션(1.5MiB)과 뒤96MiB이며 이전 프로그래머 전체2MiB readback과 구분합니다.
- 무선 시험 후 PC 원래 Wi-Fi 연결과 공유기 wireless 설정을 복원했습니다. 두 라디오는 disabled이며 임시 CGI·payload는 제거했습니다. 사용자가 자리를 비워 케이블을 이동하거나 물리 전원을 조작하지 않았습니다.
- 언어 변경은 **시스템 → 시스템 → 언어 및 스타일 → 언어 → English → 저장 및 적용**입니다. 영문 응답을 시험한 뒤 ko로 복귀했고 재부팅 후 유지됐습니다. 마지막 overlay 여유는 약7.1MiB입니다.
- root 암호는 초기 이미지에서는 비어 있었으나 후속 작업 때 사용자 암호 인증을 확인했습니다. 현재 암호를 추측하거나 빈 암호로 반복 시험하지 않습니다. 일반 sysupgrade는 차단 상태입니다.
- 과거23.05 최초 `addf531e…` UBI에는 root 인자 수정 전 kernel이 들어 있습니다. 복귀용 후보는 수정 kernel을 포함해 별도로 준비·오프라인 검사했으나 실제 복원은 미시험입니다. 단독 원본 NOR 백업이 NAND까지 포함하는 복구본은 아닙니다.
- UART 수신기는 백그라운드 수신 전용으로 복원했습니다. 조작 전 현재 소유 프로세스/COM/뮤텍스와 송신 기록을 확인하며 대화 문장을 UART에 붙여 넣지 않습니다.
- 일반 웹 UI/8801 업로드 기능 부재나 원격 관리 전용을 단정하지 않습니다. 로그인 시험은 재개하지 않습니다. 기존 실험 아이디어는 보존했습니다.

## 1. 2026-10-22 당시 조사와 남은 질문

| 분야 | 수행/관찰 | 결론의 한계 |
| --- | --- | --- |
| 8899 일반 웹 관리 | 시스템 관리 페이지와 공통 JavaScript 확인 | 조사 범위에서 펌웨어 업로드 경로 미발견. 장비 전체의 업데이트 기능 부재 증명은 아님 |
| 8801 별도 관리자 | 알려진 로그인 화면 및 사용자 제공 후보 일부 확인 | 성공 인증/메뉴 확보 없음. UART/bootdelay 설정 존재도 미확인 |
| DDNS | 기능/코드 조사 후 비활성·빈 값 상태로 복원한 기록 | 명령 실행이나 UART 복구 경로 확보로 해석하지 않음 |
| 설치 후보 2개 | Binwalk/TAR·메타데이터·rootfs/DTB 검사 | 순정 덤프가 아니라 OpenWrt sysupgrade 후보. 포함 DTB는 순정 파티션 주소 근거가 아님 |
| CH343 UART | 루프백과 부팅 로그·수동/자동 송신·반환 에코 구분 | 어댑터 정상과 U-Boot 입력 처리 정상은 별개 |
| 버튼 부팅 | 초기화 버튼 약 8초 유지, 부팅/UART·유선 관찰 | 복구 셸/TFTP 대기 확인 없음. 설정 초기화/재부팅이 섞여 있음 |
| CH341A 준비 | 프로그래머·클립·SOIC8·1.8V 어댑터 세트 구매 보고 | 실물 안전 전압·NOR 읽기·쓰기·복원 시험은 아직 없음 |

웹 로그인 시험의 마지막 저장 기록은 준비된 72개 중 `nextIndex=25`, 요청 35회, 앞선 별도 실패 2회였다. 잠금 응답의 재시험이 포함되므로 **35개의 서로 다른 후보가 모두 실패했다는 뜻이 아니다.** 성공 인증은 없었다. 2026-10-21 20:43경까지 연결 오류가 5회 누적됐고, Windows에서 공유기용 유선 어댑터/IP도 확인되지 않아 `ti04` 로그인 자동화를 삭제해 중지했다. 이번 문서 정리에서는 계정 시험/공유기 조작을 재개하지 않았다.

## 2. 환경 패치 이전 UART 증거

- 수신 배너는 `TI04-708H`, `U-Boot 2012.07`, DRAM 256MiB, NOR 2MiB + NAND 128MiB였다.
- 13:01경 Esc 전용 시험 3회에서 PC 쓰기 합계 197바이트가 기록됐다. autoboot 문구를 관찰한 뒤에도 송신했지만 세 번 모두 UBI/커널로 진행했고 U-Boot 프롬프트가 없었다. PC 쓰기 성공이 모든 바이트의 SoC 도달을 증명하지는 않는다.
- 13:34경 사용자가 `g`를 두 번 누른 사실을 확인했다. 실제 UART 원본에서 각 쓰기 약 31ms/17ms 후 `g`가 반환됐다. Linux 초기 구간이며 기록기가 넣은 로컬 에코가 아니다.
- 후속 부팅에서도 커널 시작 뒤 literal `^[` 에코가 있었다. Esc 바이트를 그대로 반환한 전선 루프백과 다르며 Linux TTY의 제어문자 에코와 부합한다. 셸 진입이나 실행 중 termios 값을 직접 읽은 증거는 아니다.
- Enter 두 번의 PC 쓰기는 기록됐지만 직후 줄바꿈·셸·로그인 반환을 확인하지 못했다.
- 과거 표시기의 약 200ms 출력 간격을 실제 키 입력 허용 시간으로 환산하지 않는다. 로그 표시 폴링 지연이 포함될 수 있다.

따라서 “UART TX가 항상 막혔다”, “원인은 무조건 bootdelay=0이다”, “입력 핀을 바꾸면 된다”는 결론은 근거가 부족하다. Linux 입력 경로 동작과 U-Boot 중단 제한을 구분해 분석한다. CN1 ①은 약 3.3V 측정만으로 VCC가 확정되지 않았다. 사각 패드 모양 역시 전원 기능의 증거가 아니다.

## 3. 순정 부팅 로그 발췌

전체 원본 대신 기기 고유 값이 없는 부분만 옮겼다. 용량·메모리 종류는 사진 추정보다 이 실기 로그를 우선한다.

```text
TI04-708H
U-Boot 2012.07
DRAM:  256 MiB
NAND:  spi_nand: spi_nand_flash_probe SF NAND ID 0:c2:12:c2
SF: Detected MX35LFxGE4AB with page size 2 KiB, total 128 MiB
SF: Detected GD25Q16 with page size 4 KiB, total 2 MiB
ipq_spi: page_size: 0x100, sector_size: 0x1000, size: 0x200000
130 MiB
Press any key to stop autoboot:  0
```

사진의 SoC 마킹은 IPQ4018이다. 공용 커널 DTB/머신 모델 문자열만으로 실물 칩을 IPQ4019로 바꾸어 기록하지 않는다. 단, 사진과 로그가 모든 보드 리비전에서 동일한 구성을 증명하지는 않는다.

## 4. 원본과 분석 자료의 출처

아래 자료는 기존 로컬 조사 폴더에서 대조했으며 **공개 저장소에 원본을 복사하지 않았다.** 파일명은 인수인계용 식별자다.

- `TI04-708H_VERIFIED_INSTALL_PATH.md`: 웹·후보 이미지·UART 시험의 누적 기록. 앞부분 초기 상태보다 후속 21~26절의 결과를 우선한다.
- `TI04-708H_UART_FINDINGS_20261021.md`: UART 해석 기록.
- `TI04-708H_CH341A_READONLY_PLAN.md`: 2026-10-22 읽기 전용 준비 계획.
- `uart-20261021-133347.bin` 및 대응 송신 감사 기록: 부팅 로그·문자/제어문자 반환. 읽기 전후 오프셋/시각을 구분했다.
- `uart-20261021-130112.bin` 및 대응 송신 감사 기록: Esc 전용 3회 시험. 모든 보관 로그를 전체 문맥 검토한 것은 아니다.
- `standard-binwalk.json`, `high-power-binwalk.json` 및 후보 TAR/DTB: 설치 후보 분석. 순정 부트로더/환경 덤프가 아님.
- 비공개 로그인 `status.json`: 진행/잠금/연결 오류 기록. 암호·세션은 공개하지 않는다.

### 설치 후보 식별용 SHA-256

다음은 보관한 파일의 식별값이지 설치 허가·호환성 인증이 아니다. 펌웨어 파일은 이 저장소에 포함하지 않는다.

| 파일 | SHA-256 |
| --- | --- |
| `openwrt-kt9200-standard.bin` | `D78899AAB90D8697FB1E198908DE76D8088393D3A2C27421F58223F01440CB3E` |
| `openwrt-kt9200-high-power.bin` | `5450D4C4C9D08274639FBC79B882D81850D066DA8DB6143ABDA2DF0BD97CF40C` |

두 파일은 OpenWrt 23.05.3, `ipq40xx/generic`, `BOARD=giga_kt-9200`용 sysupgrade TAR이며 kernel/root를 포함한다. APPSBL/U-Boot payload나 최초 RAM 부팅 이미지가 아니다. 배포자가 이미 호환 부트 환경이 준비된 장비를 전제로 한다는 조사 기록이 있지만, 정확한 최초 전환 절차와 TI04 실기 호환성은 확보하지 못했다. **이 TAR를 순정 NOR에 통째로 기록하지 않는다.**

## 5. 기존 실험 아이디어를 평가할 때

기존 README의 제안은 삭제하지 않았다. 아래는 제안별 **검증 상태/필요 조건**이지 실제 시험 결과가 아니다.

| 기존 제안 | 아직 필요한 확인 |
| --- | --- |
| `bootdelay` 환경 수정 | 실제 저장 환경의 위치·크기·CRC·중복 활성 선택, 코드의 환경 참조 여부. 문자열 발견/치환만으로 성공을 보장하지 않음 |
| 입력 차단 코드 분석 | 표준 `CONFIG_AUTOBOOT_KEYED`는 입력 제거가 아니라 중단 문자열 검사. 실제 제조사 바이너리의 분기를 확인해야 함 |
| 플래시 신호 오류 유도/글리칭 | TI04에서 복구 프롬프트·UART 활성화 결과를 확인하지 못함. 손상·버스 충돌·부트 실패 위험이 있어 지금 연결 지침으로 사용하지 않음 |
| RESET 접지/동시 전원/칩 분리 | 회로·전압·역급전 경로·패키지와 작업 가능성 확인 필요. 읽기 실패 시 자동으로 넘어가는 단계가 아님 |
| 버튼 홀드/TFTP 복구 | 시행한 초기화 시험에서는 복구 셸/대기 IP를 확인하지 못함. 공장 초기화와 구분 필요 |
| 공통 initramfs/TFTP 예제 | TI04 전용 이미지·DTB·RAM 주소·지원 명령·플래시 미기록 동작을 검증해야 함. 플랫폼 지원만으로 보드 호환성을 보장하지 않음 |

임의 환경 오프셋·공통 이미지 주소를 확정값으로 사용하지 않는다. UART 복구와 OpenWrt 설치 가능성은 별도로 판정한다. RAM 부팅도 이미지/초기화 코드 검토가 필요하며 무조건 무위험한 것은 아니다.

## 6. 2026-10-22 당시 CH341A 준비 체크리스트

현재 단계는 **연결 준비와 읽기**다. 이 목록 자체가 쓰기 승인은 아니다.

- [ ] 프로그래머 앞·뒷면, 점퍼, 어댑터, 클립 배선 사진 확인.
- [ ] 목표 `GD25...` 칩 전체 마킹·접미사·패키지·핀 1·실장 위치 확인. `U33` 등 위치를 추측하지 않음. WSON/USON이면 SOP8 클립이 맞는다고 가정하지 않음.
- [ ] 칩을 물리지 않은 프로그래머의 VCC/신호 출력 전압과 칩 데이터시트 대조. GD25Q16C는 2.7~3.6V이며 1.8V 어댑터를 무조건 사용하지 않음.
- [ ] 공유기 전원·LAN·USB–TTL 등 분리, 프로그래머 USB도 뺀 상태에서 배선 확인. 초기 시험에 동시 전원/핀 쇼트/리셋선 접지 실험을 섞지 않음.
- [ ] Windows USB 장치와 드라이버, 사용 소프트웨어·버전·실제 칩 지원 확인. WSL 사용 시 USB 전달 가능성도 별도 확인.
- [ ] JEDEC 식별 안정성과 2MiB 용량 확인 후 Read만 3회. Erase/Program/Write/Auto/Unprotect/강제 칩 선택 없이 진행. 불안정하면 중단하고 원인 조사.
- [ ] 서로 다른 파일 3개에 예상 크기 2,097,152바이트와 반복 일치 검사. 원본 이중 보관, 분석은 복제본에만 진행.
- [ ] 전부 FF/00·반복 패턴·비정상 헤더 검토. 일치 해시만으로 유효 원본 판정하지 않음. 실패 원인을 접촉 불량 하나로 단정하지 않음.
- [ ] 부트로더/환경 후보의 경계·CRC·중복 선택 규칙·실제 참조 코드를 분석. ART/보드별 데이터·부트 체인·무결성 검증을 보존.
- [ ] 환경 수정 후보/코드 수정 필요 여부를 판단한 뒤, 복원 수단과 변경 범위를 설명하고 별도 쓰기 승인을 받음.

2MiB NOR만 읽어서는 128MiB NAND나 전체 복구 데이터가 확보되지 않는다. NAND의 지원 도구·OOB/ECC·배드블록/논리 읽기 형식을 따로 정한다. 원본 전체 읽기에 OTP/보안 레지스터까지 포함된다고 가정하지 않는다.

Wi-Fi는 인터넷, 유선은 공유기 관리 전용이다. 관리 LAN에 인터넷 기본 게이트웨이를 다시 넣지 않는다. 과거 COM7·IP·프로세스는 현재 조회로 재확인한다.

Windows에 Ghidra가 설치되어 있거나 REA MCP가 연결되어 있어도 raw ARM 분석/펌웨어 provider가 자동 준비되는 것은 아니다. 기존 WSL/도구의 실제 지원을 확인하며 무관한 재설치를 선행하지 않는다. Binwalk 버전별 옵션을 확인하고 분석은 복제본·별도 출력 폴더에서 진행한다.

## 7. 공개/비공개 경계와 확인 방법

- `.gitignore`는 dump/extracted/openwrt 실제 내용과 펌웨어·로그·세션 등을 기본 제외하며 `.gitkeep`만 유지한다. 기존 추적 파일과 과거 커밋을 지우지는 않는다.
- 원본 UART/ROM/NAND, 계정 후보, 쿠키, 무선 키는 추가하지 않았다. 기존 이미지/본문의 라벨·QR·식별정보 비식별화는 이번 변경 범위가 아니다.
- 덤프 검사기는 파일만 읽는다. 최소 2개 입력(실제 작업은 3회 권장), 예상 크기 옵션, 빈/00/FF 입력·같은 파일/별칭 거부, 실패 종료 코드를 지원한다. 성공은 반복 일치만 확인한다.
- `python -m unittest discover -s tests -v`로 비기기 합성 데이터 회귀 검사를 실행한다.
- GitHub Actions는 같은 검사를 Python 3.12의 Windows/Linux에서 실행한다. 새 의존성 설치나 실기 연결은 없다.

## 참고 근거

2026-10-22 사양표 재검토: 부팅 원본에는 `S - DDR Frequency, 537 MHz`가 있으며 RAM의 DDR3L-1866 부품 등급과 구분했다. NANYA 공식 목록의 2Gb·x16·96-ball BGA는 기존 표와 일치한다. SKY85405의 PA+LNA+SPDT 통합 FEM 설명은 제조사 Product Summary와 달라 PA+전력 검출기로 정정했다. SoC는 최대 717MHz 제품 사양과 실기 동작을 구분했고, 칩 위치·패키지·미식별 RF/전원 부품·CN1 ①의 역할은 미확인으로 표시했다. 원본 사진과 실험 제안 구간은 수정하지 않았다.

- [Qualcomm IPQ4018](https://www.qualcomm.com/networking-infrastructure/products/ipq4018), [NANYA DDR3L 공식 목록](https://www.nanya.com/en/Product/List/450/7591), [Skyworks SKY85405-11 Product Summary](https://www.skyworksinc.com/-/media/B0BE21ADDC38445E93B967915E2A6B3A.pdf)
- [U-Boot v2012.07 입력 검사](https://github.com/u-boot/u-boot/blob/v2012.07/common/main.c#L83-L247), [환경 도구](https://github.com/u-boot/u-boot/blob/v2012.07/tools/env/README)
- [flashrom CH341A 전압 주의사항](https://github.com/flashrom/flashrom/blob/main/doc/supported_hw/supported_prog/ch341ab.rst), [인서킷 읽기 제약](https://github.com/flashrom/flashrom/blob/main/doc/user_docs/in_system.rst)
- [GigaDevice GD25Q16C](https://www.gigadevice.com/product/flash/spi-nor-flash/gd25q16c), [Macronix Serial NAND](https://www.macronix.com/en-us/products/NAND-Flash/Serial-NAND-Flash/Pages/default.aspx)
- [Linux N_TTY 에코](https://www.kernel.org/doc/html/latest/driver-api/tty/n_tty.html)


---

## 8. 2026-10-26 결과 요약

| 단계 | 최종 판정 |
|---|---|
| CH341A/NOR | U33 GD25Q16CSIG 2MiB 확인. 첫 수동 기록 CRC 실패 후 지정4KiB 재기록, 페이지/전체 readback 및 독립3회 읽기 통과 |
| UART | ESC2012 모드로 `(IPQ40xx) #`, 선택 명령 응답 확인. PC 감지기의 ESC 에코 처리 수정 후 자동 송신 중단/입력 활성화 성공 |
| 추가 제한 | debug_mode 값이 on일 때 제한 명령 동작. 세션에만 적용하고 환경 저장하지 않음 |
| NAND |128MiB ECC main +132MiB raw/OOB 백업 및256조각 검증. 순정 rootfs32MiB 경계 확인, 후반96MiB 보존 대상 |
| RAM OpenWrt | 비압축 kernel/FIT와 별도 initramfs로 부팅. LAN ping/HTTP200 및 PHY2개 초기화. RF/WAN은 미검증 |
| 23.05.3 설치 이력 | 앞32MiB 기록/readback 후 첫 root mount panic을 DTB로 수정. kernel 볼륨 재기록/readback, NAND 자동 부팅2회 및 overlay 저장 파일 유지 확인. NOR/뒤96MiB 해시 불변 |

원본 NOR 대비31바이트 수정, 실제4KiB 기록 단위, 기록 직전 기본 환경 대비248바이트 차이를 구분합니다. 해시 일치는 읽기/파일 무결성의 근거이며 무위험·언제든 완전 복원 가능성을 보장하지 않습니다. GPIO63=SW4 및 ‘1초 내 문자열’ 단정은 정정했고 버튼 조합 시험에서는 프롬프트를 확인하지 못했습니다.

## 9. 후속25.12.6 결과

25.12.6 NAND 설치·정상 부팅3회·저장 유지·무선 두 대역 양방향 전송·Argon3.1.0 및 한글/영문 선택까지 완료했습니다.0절과 [후속 보고서](OPENWRT_25_12_6_NAND_WIFI_UI_20261026.md)가 최신 상태입니다.8절의23.05.3 설치와1~7절의 준비 기록을 현재 미수행 상태로 해석하지 않습니다.

## 10. 다른 사용자용 배포 작업

README를 설치 진입점으로 바꾸고 기존 하드웨어·미검증 아이디어 원문은 루트의 `RESEARCH_NOTES.md`로 보존했습니다. 신규 사용자는 개발 로그의 개인용 파일명/해시/COM/IP/MTD 번호를 복사하지 않도록 `INSTALLATION.md`로 안내합니다.

현재 로컬 패처는 작성자의 원본 NOR SHA, 설치기는 작성자 장치/경로/백업/보존 해시에 고정돼 있습니다.25.12.6 rootfs는 이전 root 인증 정보와 Dropbear host key를 포함합니다. 이를 그대로 공개하거나 작성자 전체 NOR를 다른 기기에 복제하는 방식으로 배포하지 않습니다. 개인 데이터 없는 이미지 또는 재현 빌드, 원본별 환경 패치, 사용자별 guard/백업, 공개 manifest·도구·다운로드, 다른 순정 장비의 처음부터 끝까지 재현 시험이 남아 있습니다.

목표 설치 경로는 검증된 설치용 RAM에서 최종25.12.6 UBI를 앞32MiB에 기록하는 흐름이며23.05.3 NAND 선행 설치를 요구하지 않도록 준비합니다. 이 전체 직행 경로의 새로운 순정 장비 재현 검증이 끝나기 전에는 ‘누구나 한 번에 성공’ 또는 공개 릴리스 완료로 표시하지 않습니다. 이번 문서 정리에서는 실기 플래시/재부팅을 수행하지 않았습니다.

## 11. 관리자 무선 출력 프로필

사용자는 구형35dBm 고정 요청 방식 대신 **현재 드라이버 허용 최대 출력** 프로필을 선택했습니다. [LuCI 확장 소스](../luci/README.md)의 두 파일을25.12.6 overlay에 설치했습니다. 기본 NAND UBI는 재작성하지 않았습니다.

메뉴는 네트워크 → 최대 송신 출력, route는 `admin/network/ti04-power`입니다. 대역별 `wireless.<radio>.txpower`만 기존 LuCI/iwinfo API로 다루고, 자동은 해당 수동값을 제거합니다. 나라·채널·무선 활성화·드라이버는 바꾸지 않았으며 설치 전후 실제 wireless 파일SHA는 같았습니다. 두 radio는 disabled 상태입니다. Node 동작 검사, live menu satisfied/JS HTTP200 및 해시, 별도 임시UCI 수동→자동 검사는 통과했고 브라우저 렌더링/클릭 저장은 미확인입니다. 기존 UBI와 옵션 소스의 포함 관계를 배포 manifest에 명시해야 합니다.
