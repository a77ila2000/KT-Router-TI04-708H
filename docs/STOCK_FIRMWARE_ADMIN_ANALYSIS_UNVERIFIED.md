# TI04-708H 순정 펌웨어 관리자 분석 — 정적 검증 결과와 미검증 과제

> [!NOTE]
> **2026-10-30 정적 검증 반영 / 순정 실기 로그인·메뉴 동작은 미검증**
>
> v1.4.0 rootfs의 PHP 소스와 ARM 바이너리를 대조해 기존 초안의 오류를 수정했습니다. 파일 경로는 기존 링크 유지를 위해 그대로 두었습니다. 아래의 ‘확인’은 해당 파일에서 코드 경로를 확인했다는 뜻이며, 실제 로그인·설정 적용·순정 웹을 통한 OpenWrt 설치 성공을 뜻하지 않습니다.
>
> [순정 분석 파일](../dumps/README.md) · [OpenWrt 설치 안내](../INSTALLATION.md)

## 1. 분석 대상과 판정 범위

- 대상: allRadio TI04-708H / WGHE010100.
- 실물 SoC: 저장소의 U16 사진·마킹 기록은 **IPQ4018**입니다. IPQ4019 공통 플랫폼/드라이버 문자열과 실물 칩 식별을 구분합니다. [하드웨어 근거](../RESEARCH_NOTES.md#사양-근거와-판정-범위).
- rootfs: `/etc/version`의 **v1.4.0, build 2024/04/19 11:00**, `/etc/model`의 `TI04-708H`를 확인했습니다. 이번 검증에서 커널 버전을 별도로 재분석하지는 않았습니다.
- rootfs payload SHA256: `78f28453ac89e1a1972107295d809be817c9e3e64ebf4967c81ff7f1e9827f28`.
- 아래 바이너리 4개와 관련 소스 16개를 선택한 UBI payload의 `unsquashfs -cat` 출력과 직접 비교했습니다. 모두 일치했습니다. 다른 2022년 rootfs의 결과와 섞지 않았습니다.

분석은 파일 읽기와 정적 역공학으로 진행했습니다. 실제 장치의 MAC·암호를 계산하거나 저장 자격증명을 복호화하지 않았고, 로그인·펌웨어 업로드·기록 시험도 하지 않았습니다.

### 기존 초안에서 달라진 핵심

| 항목 | 검증 결과 |
|---|---|
| 웹 프레임워크 | Zend Framework가 아니라 **Yaf** |
| 기본 관리자 생성 | 매부팅 무조건 재생성이 아니라 **빈 값/초기 상태에서 조건부 생성** |
| 해시 입력 모델명 | `TI04-708H` 그대로가 아니라 **`TI04708H`로 정규화** |
| 저장 암호화 | 직접 16바이트 키의 AES-128이 아니라 **SHA256 파생 키를 사용하는 AES-256-CBC** |
| 실패 기록 | 5회째 파일 생성이 아니라 **첫 실패부터 파일 기록**, 5회/600초 조건 적용 |
| 웹 업그레이드 | 처리 코드는 존재하지만 **제조사 암호화 tar 패키지 경로**이며 일반 OpenWrt 파일 수용은 미입증 |
| 브릿지·TR069 | 추가 접근 조건이 있으며 **브릿지 무조건 허용·FOTA 완전 차단으로 단정 불가** |

## 2. 웹 서버와 포트 분리

- 서버: **lighttpd + PHP FastCGI** (`/usr/bin/php-cgi`).
- PHP 애플리케이션: **Yaf 기반 MVC**. `/www/public/index.php:7`의 `new Yaf_Application(...)` 및 `Bootstrap.php`의 Yaf 클래스가 근거입니다. PHP의 Zend 엔진 설정은 Zend Framework 사용 증거가 아닙니다.
- `/bin/rc`는 `/var/etc/lighttpd.conf`를 동적으로 만듭니다.

| 용도 | NVRAM 값 | 코드상 fallback | 확인된 처리 |
|---|---|---:|---|
| 일반 사용자 | `http/uport` | 8899 | `server.port`에 사용, 해당 socket에서 `/admin` URL 정규식 deny |
| 관리자 | `http/port` | 8801 | 별도 socket/rewrite, 기본 경로를 `/index.php/admin`으로 연결 |

**기존 `server.port = 8801` 예시는 잘못됐습니다.** 여기에는 사용자 포트를 넣으며 관리자 포트는 별도 socket으로 구성합니다. 80번에는 VOC/redirect 등 조건 분기가 있어 사용자 포트와 항상 같은 동작이라고 설명할 수 없습니다.

관리자 PHP 세션은 `ASESSION`, authtype, 접속 IP, timeout과 함께 `SERVER_PORT == nvram_get("http/port")`를 검사합니다. 따라서 `http://<장비의 관리 IP>:<설정된 관리자 포트>/admin/login/login`이 설정에 따른 접근 형태입니다. 예전 장비의 `172.30.1.254:8801`을 모든 장비에 고정된 필수 주소로 취급하지 않습니다. 이 코드만으로 방화벽·ACL 통과까지 보장하지도 않습니다.

근거: rc `0x12ce8`; `auth.class.php:140–184`.

## 3. 관리자 인증과 초기 암호 생성

### 초기화 조건과 ID

`auth.class.php:122–129`는 `system/adminname` 및 `system/adminpass`를 읽습니다. board의 초기 생성 경로는 다음 중 하나일 때 진입합니다.

- 저장 ID가 비어 있음.
- 저장 PW가 비어 있음.
- 저장 ID가 `ktadmin`이고 저장 PW가 `default`임.

이 경로는 기본 ID를 `ktadmin`으로 설정합니다. **매부팅 항상 계정을 덮어쓴다는 뜻이 아닙니다.** 기존 계정이 바뀌었다면 초기 생성 규칙을 알아도 현재 로그인 성공을 보장하지 않습니다.

근거: board `0x1343c`, `0x135dc`.

### 해시 입력의 정규화

1. MAC은 `/var/etc/board_mac`에서 읽어 6바이트로 파싱합니다. board 초기 경로에는 bootenv `base_mac`을 이 파일에 기록하는 코드가 있습니다. 화면의 현재 WAN MAC을 확인 없이 대신 넣지 않습니다.
2. MAC을 `%02X` 6개로 다시 포맷합니다. 결과는 콜론 없는 대문자 12자리입니다.
3. NVRAM `!sys/model`은 **ASCII 영문·숫자만 남기고 소문자를 대문자로 변환**합니다. 따라서 `TI04-708H`는 **`TI04708H`**가 됩니다.
4. 정규화 MAC + 정규화 모델명 + 프로그램 상수 `GIGALAND1409`를 이어 MD5를 계산하고, 소문자 hex의 앞 10자를 초기 암호로 사용합니다.

기존 초안의 하이픈 포함 모델명 식은 이 바이너리와 다릅니다. 초안에 있던 특정 MAC 예시와 암호 후보는 검증된 자격증명이 아니므로 제거했습니다. 실제 장치의 입력값·현재 계정·로그인 성공은 미확인입니다.

근거: board `0x135dc`; 모델 필터 `0x137ec–0x138a0`; MD5 helper `0x12f90`; 앞 10자 복사 `0x138f0–0x1391c`.

### 저장 형식은 AES-256-CBC

상수 문자열 `abcdel67890inter`는 16바이트이지만 **그대로 AES-128 키로 사용하는 것이 아닙니다.**

```text
key = SHA256(상수 문자열의 바이트).digest()  # raw 32바이트
IV  = key의 처음 16바이트
PKCS#7 방식 패딩 → AES-256-CBC → Base64 저장 문자열
```

board는 `AES_set_encrypt_key(..., 256, ...)`를 호출합니다. PHP native의 `aes_make_key` → `sha256_hex`도 raw SHA256 32바이트를 사용합니다. 함수 이름과 달리 64바이트 hexdigest가 아닙니다. 이 경로의 IV는 파생 키 앞 16바이트이며 랜덤 IV가 아닙니다.

웹 인증은 `apmib_aes_cbc_decrypt(nvram_get("system/adminpass"))` 결과와 입력 암호를 비교합니다. 이번 검증에서 실제 저장 암호를 읽거나 복호화하지 않았습니다.

근거: board `0x12788`, `0x12864`; php-cgi `0x402894`, `0x4028f4`, `0x402998`, `0x402cf0`; `auth.class.php:122–129,239–294`.

### 로그인 실패 처리

- 상수는 `LOGINFAILCNT = 5`, `LOGINFAILTIME = 600`입니다.
- `/tmp/admin_loginfail`은 **첫 실패부터** 생성하며 실패 횟수와 마지막 실패 시각을 저장합니다. 5회째 처음 생성되는 것이 아닙니다.
- 실패 횟수가 5 이상이면 차단값을 반환합니다. 이 코드의 카운터 파일은 IP별로 분리돼 있지 않습니다.
- `저장 시각 + 600 < 현재 시각`이면 파일을 지우지만, 같은 함수는 이미 읽은 지역변수 count를 계속 검사합니다. 따라서 만료 후 첫 함수 검사에도 차단값이 반환될 수 있어 ‘정확히 10분 뒤 첫 요청부터 허용’이라고 단정할 수 없습니다.
- 성공 시 실패 파일을 삭제합니다.

근거: `auth.class.php:13–15,187–237,257–259`. 경계 조건은 가상 값으로 대조했으며 실기 반복 로그인이나 잠금 시간 변경은 하지 않았습니다.

## 4. 관리자 UI에 존재하는 기능과 한계

표의 뷰 파일은 모두 존재하며 전체 Admin `.phtml` 파일은 60개입니다. 여기에는 레이아웃·오류·진행 화면도 포함되므로 60개 독립 기능을 뜻하지 않습니다. **화면 존재와 실제 작동·권한 허용·하드웨어 가속은 별도입니다.**

경로 기준: `/www/application/modules/Admin/views/`.

| 분류 | 뷰 파일 | 정적으로 확인한 내용 / 남은 확인 |
|---|---|---|
| 시스템 | `system/upgrade.phtml` | PC 파일 업로드 및 TFTP/FTP/USB 경로. controller와 native 호출도 존재. 파일 형식은 아래 5절 참조 |
| | `system/tr069.phtml` | TR069 활성 여부, ACS URL·주기 설정. FOTA 완전 차단은 미입증 |
| | `system/iperf.phtml` | iperf 설정 화면. 성능 측정 실행은 미시험 |
| | `system/webserver.phtml` | 사용자/관리자 웹 포트 설정 화면 |
| | `system/httpacl.phtml` | 관리자 웹 ACL 설정 화면 |
| 네트워크 | `network/sysmode.phtml` | routed/bridged/kt 선택·저장 코드. `http/lanlimituser` 제한 적용 |
| | `network/wan.phtml`, `network/wan2.phtml` | WAN 설정 화면. 각 연결 방식의 실제 동작은 미시험 |
| | `network/lan.phtml` | LAN/DHCP 설정 화면 |
| 스위치 | `switch/portmirror.phtml` | 포트 미러링 화면·controller action. 패킷 복제는 미시험 |
| | `switch/igmp.phtml` | IGMP 설정 화면. IPTV 동작은 미시험 |
| | `switch/ratectl.phtml`, `switch/qos.phtml` | 속도 제한·QoS 화면/action. 하드웨어 가속을 입증하지 않음 |
| 무선 | `wlan/radio.phtml` | 송신 출력·채널 폭 입력 UI. 실제 RF 출력은 미측정 |
| | `wlan/mesh.phtml` | Mesh 설정 화면. EasyMesh 표준 준수·인증은 미확인 |
| | `wlan/airtime.phtml` | Airtime 설정 화면 |
| | `wlan/speedlimit.phtml` | 무선 속도 제한 화면 |
| NAT/보안 | `nat/portfwd.phtml` | 포트 포워딩 화면 |
| | `nat/dmz.phtml` | DMZ/**SuperDMZ** 화면. Twin IP와의 동일성은 미확인 |
| | `nat/firewall.phtml`, `nat/filter.phtml` | 방화벽·필터 설정 화면 |

### 브릿지 접근 조건

`network/sysmode.phtml:971–973`은 `lanlimit_user=0`일 때 bridged 선택을 막습니다. Admin `Network.php:294–301`의 `get_lanlimit_user()!=1 && bridged` 검사에도 관리자 예외가 없습니다. `network.class.php:213–220`에서 `http/lanlimituser` 문자열 값이 `0`이면 제한합니다.

따라서 관리자 로그인만으로 브릿지가 무조건 허용된다는 추론은 틀립니다. 모드 저장 코드는 있지만 실제 장치의 gate 값과 적용 후 통신은 미시험입니다.

### TR069와 업데이트

Admin `System.php:1245–1297`에는 관리자용 ACS 설정 저장·cwmpClient 재시작 코드가 있습니다. rc `0x17354`는 `acs/enable == "1"`일 때 cwmpClient/cwmphealth/acsrestart 시작 분기로 들어갑니다.

이것은 TR069 비활성 설정의 정적 근거입니다. 다른 업데이트 경로·설정 재주입·기존 respawn 상태까지 모두 배제한 것은 아니므로 **FOTA 완전 차단으로 표현하지 않습니다.**

## 5. 웹 수동 업그레이드의 실제 처리 형식

수동 업로드는 화면 문자열만 있는 것이 아닙니다. Admin `System.php:351–386`에 파일 수신·관리자 권한 검사, `145–152`에 비동기 `fw_upgrade` 호출이 있습니다. TFTP/FTP/USB도 파일을 취득해 같은 helper로 전달합니다. 호출 시작을 곧바로 기록 성공으로 취급하지 않습니다.

`/bin/fw_upgrade`의 일반 실행 경로는 다음과 같습니다.

```text
main, -i 없는 일반 실행
 → intersoft_firmware_upgrade
 → tar.gz 패키지를 /tmp/upgrade에 추출
 → md5sums.enc / version.enc / TI04-708H-root.img.enc 복호화
 → MD5 목록 검증
 → bootpart에 따라 반대쪽 rootfs/rootfs2 선택
 → ubiformat으로 대상 기록
 → fw_setenv bootpart 전환, nvconvert 실행
```

`fw_decrypt`는 OpenSSL AES-256-CBC 복호화 명령을 구성합니다. **일반 OpenWrt `.ubi` 또는 `sysupgrade.bin`을 이 웹폼에 그대로 넣을 수 있다는 근거는 없습니다.** 제조사 패키지 형식에 더해 대상 slot·파티션·FIT·rootargs 호환 확인이 필요합니다. 기존 [공개 OpenWrt 설치 절차](../INSTALLATION.md)를 대체하는 검증된 경로가 아닙니다.

### 헤더 검사와 전자서명을 구분

`fw_verify_keyonet`의 256바이트 제조사 헤더·magic·`KT-GWHP`·CRC 검사는 `-i` 정보 조회 경로에서 호출됩니다. 이를 일반 업그레이드 쓰기 경로의 선행 검사라고 설명하면 틀립니다. 추적한 일반 쓰기 경로는 위 암호화 멤버 복호화·MD5 목록 검사입니다.

이 경로에서 공개키 전자서명 검증은 확인되지 않았습니다. **CRC·MD5·암호화는 전자서명과 다르며**, 이 결과가 전체 부트 체인의 서명 검사 부재나 임의 이미지 부팅 가능성을 입증하지는 않습니다.

근거: fw_upgrade `main 0x10b7c`, 실제 upgrade `0x1156c`, 복호화 `0x10fbc`, MD5 목록 검사 `0x11a6c`, 대상 slot `0x13580`, 정보 조회 `0x11a08`, 헤더 검사 `0x11120`.

## 6. 보존하는 실험 아이디어와 남은 과제

기존 초안의 실험 방향은 아래와 같이 남깁니다. 완료된 실기 시험으로 표시하지 않습니다.

1. **순정 관리자 로그인:** 실제 장치의 초기화 조건·입력값·현재 NVRAM 계정을 확인한 뒤 세션 발급 여부를 검증할 과제입니다. 기존 초안의 암호 후보는 검증 결과가 아닙니다.
2. **순정 웹을 통한 OpenWrt 설치 가능성:** 먼저 제조사 패키지·대상 slot·부트 호환성을 분석할 과제입니다. 일반 sysupgrade 파일을 직접 업로드하는 실험은 성공한 설치법으로 안내하지 않습니다. 기존 U-Boot/UART 경로와 별도 연구 항목입니다.
3. **브릿지·TR069 설정 적용:** 접근 조건, 저장·재부팅 유지와 실제 통신/프로세스를 확인해야 합니다. 기존 초안의 제안대로, 추후 순정 시험은 WAN을 분리한 사설망에서 먼저 설정을 관찰할 수 있습니다. 설정 화면 존재만으로 기능 시험 완료나 강제 업데이트 차단으로 표시하지 않습니다.
4. **메뉴별 기능:** RF 출력, Mesh 상호 운용, QoS 처리 방식, SuperDMZ 동작을 각각 시험해야 합니다.
5. **버전·리비전 차이:** 결과는 아래 해시의 2024년 v1.4.0 파일에 한정합니다. 다른 rootfs 슬롯·보드에서도 동일한지는 별도 확인이 필요합니다.

기존 OpenWrt 실기 설치·기능 시험 기록은 [공개 릴리스 검증 범위](PUBLIC_RELEASE_R1.md)에 있습니다. 그 시험은 이 순정 관리자 로그인·웹 설치 경로의 검증을 대신하지 않습니다.

## 7. 재검증용 파일 식별과 분석 근거

### 바이너리 SHA256

| 펌웨어 내부 경로 | 크기(bytes) | SHA256 |
|---|---:|---|
| `/bin/board` | 30424 | `6165e31ec0a776d5cd2437e6239d4beb7e299034e99c8f6dffbf6614f19a0d68` |
| `/bin/rc` | 275580 | `434537d6c216117f6296f65016fbad026e7f771f8d61cea33d64d4fd925e1c0e` |
| `/usr/bin/php-cgi` | 5647792 | `22f840c03da67d5147d4f33a37de1b361fddf998577937eb66dfbbceeb3e3dcd` |
| `/bin/fw_upgrade` | 85576 | `51091cc32b4dc43dbd83d5f529d7b4b3927369e433ff4ee9bdd959c8e27328dc` |

`/www/application/includes/auth.class.php` SHA256:

`219ef4b93ba35a135493e45c3470d3c778b06393a0e11ba58d4d45c27a905fa5`

함수 주소는 위 해시의 ARM ELF를 Ghidra 기본 배치로 읽은 가상 주소입니다.

### 소스 위치

아래 경로는 펌웨어 내부 경로입니다.

| 근거 | 파일·행 / 함수 주소 |
|---|---|
| Yaf | `/www/public/index.php:7`; `/www/application/Bootstrap.php:7,11,27,31,36` |
| NVRAM 인증·세션·실패 처리 | `/www/application/includes/auth.class.php:122–129,140–237,239–294` |
| 업로드 UI | `/www/application/modules/Admin/views/system/upgrade.phtml:454–466,536–543,599–712` |
| 업로드 처리 | `/www/application/modules/Admin/controllers/System.php:104–152,158–386` |
| 브릿지 제한 | `/www/application/modules/Admin/controllers/Network.php:294–301`; `/www/application/includes/network.class.php:171–220` |
| TR069 설정 | `/www/application/modules/Admin/controllers/System.php:1245–1297`; rc `0x17354` |

### 사용 도구와 한계

REA 6.5.0의 Windows Ghidra P0는 ARM ELF를 받지 않아 `target_format_unsupported`를 반환했습니다. REA에는 분석자가 선택한 board/rc/php-cgi ZIP을 전달해 파일 식별·인벤토리를 확인했습니다. **이 ZIP 검사만으로 코드 의미를 검증했다고 취급하지 않습니다.**

ARM 제어 흐름·의사코드는 별도로 설치된 **Ghidra 12.1.4 headless**로 분석하고, 주요 호출은 GNU ARM objdump의 명령·import 이름과 대조했습니다. PHP 소스는 직접 읽고 위 rootfs에서 추출한 바이트와 일치하는지 확인했습니다. 정적 분석이며 대상 프로그램을 실행한 결과가 아닙니다.

REA 수행 기록 ID:

- inventory: `ev_40b5c2c8e0941fd93f3cffc480cd21870c8dd9380ea3f691d18f86b7b34eaae3`
- inspect: `ev_b9aabe0a9c60093d49b6beacdc81fe6ce78a591e25ac8b9ecb311fc4691878f3`
- summary: `ev_c877f70ad0276fac45cfe35057b99b5dc9a061587dee1b527eee0dd4f6cdf232`

이 ID는 로컬 분석 기록의 식별자이며 공개 증거 파일 링크가 아닙니다. 제3자의 재검증에는 공개 rootfs의 해시·위 파일/행·함수 주소를 사용하세요.
