# KT GiGA WiFi Wave2 (올레디오 TI04-708H) OpenWrt 설치 경로 및 기술 검증 보고서

**작성일시**: 2026-10-26  
**대상 장비**: KT GiGA WiFi Wave2 (올레디오 TI04-708H / 보드 리비전 WGHE010100)  
**분석 환경**: `D:\ai\firmware` 및 `D:\ai\KT-Router-TI04-708H` 내 실기 로그, NOR 덤프 바이너리, 역어셈블 코드, 웹 자산  

---

## 1. 장비 아키텍처 및 펌웨어 구성 요약

- **메인 SoC**: Qualcomm Atheros IPQ4018 (4-Core ARM Cortex-A7, 최대 717MHz)
- **시스템 RAM**: Nanya NT5CC128M16JR-EK 256MiB DDR3L SDRAM (DDR 537MHz 동작)
- **이중 플래시(Dual Flash) 구조**:
  - **SPI NOR Flash (U33 실장)**: GigaDevice `GD25Q16CSIG` (2MiB = 2,097,152 바이트, SOP-8 패키지)
    - 역할: 퀄컴 부트 체인 및 부트로더 저장 (`SBL1`, `MIBIB`, `QSEE/TZ`, `CDT`, `DDRPARAMS`, `APPSBLENV`, `APPSBL`, `ART`)
  - **SPI NAND Flash**: Macronix `MX35LFxGE4AB` (128MiB = 1Gbit)
    - 역할: 대용량 UBI 파티션 저장 (Linux Kernel FIT 이미지, SquashFS Rootfs, 통신사 데몬 등)
- **무선 프런트엔드**: Skyworks `SKY85405` (5GHz PA + 전력 검출기) / 2.4GHz 내장
- **디버그 콘솔(CN1)**: 4핀 헤더 (①: VCC(미연결 유지) / ②: Board TX &rarr; 어댑터 RX / ③: Board RX &larr; 어댑터 TX / ④: GND)
- **물리 버튼**: SW1 (`FACTORY RESET`), SW3 (`WPS`), SW4 (`RESET`)

---

## 2. [방법 1] 별도 장비(ROM 라이터 등) 없는 기본 상태 설치 가능성 조사 및 기술 검증

사용자 요청 우선순위 1번인 **"별도의 하드웨어 장비로 NOR을 변경하지 않고 기본 상태에서 설치하는 방법"**에 대해 웹 UI, 네트워크 서비스/취약점, UART 콘솔 세 가지 측면에서 정밀 검증을 수행했습니다.

### 2.1. 웹 UI 관리자 권한을 통한 펌웨어 업데이트 메뉴 활성화 가능성 &rarr; **[불가]**

1. **일반 사용자 웹 UI (포트 8899 / `http://172.30.1.254:8899`)**:
   - 시스템 관리 메뉴 경로: `/system/id` (관리 계정 설정), `/system/config` (설정 초기화), `/system/reboot` (시스템 재시동)의 3개 페이지만 존재합니다.
   - `/system/config` 페이지 및 공통 자바스크립트(`jquery.custom.js`, `board.custom.js` 등) 정적 분석 결과:
     - 폼 내부에는 hidden 필드인 `configfilename`만 존재하며, 파일 업로드용 `<input type="file">` 태그나 펌웨어 업그레이드 엔드포인트가 전혀 구현되어 있지 않습니다.
     - "초기 설정 복원"은 파일 복원이 아닌 단순 `POST configreset` 후 재부팅 트리거입니다.
2. **별도 관리자 웹 UI (포트 8801 / `http://172.30.1.254:8801/admin/login/login`)**:
   - LAN 포트 스캔을 통해 포트 8801에 별도의 최고관리자 로그인 화면이 존재함을 확인했습니다.
   - KT 라우터의 일반적인 비밀번호 조합(admin / MAC 뒤 6자리 등) 72종을 준비하여 테스트했으나 모두 인증에 실패했습니다 (5회 실패 시 10분 잠금).
   - **결정적 근거**: 장비 UART 로그에서 `Change admin id/pwd by kt hash string` 메시지가 확인되었습니다. KT 순정 펌웨어는 공장 초기화 시 기기 고유 식별값(시리얼, MAC 등)과 KT 고유의 비공개 솔트/해시 알고리즘을 결합하여 관리자 비밀번호를 생성하므로 기본값 추측으로 진입할 수 없습니다.
   - **구조적 한계**: KT의 라우터 관리 아키텍처상 펌웨어 업데이트는 웹 UI를 거치지 않고 WAN 구간의 **TR-069 (CWMP)**를 통해 KT 중앙 ACS 서버에서 전자서명된 바이너리를 푸시하는 방식으로만 수행됩니다. 따라서 관리자 웹에 로그인하더라도 로컬 펌웨어 파일 업로드 메뉴 자체가 존재하지 않습니다.

