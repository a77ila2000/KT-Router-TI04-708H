# TI04-708H 다음 작업 인수인계

정리 기준: **2026-10-26, 한국 시간**. 최신 결과는0절과8절 및 연결된 보고서를 우선합니다.1~7절은2026-10-22 당시의 조사·준비 기록을 보존한 것으로, ‘아직 미확인/미수행’은 당시 상태입니다. IP·COM·프로세스·케이블 상태는 재개할 때 다시 확인합니다. README 3~6절의 실험 아이디어는 원문 보존했습니다.

## 0. 최신 상태와 다음 작업

**완료:** NOR 환경4KiB 재기록과 전체 readback, ESC U-Boot 콘솔, NAND 전체 백업, OpenWrt NAND 영구 설치와 자동 부팅2회, overlay 저장 파일 유지, NOR 및 NAND 뒤96MiB 해시 보존, 유선 ping/LuCI 로그인 화면.

**미검증:** 물리 전원 차단/재인가, 실제 DHCP 클라이언트 임대, WAN 인터넷, RF 송수신·출력 및 장기 안정성.

후속 [25.12.6 RAM 시험](OPENWRT_25_12_6_RAM_TEST_20261026.md)에서 최신 kernel6.12.112 부팅과 QCA8075 드라이버 수정, 유선1Gbps·실제 DHCP 임대·LuCI·무선 PHY2개 초기화를 확인했습니다. 이 DHCP 결과는25.12.6 RAM 환경의 결과이며 위23.05.3 설치 검증과 구분합니다. 노출된10개 플래시 파티션 SHA 보존 후 NAND23.05.3으로 복귀했습니다. 25.12.6 영구 설치는 아직 없습니다. 새 kernel이 기존96 LEB kernel 볼륨보다 커 앞32MiB UBI 재구성이 필요합니다.

- [종합 보고서](../OPENWRT_INSTALLATION_ANALYSIS_REPORT.md)에 GPIO·웹 로그인·압축·FIT·파티션 단정을 수정했습니다.
- [실험·실패 이력](EXPERIMENT_LOG_20261026.md)에 첫 CRC 실패, PC 수신기 종료/프롬프트 감지 버그, TFTP 초기 실패, LZMA 부팅 실패, 실행 전 중단과 도구 차단을 구분했습니다.
- 마지막 실기 환경은 **NAND kernel + SquashFS /rom + UBIFS /overlay**입니다. 순정 bootipq의 `config@5` 선택으로 자동 부팅2회, ESC 송신0/TFTP 없음, 저장 파일 유지를 확인했습니다. 재개 시 MTD 이름·경계·flags를 다시 확인합니다.
- 현재 DTB에서 NOR 전부와 뒤96MiB `stock-reserved`는 read-only, 앞32MiB `rootfs`에 UBI가 attach돼 있습니다. 설치 때의 `install-target` 이름과 현재 이름을 혼동하면 안 됩니다.
- 최초 UBI는20,447,232바이트, SHA256 `addf531e520fd97481ce4ded91ea1677ec2175bd0d65837d54072d96b931237b`입니다. **수정 전 kernel이 들어 있어 최종 복구 이미지로 단독 재사용하면 안 됩니다.** 최종 kernel FIT는12,143,380바이트, SHA256 `005b1808fc0c365c3bf1a86cf4e4cacd667f01f9f38366cc426f0b6e188df277`이며 kernel 볼륨만 추가 갱신·검증했습니다. 바이너리·원본 로그·장비별 데이터는 비공개 보관입니다.
- 첫 NAND 부팅은 root 인자 불일치로 panic했습니다. DTB의 파티션 이름 `rootfs` 및 `bootargs-append`의 ubiblock root로 해결했습니다. 상세 실패·수정 근거는 종합 보고서8절과 실험 기록9절을 확인합니다.
- 다음 작업은 로컬 root 암호 설정과 필요 기능 검증입니다. DHCP 활성·dnsmasq 실행은 확인했지만 실제 임대는 미시험이고, 두 라디오는 disabled입니다. 관리 화면은 LuCI 로그인 HTML로 응답합니다. 일반 sysupgrade를 재사용하지 않습니다.
- 원래 sysupgrade TAR를 재사용하면 LZMA/보드 config/128MiB 범위 문제가 재발할 수 있습니다. 준비된 후보는 순정 U-Boot용 비압축 FIT와 config 이름 및32MiB 경계가 반영된 별도 이미지입니다.
- 일반 웹 UI와8801에 대해 업로드 기능 부재나 원격 관리 전용을 단정하지 않습니다. 로그인 시험은 재개하지 않습니다.

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
| 영구 설치 | 앞32MiB 기록/readback 후 첫 root mount panic을 DTB로 수정. kernel 볼륨 재기록/readback, NAND 자동 부팅2회 및 overlay 저장 파일 유지 확인. NOR/뒤96MiB 해시 불변 |

원본 NOR 대비31바이트 수정, 실제4KiB 기록 단위, 기록 직전 기본 환경 대비248바이트 차이를 구분합니다. 해시 일치는 읽기/파일 무결성의 근거이며 무위험·언제든 완전 복원 가능성을 보장하지 않습니다. GPIO63=SW4 및 ‘1초 내 문자열’ 단정은 정정했고 버튼 조합 시험에서는 프롬프트를 확인하지 못했습니다.
