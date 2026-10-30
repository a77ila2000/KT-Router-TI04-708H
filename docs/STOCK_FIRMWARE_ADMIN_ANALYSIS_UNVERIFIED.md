# KT GiGA WiFi Wave 2 (TI04-708H) 순정 펌웨어 8801 관리자 분석 노트 (미검증)

> [!WARNING]
> **미검증 연구 노트 (Unverified / Experimental Research Note)**
> 본 문서는 KT 순정 펌웨어(v1.4.0) NAND 덤프(`nand-main-ecc.bin`)에서 추출한 rootfs, 바이너리(`/bin/board`, `/bin/rc`, `/usr/bin/php-cgi`), 그리고 웹 애플리케이션 프레임워크 소스코드 정적 분석(Reverse Engineering)을 통해 도출된 내용입니다.
> 
> 실제 기기 웹 UI 진입 및 기능 동작 검증은 아직 수행되지 않았으며, 추후 연구 및 하드웨어 복구/개조를 위한 참고용 초안입니다.
> 
> 📦 **분석용 순정 롬 덤프 다운로드**: [GitHub Releases (stock-dump-v1.4.0)](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/stock-dump-v1.4.0) · [덤프 안내 문서](../dumps/README.md)

---

## 1. 개요 및 분석 배경

* **대상 기기**: KT GiGA WiFi Wave 2 (올래디오 제조, 모델명: `TI04-708H`)
* **SoC / 아키텍처**: Qualcomm Atheros IPQ4019 (ARMv7 32-bit Cortex-A7)
* **순정 펌웨어 버전**: v1.4.0 (Linux Kernel 3.14.77 기반)
* **분석 목적**: 
  * 일반 사용자 웹 UI(`:8899`)에서는 수동 펌웨어 업로드나 브릿지 모드 등의 고급 제어가 차단되어 있음.
  * 포트 스캔에서 식별된 `:8801` 포트의 정체, 엔지니어 관리자 계정 생성 규칙, 수동 펌웨어 업로드 가능 여부 규명.

---

## 2. 웹 서버 아키텍처 및 포트 격리 구조

* **웹 서버 데몬**: `lighttpd` + FastCGI (`/usr/bin/php-cgi`)
* **웹 프레임워크**: Zend Framework 기반 MVC 구조 (`/www/application/`)

### 포트 분리 및 접근 제어 (`/bin/rc` 바이너리 분석)
부팅 시 `/bin/rc` 바이너리가 `/var/etc/lighttpd.conf`를 동적으로 생성하며 다음과 같은 접근 제어 규칙을 적용합니다:

```text
# 일반 사용자 포트 (:8899 / nvram "http/uport")
$SERVER["socket"] == ":8899" {
    $HTTP["url"] =~ "/admin" {
        url.access-deny = ( "" )   <-- 일반 포트에서는 /admin 접근 원천 차단
    }
}

# 엔지니어 관리자 메인 포트 (:8801 / nvram "http/port")
server.port = 8801                 <-- 8801 포트로만 /admin 모듈 허용
```

* 일반 포트(`:8899` 또는 `:80`)로 접속 시 엔지니어 관리 페이지(`/admin`)는 웹서버 차원에서 차단됩니다.
* 엔지니어 전용 관리자 페이지는 반드시 **`http://172.30.1.254:8801/admin/login/login`**으로 접근해야 합니다.

---

## 3. 관리자 계정 인증 알고리즘 역공학

`/www/application/includes/auth.class.php` 및 `/bin/board` 바이너리의 디스어셈블리 분석 결과:

### 1) 관리자 아이디 (loginid)
* `auth.class.php`에서 `nvram_get("system/adminname")`을 호출하여 인증.
* `/bin/board` 바이너리가 설정하는 기본값: **`ktadmin`**
  *(일반적으로 널리 알려진 `ktroot`가 아님)*

### 2) 관리자 비밀번호 (loginpwd)
* 공유기 부팅 시 `/bin/board`의 `Change admin id/pwd by kt hash string` 함수가 동적으로 비밀번호를 생성하여 NVRAM에 저장합니다.
* **해시 생성 재료**:
  1. `WAN MAC 주소`: 콜론(`:`) 없는 대문자 12자리 (예: `000789D56EC9`)
  2. `모델명`: 대문자 문자열 (`TI04-708H`)
  3. `KT Salt 문자열`: **`GIGALAND1409`** (바이너리 내 하드코딩)
* **알고리즘**:
  ```python
  # 포맷 스트링: "%s%s%s"
  hash_input = f"{WAN_MAC}{MODEL}GIGALAND1409"
  md5_hex = hashlib.md5(hash_input.encode()).hexdigest()
  admin_password = md5_hex[:10]  # MD5 32자리 hex 중 앞 10자리 (소문자)
  ```
