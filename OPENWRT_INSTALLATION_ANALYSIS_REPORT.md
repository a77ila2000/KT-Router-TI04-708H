# TI04-708H OpenWrt 진행 결과와 설치 제약

기록 기준: **2026-10-26, 한국 시간**. 사용자 소유 allRadio TI04-708H 한 대에서 확인한 결과다. 초기 검토 문서의 단정과 이후 실기 결과를 구분해 갱신했다.

**현재 완료: NOR 환경 패치, U-Boot 양방향 콘솔, NAND 전체 백업, OpenWrt NAND 영구 설치, ESC/TFTP 없는 자동 부팅2회 및 overlay 저장 파일 유지. NOR 전체와 NAND 뒤96MiB의 해시 보존 및 유선 ping/LuCI 로그인 화면 확인. 미검증: 물리 전원 재인가, DHCP 클라이언트 임대, WAN 인터넷, 실제 무선 송수신·장기 안정성.**

- 시행 순서와 실패 원인: [실험·실패 이력](docs/EXPERIMENT_LOG_20261026.md).
- 다음 작업과 과거 조사: [인수인계](docs/HANDOFF.md).
- 원래 README 3~6절의 미검증 실험 아이디어는 보존했다. 해당 예제보다 이 문서의 실기 결과를 우선한다.

## 1. 실제 확인한 하드웨어와 저장 영역

| 항목 | 확인 결과 / 한계 |
|---|---|
| SoC / RAM | IPQ4018, 256MiB. 순정 로그의 `DDR Frequency, 537 MHz`는 관측 표기이며 RAM 부품의 DDR3L-1866 등급과 구분 |
| NOR | U33, GD25Q16CSIG, SOP-8, JEDEC `C8 40 15`, 2MiB. CH341A로 독립 읽기와 기록 후 검증 수행 |
| NAND | Macronix SPI NAND, 128MiB. 순정 표기는 `MX35LFxGE4AB`, 실물 전체 접미사는 미확정 |
| NAND geometry | page2048 / OOB64 / erase131072바이트. 순정 U-Boot와 OpenWrt에서 관측 |
| UART | 115200 8N1. 사용한 CN1 배선은 ②→어댑터 RX, ③←어댑터 TX, ④→GND. ①은 미연결; 전압만으로 VCC 역할을 확정하지 않음 |
| 버튼 | SW1 FACTORY RESET, SW3 WPS, SW4 RESET 라벨 확인. GPIO2/63과 각 스위치의 전기적 대응은 미확정 |
| 무선 | SKY85405 계열은 5GHz PA+전력 검출기. 2.4GHz의 외부 RF 부품·구성은 이 결과로 단정하지 않음 |

순정 `smeminfo`가 표시한 영역은 다음과 같다. 끝 주소는 포함하지 않는다.

| 저장 장치 | 파티션 | 범위 |
|---|---|---|
| NOR | SBL1 | `0x000000–0x040000` |
| NOR | MIBIB | `0x040000–0x060000` |
| NOR | QSEE | `0x060000–0x0C0000` |
| NOR | CDT | `0x0C0000–0x0D0000` |
| NOR | DDRPARAMS | `0x0D0000–0x0E0000` |
| NOR | APPSBLENV | `0x0E0000–0x0F0000` |
| NOR | APPSBL | `0x0F0000–0x170000` |
| NOR | ART | `0x170000–0x180000` |
| NAND | 순정 rootfs/UBI | **`0x0000000–0x2000000` (앞32MiB)** |
| NAND | 보존 대상 후반부 | `0x2000000–0x8000000` (뒤96MiB), 다른 UBI sequence의 데이터도 관측 |

**물리 NAND가 128MiB라는 사실은 전체를 하나의 설치 대상으로 지워도 된다는 뜻이 아니다.** 이전의 128MiB 전체 `ubi` 후보 DTS는 실제 순정 부팅 범위와 달랐다.