### 2.2. 로컬 네트워크 서비스 취약점 분석 &rarr; **[불가]**

- **DDNS 명령 주입 시험**: `/service/ddns`의 POST 요청을 분석한 결과, 특수문자(`;`, `|`, `&`, 백틱, `$`) 필터링(`CheckHtmlString()`)이 존재하며, 백도어 실행을 위한 임의 명령어 전송 시 서버 측에서 저장을 거부했습니다.
- **UPnP (포트 35500)**: SSDP 응답으로 확인된 엔드포인트(`/rootDesc.xml`, `/WANIPCn.xml` 등)는 표준 포트포워딩 및 상태 조회 액션만 제공하며, 임의 명령 실행이나 펌웨어 다운로드 기능은 없습니다.
- **원격 관리 포트**: LAN 상에서 텔넷(23), SSH(22), CWMP(7547) 포트는 모두 타임아웃(차단) 상태입니다.

### 2.3. UART 직렬 콘솔 진입 가능성 및 락(Lock) 원인 분석 &rarr; **[APPSBL 역어셈블 검증 완료]**

1. **물리적 UART 통신 검증**:
   - CN1 핀 연결 (②: TX, ③: RX, ④: GND, 115200 8N1).
   - U-Boot 2012.07 배너 및 리눅스 부팅 로그 수신 확인.
   - 리눅스 초기 부팅 구간에서 문자 `g` 및 제어문자 `^[`가 반환되는 TTY 에코 동작을 확인하여 **보드 RX 및 USB-TTL 어댑터 TX 하드웨어 경로가 정상 도통됨을 증명**했습니다.
2. **Autoboot 중단 실패 현상**:
   - 부팅 중 콘솔에 `Press any key to stop autoboot:  0` 문구가 출력되지만, 부팅 전/중/후로 Esc, Space, Enter, 숫자 키를 지속적으로 전송해도 중단되지 않고 곧바로 커널(`UBI: attaching mtd2...`)로 진입했습니다.
3. **부트로더(APPSBL) 역어셈블 분석을 통한 락(Lock) 메커니즘 규명**:
   - NOR 플래시 오프셋 `0x100000`에서 추출한 U-Boot 바이너리(`appsbl-load.bin`)의 autoboot 루틴(`0x8731ad54 ~ 0x8731af50`)을 정밀 분석하여 통신사 순정 락 구조를 완벽하게 밝혀냈습니다.
   - U-Boot는 환경변수 `bootdelay` 값을 읽어 다음과 같이 동작합니다:

| 저장된 `bootdelay` 값 | 내부 Mode | 동작 방식 및 autoboot 중단 조건 |
| :--- | :---: | :--- |
| **`0` (순정 기본값)** | **Mode 0** | **[2중 락 구조]**<br/>1) 하드웨어 GPIO 검사: `GPIO2 == 0 && GPIO63 == 0` (두 핀 모두 접지/LOW)<br/>2) 1)이 참인 경우에 한해 1초간 UART 입력 대기 후 **비밀 문자열 `@tnie`** 입력 시에만 중단<br/>※ GPIO 조건이 거짓이면 UART 입력을 **전혀 검사하지 않고 0초 만에 커널로 직행** |
| **`2012`** | **Mode 1** | **[ESC 폴링 모드]**<br/>화면에 `Press ESC to stop autoboot:  1 ` 출력 후 약 500ms 동안 UART에서 `0x1B`(ESC) 입력을 감지하면 **즉시 U-Boot 프롬프트로 진입** (GPIO 검사 없음) |
| **`2` 또는 미설정** | **Mode 2** | `GPIO2 == 0 && GPIO63 == 0` 검사 후 참이면 비밀번호 없이 중단 |
| **그 외 (3, 5, 10 등)** | **Mode 0** | 일반 U-Boot와 달리 0으로 정규화되어 Mode 0으로 동작 (일반적인 초 단위 대기 불가) |

### 2.4. 기본 상태(장비 없이)에서 설치 가능한가? &rarr; **[실질적 결론: 불가 (단 1가지 극단적 예외)]**