* **암호화 저장 및 복호화**:
  * 생성된 평문 10자리는 AES-128-CBC로 암호화되어 NVRAM(`system/adminpass`)에 저장됩니다.
  * AES 키: `abcdel67890inter` (16바이트)
  * 웹 로그인 시 `auth.class.php`가 `apmib_aes_cbc_decrypt(nvram_get("system/adminpass"))`를 호출하여 사용자가 입력한 `loginpwd`와 일치하는지 비교합니다.

### 3) 무차별 대입 방어 (Brute-force Protection)
* 코드 내 상수: `LOGINFAILCNT = 5`, `LOGINFAILTIME = 600` (10분)
* 로그인 5회 연속 실패 시 `/tmp/admin_loginfail` 파일이 생성되며, 10분간 로그인이 잠깁니다.

---

## 4. 8801 관리자 UI 탑재 기능 목록

순정 rootfs의 `/www/application/modules/Admin/views/`에 존재하는 35개 이상의 뷰 파일 목록입니다. 일반 `:8899` 화면에서는 비활성화/숨김 처리되었던 고급 기능들이 실제 구현되어 있습니다.

| 분류 | 뷰 파일 | 주요 제공 기능 |
|---|---|---|
| **시스템 관리** | `system/upgrade.phtml` | **PC 수동 펌웨어 업로드(`<input type="file">`)**, TFTP/FTP/USB 업그레이드 |
| | `system/tr069.phtml` | KT 본사 ACS 서버 URL 및 주기 설정, FOTA 강제 업데이트 차단 |
| | `system/iperf.phtml` | 공유기 내장 iperf 네트워크 대역폭 성능 측정 |
| | `system/webserver.phtml` | 웹 관리자 포트 번호(`8801`, `8899`) 변경 |
| | `system/httpacl.phtml` | 특정 IP 대역만 관리자 웹 접속을 허용하는 접근 제어(ACL) |
| **네트워크 모드** | `network/sysmode.phtml` | **공유기(Router / NAT) 모드 $\leftrightarrow$ 브릿지(Bridge / AP) 모드 전환** |
| | `network/wan.phtml`, `wan2.phtml` | WAN 연결 방식(DHCP/PPPoE/Static), VLAN 태깅, MTU, MAC Clone |
| | `network/lan.phtml` | 내부 LAN IP 대역 및 DHCP 서버 범위 설정 |
| **스위치 / LAN** | `switch/portmirror.phtml` | 패킷 덤프 및 분석을 위한 LAN 포트 미러링(Port Mirroring) |
| | `switch/igmp.phtml` | IPTV 멀티캐스트 트래픽 분배 및 IGMP Snooping 토글 |
| | `switch/ratectl.phtml`, `qos.phtml` | 하드웨어 기반 포트별 대역폭 속도 제한 및 트래픽 우선순위 |
| **무선 제어 (Wi-Fi)** | `wlan/radio.phtml` | 2.4GHz / 5GHz RF 송신 출력(Tx Power) 및 채널 대역폭 설정 |
| | `wlan/mesh.phtml` | KT EasyMesh 연동 설정 |
| | `wlan/airtime.phtml` | Airtime Fairness 공용 시간 제어 |
| | `wlan/speedlimit.phtml` | 무선 클라이언트별 전송 속도 제한 |
| **보안 / NAT** | `nat/portfwd.phtml` | 포트 포워딩 규칙 추가/삭제 |
| | `nat/dmz.phtml` | DMZ 및 Twin IP (공인 IP 직접 할당) |
| | `nat/firewall.phtml`, `filter.phtml` | SPI 방화벽 및 패킷 필터링 |

---

## 5. 핵심 관전 포인트 및 후속 검증 과제

1. **웹 수동 플래싱(`/system/upgrade`)의 서명 검증 여부**:
   * `upgrade.phtml`을 통해 OpenWrt `sysupgrade.bin` 업로드 시 커널/헤더 서명 체크 로직이 동작하는지 확인 필요.
   * 서명 검증에서 반려될 경우 이전과 같이 U-Boot TFTP 또는 UART 콘솔 주입 필요.
2. **실제 하드웨어 로그인 테스트**:
   * 계산된 비밀번호 후보(`fc46929303` 등)를 기기에 직접 입력하여 세션이 정상 발급되는지 검증 필요.
3. **TR-069 차단**:
   * 순정 펌웨어 상태에서 사설망 연결 시 KT 중앙 관리 서버에 의해 설정이 초기화되거나 펌웨어가 자동 업데이트되지 않도록 WAN 분리 상태에서 설정 검증 권장.
