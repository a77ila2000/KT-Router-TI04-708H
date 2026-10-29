# TI04-708H 설치 — 공개 시험판 r1

**[설치 패키지 다운로드](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/download/v25.12.6-ti04-r1/ti04-openwrt-25.12.6-r1-install.zip)** · [파일/검증 범위](docs/PUBLIC_RELEASE_R1.md) · [빌드 소스](firmware/BUILD.md)

대상: **allRadio TI04-708H / WGHE010100**, IPQ4018/256MiB, U33 GD25Q16CSIG(C8 40 15,2MiB), Macronix128MiB SPI NAND(page2048/OOB64/erase131072), 제조사 U-Boot2012.07. 비슷한 KT 모델이나 불량 NAND 블록이 있는 장비는 이번 도구의 지원 범위 밖이다.

**새 공개 이미지/범용 도구는 오프라인 검증만 마쳤으며 아직 실기 기록·부팅 전이다.** 기존 개인용25.12.6의 실기 성공과 구분한다. [남은 검증](docs/PUBLIC_RELEASE_R1.md#검증과-한계)을 확인한다.

## 1. PC와 파일 준비

Windows PowerShell5.1, Python3.11 이상, CH341A/SOP8 클립,3.3V TTL UART, Ethernet 케이블, 별도 백업 저장소를 준비한다. [AsProgrammer2.1.2 공식 배포](https://github.com/nofeletru/UsbAsp-flash/releases/tag/v2.1.2)에서 WCH 드라이버와 `CH341DLL.DLL`을 준비한다. DLL/드라이버는 재배포하지 않는다. 지원 DLL의 SHA/서명 검사는 도구에 포함돼 있다.

설치 ZIP을 예를 들어 `C:\ti04`에 푼다. 이하 PC 명령은 그 폴더에서 실행한다. `python --version`으로3.11 이상인지 확인한다. Python이 `py`로만 실행된다면 명령의 `python`을 `py -3`으로 바꾸고 CH341 기록 명령에는 `-Python py`를 추가한다.

```powershell
cd C:\ti04
python scripts\verify_release.py .
```

`PASS`가 필요하다. **Code → Download ZIP은 소스만 받는다.** 위 설치 패키지를 받는다. `.ubi`는 순정 관리자/LuCI 업로드용 파일이 아니다.

## 2. 자기 NOR 독립 백업

공유기 DC 전원·LAN·UART를 모두 분리하고 프로그래머/클립만 연결한다. 전원과 신호 전압을 확인한다. GD25Q16C는3.3V 계열이므로1.8V 어댑터를 무조건 끼우지 않는다. AsProgrammer를 닫는다.

다음 도구는32비트 PowerShell을 사용한다. DLL 경로는 자기 PC에 맞게 바꾸고, 출력에는 **존재하지 않는 새 절대 경로**를 사용한다.

```powershell
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\ch341_nor.ps1 -Mode Read -DllPath "C:\tools\AsProgrammer\CH341DLL.DLL" -OutputDirectory "C:\ti04-private\nor-original" -BoardUnpoweredAndOtherCablesRemoved
python scripts\verify_dump.py --expected-size 2097152 C:\ti04-private\nor-original\nor-read1.bin C:\ti04-private\nor-original\nor-read2.bin C:\ti04-private\nor-original\nor-read3.bin
```

3회 읽기의 크기/내용이 일치해야 한다. `FFFFFF`, `000000`, 다른 JEDEC나 내용 불일치면 중단한다. 반복 일치만으로 칩/백업 유효성이 모두 증명되는 것은 아니다. 자기 원본을 별도 저장소에도 보관하고 공개하지 않는다.

## 3. 자기 환경만 ESC2012 패치

```powershell
python scripts\patch_nor_env.py --source C:\ti04-private\nor-original\nor-read1.bin --read2 C:\ti04-private\nor-original\nor-read2.bin --read3 C:\ti04-private\nor-original\nor-read3.bin --out C:\ti04-private\patch
```

CRC가 유효하고 `bootdelay=0`인 환경만 받는다. 다른 키/값/순서를 보존하며 `bootdelay=2012`와 CRC만 바꾼다. 변경이 `[0xE0000,0xE1000)`4KiB를 넘으면 거부한다.2012는 제조사 ESC 모드 선택값이다.

공유기는 계속 무전원/프로그래머만 연결한 상태로 둔다. 아래 기록기는4KiB 한 섹터만 erase/program한다. 전체 erase·상태 레지스터 변경·unprotect는 구현하지 않았다.

```powershell
C:\Windows\SysWOW64\WindowsPowerShell\v1.0\powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\ch341_nor.ps1 -Mode WriteEnv -DllPath "C:\tools\AsProgrammer\CH341DLL.DLL" -Source C:\ti04-private\nor-original\nor-read1.bin -Read2 C:\ti04-private\nor-original\nor-read2.bin -Read3 C:\ti04-private\nor-original\nor-read3.bin -Candidate C:\ti04-private\patch\own-nor-esc2012.bin -OutputDirectory C:\ti04-private\nor-write -BoardUnpoweredAndOtherCablesRemoved
```

live NOR가 자기 원본과 다르면 거부한다. 성공 뒤에도 아직 전원을 켜지 않는다.2절 Read를 새 폴더 `C:\ti04-private\nor-after`로 다시 실행해3회 일치를 확인하고 다음을 실행한다.

```powershell
python scripts\patch_nor_env.py --source C:\ti04-private\nor-original\nor-read1.bin --read2 C:\ti04-private\nor-original\nor-read2.bin --read3 C:\ti04-private\nor-original\nor-read3.bin --verify-readback C:\ti04-private\nor-after\nor-read1.bin
```

전체2MiB 비교와 CRC 검사가 통과해야 한다. 첫 수동 기록 때 전원 전 Verify를 확인하지 않아 `bad CRC`로 실패한 이력이 있다. 이 검사를 생략하지 않는다. 생성된 자기 NOR/패치/receipt는 다른 기기에 사용하지 않는다.

## 4. UART와 주소 준비

CH341A와 클립을 분리한다. UART115200 8N1, DTR/RTS 끔, **VCC 미연결**로 연결한다. 관측 CN1은 사각① 기준②→어댑터RX,③←TX,④→GND였으나 자기 보드 배선 확인을 우선한다. [하드웨어 기록](RESEARCH_NOTES.md)을 참고한다.

전원 인가 직후 ESC `0x1B`를 짧게 반복해 `(IPQ40xx) #`가 뜨면 송신을 멈춘다. 터미널에서:

```text
version
setenv debug_mode on
nand device
nand bad
```

TI04-708H/U-Boot2012.07, Device1 nand1,2048/64/131072, 불량 블록 없음이 기준이다. `saveenv`는 하지 않는다.

WAN은 분리하고 PC–LAN을 직접 연결한다. 실물 LAN4는 현재 Linux 통신이 확인된 포트다. PC 유선 어댑터를 수동 `192.168.1.2/24`로 설정한다. 아래는 **PC192.168.1.2 / 공유기192.168.1.1** 예시다. 실제 주소/COM/DLL 경로를 명령과 일치시키고 다른 같은 대역 연결은 피한다. 설치 뒤 PC는 DHCP 자동으로 복구한다.

## 5. NAND 전체 백업

PC 첫 PowerShell에서 TFTP 서버를 연다. 방화벽은 해당 프로세스/분리된 유선 연결의 UDP69와 전송용 UDP 포트를 허용한다. 방화벽 전체를 끄지 않는다.

```powershell
python scripts\tftp_server.py --bind 192.168.1.2 --peer 192.168.1.1 --output C:\ti04-private\nand-chunks --read ram.fit=ti04-25.12.6-ram-installer.itb
```

UART 터미널만 닫아 COM을 해제한다. 두 번째 PowerShell에서 **실제 COM 번호**로 바꿔 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_nand.ps1 -Port COM7 -ServerIP 192.168.1.2 -RouterIP 192.168.1.1 -Chunks C:\ti04-private\nand-chunks
```

U-Boot `nand read`/`read.raw`→RAM CRC→TFTP만 실행한다. `read.raw`의200은512페이지다. main128개/raw128개 조각을 받는다. 서버 제한 시간30분이 만료되면 같은 완료 파일을 덮어쓰지 말고 새 백업 실행으로 다시 검증한다. 실패/스킵/시간 초과면 중단한다.

```powershell
python scripts\verify_backups.py --chunks C:\ti04-private\nand-chunks --nor-readback C:\ti04-private\nor-after\nor-read1.bin --out C:\ti04-private\verified-backup
```

ECC main134,217,728바이트와 raw+OOB138,412,032바이트를 조립하고 CRC/SHA를 검사한다. `own-backup-receipt.json`은 자기 보존 영역 해시다. 백업/receipt를 별도 저장소에도 복사한다. raw와ECC main은 차이가 있을 수 있으며 같은 복원 형식이 아니다. 실제 복원 시험은 아직 없다.

## 6. 설치용 RAM 부팅

백업기가 종료되면 UART 터미널을 다시 연다. TFTP 서버 실행 여부를 확인한다. 만료됐다면5절 명령의 `--output`을 다른 새 경로로 바꿔 다시 실행한다. U-Boot에서:

```text
setenv ipaddr 192.168.1.1
setenv serverip 192.168.1.2
setenv netmask 255.255.255.0
setenv initrd_high 83f00000
setenv fdt_high 83e00000
setenv bootargs console=ttyMSM0,115200 rdinit=/init root=/dev/ram0 loglevel=6
tftpboot 84000000 ram.fit
iminfo 84000000
```

전송 크기가 `RAM_BOOT.json`의bytes/size_hex와 맞고 FIT hash 검사가 통과해야 한다. `crc32 84000000 SIZE_HEX`를 실행해 그 파일의crc32와 비교한다. **SIZE_HEX는 실제16진수 값으로 바꾼다.** 일치하면:

```text
bootm 84000000#config@1
```

RAM Linux가 뜨면 Enter로 셸에 진입한다. `cat /etc/ti04-installer-release`는 `25.12.6-ti04-r1`, mount의 `/`는tmpfs여야 한다. NAND가 자동 attach돼 있으면 설치기는 거부한다.

## 7. 이미지 전달과 사전 검사

PC에서 TFTP를 종료하고 HTTP 서버를 연다. **IMAGE_SHA256은manifest.json의files.ubi.sha256 64글자로 바꾼다.** 서버는 아래 세 파일만 지정 peer에20분간 제공한다.

```powershell
python scripts\serve_image.py --bind 192.168.1.2 --peer 192.168.1.1 --file ti04-25.12.6-first32m.ubi --sha256 IMAGE_SHA256 --manifest manifest.json --receipt C:\ti04-private\verified-backup\own-backup-receipt.json
```

**공유기 UART 셸에서**:

```sh
mkdir /tmp/ti04-bundle
uclient-fetch -O /tmp/ti04-bundle/ti04-25.12.6-first32m.ubi http://192.168.1.2:8000/install.ubi
uclient-fetch -O /tmp/ti04-bundle/manifest.json http://192.168.1.2:8000/manifest.json
uclient-fetch -O /tmp/own-backup-receipt.json http://192.168.1.2:8000/own-backup-receipt.json
/usr/sbin/ti04-install --check /tmp/ti04-bundle /tmp/own-backup-receipt.json
```

`TI04_ALL_INSTALL_GUARDS_PASS`가 필요하다. 실제 IP가 다르다면 서버bind/peer와 다운로드 주소를 맞춘다. 오류를 피하려고 guard를 지우지 않는다.

## 8. 앞32MiB 기록/검증

**앞32MiB의 기존 데이터를 지우는 명령이다.** 자기 백업을 별도 보관하고7절을 통과한 뒤 실행한다.

```sh
/usr/sbin/ti04-install --apply /tmp/ti04-bundle /tmp/own-backup-receipt.json WRITE-FIRST32M
```

RAM marker/root/board, 동적 MTD 이름·offset·size·geometry·flags·불량 블록·UBI 미attach, 파일SHA와 RAM 내manifest, 자기 NOR8개 영역/NAND뒤96MiB 해시를 검사한다. 앞32MiB만 `ubiformat`하고 kernel/rootfs 볼륨 readback SHA와 보존 해시를 다시 검사한다. rootfs_data는남는공간으로 확장된다. 같은 RAM 세션의 재기록은 거부한다.

**erase/program 중 Ctrl+C/전원 차단을 하지 않는다.** 오류면 RAM과 자기 백업을 보존한다. 성공 메시지는 `TI04_WRITE_READBACK_PRESERVATION_PASS`다. 아직 NAND 부팅 확인 전이다.

## 9. NAND 자동 부팅과 첫 설정

검증 성공 뒤 UART 셸에서 `reboot`한다. ESC/TFTP 없이 stock bootipq의config@5와 OpenWrt25.12.6/Linux6.12.112 진입, `/rom`SquashFS·`/overlay`UBIFS·overlayfs root를 확인한다. PC를 DHCP 자동으로 복구하고 [LuCI](http://192.168.1.1/)에 접속한다.

1. 초기 root 암호는 비어 있다. UART/분리된 LAN에서 자기 암호를 바로 설정한다. host key/웹 인증서는 장비에서 생성한다.
2. `/etc`에 시험 파일을 만들고 정상 재부팅 뒤 내용이 유지되는지 확인한다.
3. Argon/한국어가 기본이다. **시스템 → 시스템 → 언어 및 스타일 → English**로 영문 전환한다.
4. Wi-Fi는두대역 모두 꺼져 있다. 자기 국가·SSID·WPA 암호를 설정하고 **2.4GHz Wi-Fi / 5GHz Wi-Fi**를 구분해 켠다.
5. 연결한 LAN의통신/LED, 각 무선의실제 양방향 전송을 확인한 뒤 WAN의DHCP·DNS·NAT를 확인한다.
6. **네트워크 → 최대 송신 출력**은 현재 드라이버의자동/수동 상한이다.35dBm 고정 패치는 아니다.

일반 sysupgrade/다른 보드 이미지는 사용하지 않는다. 초기화 버튼 GPIO는미확정이므로 비활성화돼 있다. 새 공개 빌드의물리 전원 재인가·복원·장기 시험은남아있다.

## 문제가 생기면

| 증상 | 조치 |
|---|---|
| JEDEC/CRC/readback 불일치 | 무전원 유지, 자기 원본·접촉/전압·실제 칩부터 확인 |
| ESC 없음/bad CRC | NAND 단계 중단, 자기 NOR CRC와 전체readback부터 확인 |
| 명령이 에코만 남음 | U-Boot 세션debug_mode=on 확인, saveenv하지 않음 |
| TFTP 없음 | 케이블·PC고정IP·bind/peer/serverip·방화벽·서버 만료 확인 |
| guard 실패 | 오류가 지목한 실제 값 확인, 다른 기기의해시/MTD값으로 바꾸지 않음 |
| QCA8075/root mount 오류 | 공개 FIT/manifest/hash 일치 확인, 과거 실패 kernel/다른 DTB를 섞지 않음 |
| 기록 후 검증 실패 | 재부팅 강행/전체 플래시 덮어쓰기 없이 RAM과 자기 백업 보존 |

[실패·수정 이력](docs/EXPERIMENT_LOG_20261026.md), [포팅 제약](OPENWRT_INSTALLATION_ANALYSIS_REPORT.md), [미검증 아이디어](RESEARCH_NOTES.md)를 보존한다. 실기 검증 전인 완전 복원 명령을 추측해 제공하지 않는다. 공개 이슈에는백업·receipt·계정/키·MAC/SSID·전체로그를 올리지 않는다.