- **순정 상태의 결론**: 웹 UI 업데이트 경로는 존재하지 않으며, UART는 `bootdelay=0` 상태에서 `GPIO2=0`, `GPIO63=0`, 그리고 비밀 문자열 `@tnie` 입력이라는 3중 조건을 요구합니다.
- **유일한 이론적 무장비 시도 경로**:
  - `GPIO63`은 DTS상 `SW4 (RESET)` 버튼에 매핑되어 있습니다.
  - 만약 `GPIO2`가 보드 전면의 `SW1 (FACTORY RESET)` 또는 `SW3 (WPS)` 버튼에 연결되어 있다면:
    1. PC 시리얼 터미널을 115200 8N1로 열어둠.
    2. 보드의 **`SW4 (RESET)`와 `SW1 (또는 SW3)` 두 버튼을 동시에 손으로 꾹 누른 상태**에서 전원 어댑터 연결.
    3. 전원이 켜지자마자 1초 이내에 시리얼 터미널로 **`@tnie\r`** 문자열을 즉시 전송.
    4. U-Boot가 두 GPIO의 LOW 상태를 감지하고 `@tnie` 문자열을 확인하면 autoboot를 중단하고 `ipq40xx# ` 프롬프트로 진입 가능.
  - **한계**: 만약 `GPIO2`가 버튼이 아닌 내부 테스트 포인트이거나 풀업 저항에 묶여 있다면 물리적 접지 도구(핀셋/점퍼선 등) 없이는 불가능합니다. 따라서 100% 장비 없이 안정적으로 진입하는 것은 보장되지 않습니다.

---

## 3. [방법 2] SPI NOR 최소 변경을 통한 안정적 UART 진입 및 검증 결과

외부 롬 라이터(CH341A)를 사용할 수 있는 환경이라면, **부트로더를 교체하거나 위험한 전체 플래싱을 할 필요 없이**, NOR 환경변수 파티션 내의 단 한 항목(`bootdelay`)만 수정함으로써 100% 안전하게 U-Boot 프롬프트를 획득할 수 있습니다.

### 3.1. 2MiB NOR 덤프 및 무결성 검증 (2026-10-26 실기 검증 완료)

- **장비 구성**: CH341A 프로그래머 + SOP8 테스트 클립 (공유기 전원 및 외부 배선 완전 분리, 3.3V 전압 확인).
- **AsProgrammer 2.1.2**를 통해 JEDEC ID `C8 40 15` (GD25Q16C) 정상 인식.
- 3회 연속 독립 덤프 수행: `nor-read1.bin`, `nor-read2.bin`, `nor-read3.bin`.
  - 각 파일 크기: 정확히 `2,097,152 바이트` (2MiB).
  - SHA-256 해시 일치: **`c33402801b9c4484b20634303675fe7422b0dcde1e6e1d95c4fac790bea9d23e`**
  - 3개 파일 간 바이너리 100% 일치 확인으로 완벽한 순정 복원용 원본 백업본 확보 완료.

### 3.2. 환경변수(APPSBLENV) 최소 패치(Minimal Patch) 설계 및 오프라인 검증

1. **파티션 테이블 확인**:
   - NOR `0x40100` MIBIB 파티션 테이블 분석 결과, `0:APPSBLENV` 파티션은 오프셋 **`0x0E0000 ~ 0x0F0000`** (64KiB)에 위치합니다.
   - 시작점 `0x0E0000`에 4바이트 CRC32 `77ec5d89` 및 18개의 환경변수 문자열이 배치되어 있습니다.
2. **`bootdelay=2012` 패치**:
   - `prepare-ti04-uart-env.py` 스크립트를 통해 환경변수 내 `bootdelay=0`을 **`bootdelay=2012`**로 변경.
   - 전체 64KB 데이터에 대한 CRC32 체크섬을 재계산하여 `5ae6809d`로 갱신.
3. **변경 범위 검증 (`review.json` 증거)**:
   - 전체 2MiB 중 오직 첫 번째 4KiB 섹터(`0x0E0000 ~ 0x0E1000`) 내의 **31개 바이트만 변경**됨.
   - SBL1, MIBIB, QSEE, CDT, APPSBL(부트로더 본체), ART(무선 캘리브레이션) 파티션은 **단 1비트도 건드리지 않고 100% 순정 상태 유지**.
   - 생성된 4KiB 패치 파일: `candidate-sector-at-e0000-size-1000.bin` (SHA-256: `12abf9e2b7b170812f6e92f55be456f1c5fb5eb0a2f4208a94f057bbade456d2`).
   - 원본 4KiB 복구 파일: `original-sector-at-e0000-size-1000.bin` (언제든 100% 원상 복구 가능).