## 2. 웹·버튼 경로에 대한 정정

| 이전 표현 | 증거에 맞춘 판정 |
|---|---|
| 8899/8801 모두 로컬 업로드 기능 없음 | 확인한 일반 관리 화면·공통 스크립트에서 업로드 경로를 확보하지 못했다. **8801 인증 후 메뉴는 확보하지 못했으므로 기능 부재를 단정하지 않음** |
| 관리자 암호 72개 모두 실패 | 마지막 보존 상태는 준비72개 중 `nextIndex=25`, 요청35회 및 앞선 별도 실패2회. 잠금 재시험이 포함돼 요청 수를 서로 다른 암호 수로 계산할 수 없음. 성공 인증 없음 |
| 기기 식별값+비공개 salt로 암호 생성 확정 | `Change admin id/pwd by kt hash string` 로그는 근거지만, 정확한 입력·알고리즘·salt·생성 규칙은 복원하지 못함 |
| 펌웨어는 TR-069 전자서명 푸시로만 업데이트 | 원격 관리 경로의 단서와 로컬 메뉴 미발견을 업데이트 방식의 독점성·서명 검증 증명으로 확대하지 않음 |
| 네트워크 취약점 경로 불가능 | 시행한 DDNS/UPnP/포트 조사에서 UART 제어·명령 실행·업로드 경로를 확보하지 못한 결과. 전체 취약점 부재의 증명은 아님 |
| GPIO63=SW4, SW1+SW4로 진입 가능 | 후보 DTS의 reset GPIO 번호와 실물 SW 번호는 별개. 실제 조합 시험에서는 프롬프트를 확인하지 못함 |

로그인 반복 시험은 중단된 과거 조사다. 이 문서 갱신 과정에서 로그인 후보 추가나 새 인증 요청을 하지 않았다.

## 3. 제조사 autoboot와 추가 명령 제한

대상 APPSBL은 NOR에서 추출한 U-Boot 2012.07이다. 아래 주소는 링크 가상주소이며 모든 실행 시점의 재배치 주소라는 뜻은 아니다.

| `bootdelay` 값 | 내부 모드 | 이 바이너리에서 확인한 동작 |
|---|---|---|
| `0`, 또는 `2`/`2012` 이외의 값 | 0 | GPIO2/63 관련 raw 레지스터 값 검사와 추가 UART 문자열 비교 경로. 일반 ESC 카운트다운과 다름 |
| `2` 또는 미설정 | 2 | GPIO 검사 경로. 일반적인 ‘2초 키 입력 대기’로 해석하면 안 됨 |
| `2012` | 1 | GPIO 검사를 건너뛰고 ESC `0x1B`를 검사. 실기에서 `Press ESC to stop autoboot: 1` 확인 |

- autoboot 주요 구간: `0x8731AD54–0x8731AF50`.
- GPIO 조회 함수 `0x87302734`는 해당 raw 레지스터 값을 반환한다. 두 핀을 단순히 접지/LOW로 만들라는 지침으로 바꿀 수 없다.
- mode0의 추가 문자열 대기는 코드상 무입력 약10초 경로이며, 기존 보고서의 ‘1초 내’ 단정은 정정한다.
- mode1의 ESC 폴링은 약0.5초로 해석되는 코드다. `2012`는 초 단위 대기 시간이 아니다.
- 초기 공백·ESC·숫자 송신과 버튼 조합은 프롬프트 진입에 실패했다. 성공한 경로는 다음 절의 환경 패치다.

**프롬프트 진입 후에도 추가 제한이 있었다.** `help`, `nand read`, `tftpput`이 에코만 남기고 돌아오는 현상을 확인했다. 공통 함수 `0x873042C4`가 `debug_mode` 값과 정확한 문자열 `on`을 비교하고, 제한된 명령은 조건이 맞지 않으면 무출력 반환한다. 현재 세션에서만 `setenv debug_mode on`을 적용한 뒤 도움말·NAND 읽기·TFTP가 실제 동작했다. 이 목적에 `saveenv`는 실행하지 않았다.