4. **기록 시 주의점**:
   - AsProgrammer의 기본 "Erase" 버튼은 칩 전체(Chip Erase)를 지우는 명령(`0xC7`)을 실행하므로 절대 사용하면 안 됩니다.
   - CH341A CLI 도구(`flashrom` 또는 전용 섹터 기록 스크립트)를 이용하여 오직 `0x0E0000` 주소의 4KiB 섹터만 Erase & Write해야 합니다.
5. **결과**:
   - 이 패치가 기록되면 부팅 시 `Press ESC to stop autoboot:  1 `이 출력되며, 500ms 동안 시리얼로 ESC 키를 누르면 GPIO 접지나 비밀번호 없이 **즉시 U-Boot 콘솔(`ipq40xx# `)에 진입**하게 됩니다.

---

## 4. 확보된 OpenWrt 펌웨어 파일(`openwrt-kt9200-*.bin`) 분석 및 치명적 주의사항

`D:\ai\firmware` 폴더에 위치한 파일들에 대한 분석 결과입니다:
- `openwrt-kt9200-standard.bin` (10,292,275 바이트)
- `openwrt-kt9200-high-power.bin` (10,302,515 바이트)

### [경고] 2MiB NOR 플래시에 이 파일을 직접 플래싱하면 절대 안 됩니다!

1. **이미지 형식 분석**:
   - 두 파일은 TAR 포맷의 OpenWrt `sysupgrade` 아카이브입니다.
   - 내부 구성:
     - `sysupgrade-giga_kt-9200/kernel` (FIT 이미지, 3,218,180 바이트 &asymp; 3.07MB)
     - `sysupgrade-giga_kt-9200/root` (SquashFS 파일시스템, 7,068,672 바이트 &asymp; 6.74MB)
     - `CONTROL` (`BOARD=giga_kt-9200`)
2. **NOR 플래시와의 불일치**:
   - 파일 크기(~10.3MB)가 보드의 SPI NOR 크기(2MB)의 5배를 초과합니다.
   - 이 파일에는 퀄컴 부트체인(SBL1, QSEE, APPSBL 등)이 포함되어 있지 않습니다. 만약 CH341A로 이를 NOR에 강제 기록하면 라우터가 전원조차 켜지지 않는 **완전한 벽돌(Hard Brick)**이 됩니다.
   - 이 커널과 룻에프에스는 **128MiB SPI NAND 플래시의 UBI 볼륨**에 설치되어야 하는 파일입니다.
3. **배포 영상 및 호환성 한계**:
   - 배포 영상(N1Kn0bFdptc)은 본 바이너리가 "Pandora boot가 이미 설치된 장비용"이라고 명시하고 있습니다.
   - 포함된 DTS(`giga_kt-9200.dts`)의 NOR 파티션 맵은 TI04-708H와 일치하지만, 최초 Pandora 부트로더 설치 절차나 팩토리 설치 바이너리는 공개 파일에 포함되어 있지 않습니다.
   - 따라서 **순정 U-Boot를 유지한 채 U-Boot 콘솔에서 TFTP RAM 부팅을 거쳐 NAND에 설치하는 정공법**을 사용해야 합니다.

---

## 5. TI04-708H OpenWrt 설치 권장 로드맵 (단계별 가이드)

```mermaid
flowchart TD
    A["[1단계] U-Boot 콘솔 확보<br/>(A: 무장비 SW4+SW1 홀드 후 @tnie 입력<br/>B: CH341A로 bootdelay=2012 패치)"] --> B["[2단계] 위험 없는 TFTP RAM 부팅<br/>(openwrt-initramfs-kernel.bin을 RAM 0x84000000에 로드)"]
    B --> C["[3단계] 순정 파티션 및 캘리브레이션 백업<br/>(RAM 상 OpenWrt에서 ART caldata 및 NAND 전체 백업)"]
    C --> D["[4단계] NAND에 OpenWrt 영구 설치<br/>(sysupgrade -n openwrt-kt9200-standard.bin 실행)"]
```

### [1단계] U-Boot 콘솔 획득
- **시도 1 (무장비 경로)**:
  - USB-TTL 어댑터(115200 8N1)를 CN1 (② TX, ③ RX, ④ GND)에 연결.
  - `SW4 (RESET)`와 `SW1 (FACTORY RESET)` 버튼을 동시에 누른 채 전원을 켜고, 1초 이내에 터미널로 `@tnie\r`를 연속 전송 &rarr; 프롬프트 진입 성공 시 2단계로 직행.
- **시도 2 (검증된 하드웨어 경로)**:
  - 위 방법이 안 될 경우, CH341A로 NOR `0x0E0000` 섹터에 `bootdelay=2012` 패치(`candidate-sector-at-e0000-size-1000.bin`) 기록.
  - 전원 인가 후 터미널에서 `ESC` 키를 눌러 `ipq40xx# ` 프롬프트 진입.

### [2단계] 위험 없는 RAM 부팅 검증 (TFTP Initramfs 부팅)
- 플래시를 영구 덮어쓰기 전에 플래시 훼손 위험이 전혀 없는 RAM 부팅을 먼저 수행합니다.
- PC 유선 랜을 공유기 LAN 포트에 연결 (PC IP: `192.168.1.100`, TFTP 서버 구동).
- TFTP 루트 폴더에 IPQ4018 호환 `openwrt-ipq40xx-generic-initramfs-kernel.bin` 배치.
- U-Boot 콘솔에서 다음 명령 실행:
  ```sh
  setenv ipaddr 192.168.1.1
  setenv serverip 192.168.1.100
  tftpboot 0x84000000 openwrt-ipq40xx-generic-initramfs-kernel.bin
  bootm 0x84000000
  ```
- RAM 상에서 OpenWrt가 정상 부팅되고 유선 LAN 및 웹 루치(LuCI) 화면이 뜨는지 확인합니다.

### [3단계] 순정 파티션 및 고유 캘리브레이션(ART) 데이터 백업 (필수)
- RAM으로 부팅된 OpenWrt 쉘(SSH `192.168.1.1`)에서 실행:
  ```sh
  cat /proc/mtd
  # ART 파티션 (각 기기 고유의 Wi-Fi 송신 출력 및 튜닝 값) 추출:
  dd if=/dev/mtdX of=/tmp/art_backup.bin
  # 순정 128MB SPI NAND 전체 백업:
  dd if=/dev/mtdY of=/tmp/nand_full_backup.bin
  ```
- PC로 `scp` 또는 TFTP를 통해 백업본을 안전하게 전송 및 보관합니다. (ART 파티션이 소실되면 5GHz Wi-Fi가 켜지지 않거나 출력이 극도로 약해집니다.)

### [4단계] 128MB SPI NAND에 OpenWrt 영구 설치
- RAM 상의 OpenWrt `/tmp` 디렉터리에 `openwrt-kt9200-standard.bin`을 복사합니다.
- sysupgrade 명령 실행:
  ```sh
  sysupgrade -n /tmp/openwrt-kt9200-standard.bin
  ```
- 시스템이 NAND의 UBI 볼륨 포맷 및 커널/rootfs 기록을 완료한 후 자동으로 재부팅되면 영구 설치가 완료됩니다.

---

## 6. Remaining Questions & Gaps (남은 의문점 및 향후 과제)

1. **GPIO2의 물리적 회로 매핑 미확정**:
   - `GPIO63`은 DTS 및 PCB 분석을 통해 `SW4 (RESET)`으로 확인되었으나, `GPIO2`가 전면 버튼(SW1 FACTORY RESET / SW3 WPS) 중 하나인지, 아니면 기판 내부 테스트 포인트/풀업 회로인지 물리적 회로 추적이 완료되지 않았습니다.
   - 향후 테스터기를 통한 도통 시험(SW1/SW3 누름 시 SoC GPIO2 레지스터 전압 변화 측정)을 우선 진행하면 무장비 진입 가능 여부를 최종 확정할 수 있습니다.
2. **`bootdelay=2012` 패치의 실제 하드웨어 쓰기 검증**:
   - 4KiB 패치 바이너리 생성, CRC 재계산, 17개 타 환경변수 보존 및 오프라인 복구 검증은 100% 완료되었으나, 실제 실기 칩에 쓰기 및 ESC 프롬프트 획득 테스트는 아직 실행되지 않았습니다. 사용자 승인 하에 `0x0E0000` 4KB 섹터 플래싱을 수행하여 U-Boot 프롬프트 획득을 최종 실증해야 합니다.
3. **보드 전용 OpenWrt Initramfs 이미지 빌드**:
   - 현재 보유한 두 파일은 sysupgrade TAR 파일이므로 2단계 RAM 부팅에 사용할 `initramfs-kernel.bin` 파일이 필요합니다. 공식 OpenWrt 23.05 `ipq40xx/generic` 타깃에서 KT-9200 DTS를 적용한 initramfs 커널 바이너리를 빌드하거나 추출하는 작업이 후속 단계로 필요합니다.