## 4. NOR 패치: 첫 실패와 검증된 재기록

1. 원본 NOR 독립3회 읽기는 크기2,097,152바이트 및 SHA가 일치했다. 이는 NOR 사용자 영역 백업이며 NAND/OTP나 완전한 복원 시험을 대신하지 않는다.
2. APPSBLENV는64KiB다. CRC는 헤더4바이트를 제외한65532바이트에 대해 계산했다. 의도한 최종 변경은 원본 대비31바이트이며 모두 첫4KiB `[0xE0000,0xE1000)` 안에 있다.
3. 첫 수동 기록 뒤 **전원 인가 전 Verify를 확인하지 못했다**. 다음 부팅에서 `bad CRC, using default environment`가 발생했고 `bootdelay=2`로 부팅됐다. 최초 오류의 원인은 미확정이다.
4. 후속 readback은 CRC가 유효한 기본 환경이었다. 원본과의 차이는 환경 첫4KiB에만 있었다. `uboot_ver` 조건에 따른 자동 환경 저장 코드가 기본 환경의 후속 보존을 설명하지만, 최초 기록 실패 원인까지 입증하지는 않는다.
5. 17:23 KST, 지정4KiB 섹터 지우기1회와256바이트 페이지 프로그램16회를 실행했다. 섹터/페이지 확인, 전체2MiB readback 비교, 장치를 새로 연 독립3회 읽기가 모두 통과했다. 다른 NOR 영역은 원본과 일치했다.
6. 17:43 KST 첫 프롬프트를 확인했으나, ESC 되울림 때문에 PC 감지기가 이를 놓쳤다. 감지기를 수정한 뒤 17:50 KST 재시험에서 `(IPQ40xx) #`, 자동 ESC 중단, 키보드 활성화를 확인했다. `version`과 선택한 `printenv` 응답도 확보했다.

| 식별 대상 | SHA256 |
|---|---|
| 원본 NOR 2MiB | `c33402801b9c4484b20634303675fe7422b0dcde1e6e1d95c4fac790bea9d23e` |
| 재기록/검증된 ESC2012 NOR 2MiB | `826c074ace0f52ec7fbcffe0ff6e76ca0365041cb1000e01e5764f85d9d64b78` |

‘31바이트 수정’은 파일 차이다. 실제 지우기·기록 단위4KiB와 구분하며 전원·접촉·기록 실패 위험이나 복원 성공을 보장하지 않는다. APPSBL 본체를 교체하지 않았다.

## 5. NAND 전체 백업과 순정 UBI

U-Boot에서 앞부분부터 끝까지1MiB 단위로 두 종류를 읽어 전송했다. geometry와 raw 명령의 단위를 먼저 확인했다.

- 일반 `nand read`: ECC 처리 main 데이터.128개 조각, 합계128MiB.
- `nand read.raw`: 마지막 인자는 바이트 수가 아니라 페이지 수.2048+64바이트 페이지512개는1,081,344바이트다.128개 조각, 합계132MiB.
- 256개 파일의 offset coverage·크기·중복 없는 manifest·SHA 및 조립 후 재읽기 해시가 모두 통과했다.
- raw에서 OOB를 제거한 데이터와 ECC main은174바이트 달랐다. UART의 ECC 정정 메시지도 관측했다. 이를 전송 오류나 동일한 복원 형식으로 취급하지 않는다.
- 이후 Linux에서 읽은 앞32MiB와 뒤96MiB의 SHA도 대응 백업 구간과 일치했다. 조회한 불량 블록 수는0이었다. 실제 NAND 복원은 시행하지 않았다.

| 백업 | 바이트 | SHA256 |
|---|---:|---|
| ECC main | 134217728 | `06cbcf9d70d48744fb932e5cc031f3bac86ba2648d9d1ee8e5e9682a46ed883f` |
| raw+OOB | 138412032 | `c3641f0da22d56a28e2aea7805d887bfdd4ccbe6c9ac3199a8834c1765859ba1` |

순정 앞부분 UBI의 PEB131072 / VID offset2048 / data offset4096 / LEB126976 구조와 두 layout 사본의 CRC를 확인했다. 볼륨은 `kernel`(dynamic23LEB), `ubi_rootfs`(dynamic183LEB)다. 복원한 순정 FIT는 Linux3.14.77 gzip, load/entry `0x80208000`, 기본 configuration `config@ap.dk01.1-c2`였다.

## 6. 기존 OpenWrt 이미지가 바로 설치되지 않는 이유

기존 `openwrt-kt9200-standard.bin`(10,292,275바이트), high-power(10,302,515바이트)는 custom `giga_kt-9200` sysupgrade TAR다. 최초 initramfs·전체 NOR 이미지가 아니다. 이 파일을2MiB NOR에 쓰면 부트 체인이 손상될 수 있으나 ‘언제나 영구 복구 불능’이라고 단정하지 않는다.

| 제약 | 실제 확인과 대응 |
|---|---|
| 기존 FIT에 ramdisk 없음 | kernel+DTB만 포함. 원래 SquashFS root를 그대로 initramfs 인자로 사용할 수 없음. 별도 newc cpio를 구성 |
| FIT ramdisk `load` 필수 | 순정 U-Boot의 필수 속성 조회를 코드로 확인해 실행 전에 후보 수정. `initrd_high`만으로 대신할 수 없음 |
| LZMA 미지원 | 실기 `Unimplemented compression type 3`. 해시 검증 후 커널 실행 전에 U-Boot로 복귀 |
| gzip 출력8MiB 한도 | 코드에서 확인. 압축 해제 kernel12,124,224바이트가 초과하므로 gzip 후보는 전송·CRC만 확인하고 부팅하지 않음 |
| 순정 bootipq의 config 선택 | `config@5` / `config@ap.dk01.1-c2` 이름을 직접 검색. custom의 `config@1`만으로 영구 부팅을 보장할 수 없음 |
| NAND 전체128MiB 후보 | RAM에서 읽기 전용 attach 시 후반 PEB의 다른 image sequence로 실패. 앞32MiB와 뒤96MiB로 분리 |

해결된 RAM 후보는 **동일 kernel을 비압축 FIT로 포장**하고 명시적 ramdisk load와 검토한 메모리 범위를 사용했다. source/staging `0x84000000`은 순정 bootipq 코드에서도 확인한 주소다. 새 이미지의 크기·kernel 출력·initrd·FDT 범위 검토를 생략하는 공통 주소 예제는 아니다.

## 7. OpenWrt RAM 부팅에서 확인한 것

- 최소 UART 셸: 비압축 FIT 전체 CRC와 payload CRC32/SHA1 검사 후 Linux5.15.150, 4CPU, 256MiB, `/init` ash 응답 확인. 이 후보는 모든 플래시 노드를 비활성화했고 `/proc/mtd`에 장치가 없었다.
- 전체 사용자 환경: OpenWrt23.05.3/r23809, `rootfs_type=initramfs`, tmpfs 루트, 유선 ping과 HTTP200 응답 확인.
- 무선: ath10k 펌웨어 및 PHY2개 초기화,2.4/5GHz band 및 pre-cal-nvmem 경로 관측. 라디오는 disabled. 실제 송수신·출력·안정성·WAN 인터넷은 미검증.
- 연결한 실물 LAN1은 후보 DSA에서 `lan4`/PHY1로 표시됐다. 나머지 실물 포트 전체 매핑은 확인하지 않았으며 네 LAN을 bridge로 묶어 통신했다.
- 처음 전체128MiB를 읽기 전용 노출한 후보는 UBI attach에 실패했지만 RAM 시스템은 부팅됐다. 이를 설치 또는 데이터 손상 성공/실패와 혼동하지 않는다.
- 최초 기록에 사용한 설치용 RAM 환경은 NOR 전부 및 뒤96MiB를 읽기 전용, 앞32MiB만 `install-target`으로 쓰기 가능하게 노출했다. 이름·offset·크기·flags와 UBI 미attach를 실기로 확인한 후8절의 설치를 진행했다.

## 8. NAND 영구 설치와 첫 부팅 실패 수정

준비된 사설 포트 이미지는 아래와 같다. 원본 보정값이나 장비별 데이터가 포함될 수 있어 **바이너리·전체 로그·개별 환경 값은 공개하지 않는다**. 해시는 보관 파일의 식별값이며 배포 승인이나 설치 성공 인증이 아니다.

| 산출물 | 바이트 | SHA256 |
|---|---:|---|
| 최초 기록 kernel FIT — root mount 실패, 아래 수정 필요 | 12143256 | `1eb48d2b6bcf40fd12adb2162b87e87e073442ef607dede523405918ab19090d` |
| 최종 기록 kernel FIT — DTB root 인자 수정 | 12143380 | `005b1808fc0c365c3bf1a86cf4e4cacd667f01f9f38366cc426f0b6e188df277` |
| 준비된 root SquashFS | 7290880 | `1dac6d6d2b64d48a4b5d5e67fafee24959dbbe773ea3951f19247e1906f9d042` |
| 최초 기록 UBI — 수정 전 kernel 포함, 최종 이미지 아님 | 20447232 | `addf531e520fd97481ce4ded91ea1677ec2175bd0d65837d54072d96b931237b` |

후보는 kernel/rootfs/rootfs_data 볼륨, 순정 bootipq용 config 이름,32MiB 설치 경계, NOR 및 뒤96MiB 보호를 포함한다. 기본 LAN DHCP·WAN DHCP·방화벽/NAT를 정리하고 라디오는 껐다. 원래 base_mac의 unicast 유효성 검사가 통과하지 않아 원래 환경은 그대로 두고 Linux용 안정적 locally administered MAC을 구성했다. 이 맞춤 rootfs의 초기 root 암호는 비어 있으므로 실제 설치 후 로컬에서 설정해야 한다.

일반 sysupgrade는 원래 LZMA/config/파티션 문제를 다시 만들 수 있어 후보의 platform check가 이를 거절하도록 했다. 최신 공식 TI04 지원 펌웨어를 빌드한 결과가 아니다.

**NAND 설치 파일 전송 준비 명령이 자동 승인 검토에서 두 차례 `blocked by policy`로 거절됐다.** 구체 사유는 제공되지 않았다. 사용자의 수동 PowerShell 시도는 처음 변수 설정/호출 순서 오류(`BadExpression`)로 실패했고, 변수 없는 한 줄로 정정한 뒤 전송 서버의 LISTEN 상태를 확인했다.

### 실제 기록과 실패

- 설치 파일 RAM 다운로드와 SHA 확인 후, 앞32MiB만 `ubiformat`했다. kernel/rootfs readback SHA 일치, NOR8개 파티션 및 뒤96MiB SHA 불변을 확인했다.
- 첫 긴 UART 명령은 수신 누락/셸 continuation으로 실행 전 guard가 실패했다. 이어진 전송 방식은 `base64` applet 부재로 중단됐다. 두 번 모두 NAND 기록 전 중단이다. 짧은 리터럴 줄·16바이트 단위 송신 간격·전송한 guard 자체의 SHA 검사로 수정한 뒤 기록했다.
- **첫 NAND 부팅은 kernel 로딩·해시·config@5 선택까지 성공했지만 root mount에서 panic했다.** 순정 bootipq가 `ubi.mtd=rootfs root=mtd:ubi_rootfs rootfstype=squashfs`를 넣어, 처음 DTB의 파티션 이름 `ubi`와 현대 ubiblock 경로가 맞지 않았다. U-Boot 콘솔로 복귀했으며 이를 설치 완료로 표시하지 않았다.
- 수정 DTB는 앞32MiB 파티션 이름을 `rootfs`로 맞추고 `/chosen/bootargs-append`로 ` root=/dev/ubiblock0_1 rootfstype=squashfs console=ttyMSM0,115200 loglevel=6`을 붙였다. bootargs 기본값만 바꾸는 것으로는 bootipq 덮어쓰기를 해결하지 못한다. OpenWrt 해당 커널의 append 처리를 확인했고, 동일한 순정 root 인자를 주입한 RAM kernel에서 NAND root/overlay 부팅을 먼저 검증했다.
- 수정 FIT를 RAM으로 다시 전송하고 크기/SHA 확인 후 **UBI kernel 볼륨만** 갱신했다. 최종 kernel readback은 `005b1808…df277`, rootfs는 위 `1dac6d6d…9d042`와 일치했다. rootfs/overlay를 재포맷하거나 NOR를 추가 수정하지 않았다.

### 최종 실기 판정

| 검증 | 실제 결과 |
|---|---|
| 순정 bootipq 자동 부팅 | kernel 볼륨을 NAND에서 읽고 `config@5`, CRC32/SHA1 통과 후 부팅2회. 각 재부팅에서 자동 ESC 송신0, TFTP 없음 |
| root/overlay | UBI가 앞32MiB에 attach, `/dev/root /rom squashfs ro`와 `/dev/ubi0_2 /overlay ubifs rw`, overlayfs 루트 확인 |
| 저장 유지 | overlay의 확인용 파일이 두 차례 소프트웨어 재부팅 후 같은 내용으로 유지 |
| 보존 범위 | NAND 뒤96MiB 및 NOR8개 파티션 모두 설치 전 SHA와 일치 |
| 유선 관리 | LAN bridge up, PC ping 응답, LuCI 로그인 HTML 확인. 로그인 페이지의 HTTP403 + `x-luci-login-required: yes`는 로그인 요구 응답 |
| DHCP/무선 | DHCP 활성·dnsmasq 실행 확인. 클라이언트 임대는 미시험. 두 라디오는 disabled 유지 |
| 남은 시험 | 물리 전원 차단/재인가, WAN 인터넷, RF 송수신·출력, 나머지 포트 매핑, 장기 안정성 |

이 결과는 해당 한 대의 OpenWrt23.05.3 맞춤 포트 설치 검증이다. 일반 sysupgrade나 모든 TI04 리비전 지원을 뜻하지 않는다. **현재 MTD 번호를 다른 부팅 환경에 그대로 복사해 쓰면 안 된다.** 최초 UBI에는 수정 전 kernel이 들어 있으므로, 그 파일 하나를 다시 기록하면 root mount 실패가 재현될 수 있다.

## 근거와 공개 범위

직접 근거는 보존된 NOR/NAND 읽기, 기록 결과 JSON, 선택한 환경 조회, UART RX/TX 감사 기록, FIT/DTB/cpio/UBI 파싱 결과다. 공개 저장소에는 비식별 요약과 식별 해시만 추가했다. 장비별 비밀 값·원본 덤프·세션·사설 이미지·스크린샷의 사용자 경로는 추가하지 않았다.

일반 구조 참고: [U-Boot v2012.07 main.c](https://github.com/u-boot/u-boot/blob/v2012.07/common/main.c), [Linux UBI media header](https://github.com/torvalds/linux/blob/v5.15/drivers/mtd/ubi/ubi-media.h), [OpenWrt v23.05.3 ipq40xx 이미지 정의](https://github.com/openwrt/openwrt/blob/v23.05.3/target/linux/ipq40xx/image/generic.mk). 제조사 바이너리와 실제 실기 결과가 일반 소스보다 구체적인 범위에서는 해당 장비의 증거를 우선했다.
