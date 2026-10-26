# TI04-708H 실험·실패 이력 — 2026-10-26

한국 시간 기준. **성공, 실제 실패, 실행 전 중단, 미검증 가설을 구분한다.** 원본 ROM/NAND·환경의 비밀 값·로그·장비별 이미지·사용자 PC 경로는 비공개로 보관한다.

현재 결론: **NOR 환경 변경과 UART 콘솔, NAND 전체 백업, OpenWrt RAM 부팅은 성공. NAND 영구 설치는 아직 실행하지 않았다.** 기술 설명은 [종합 보고서](../OPENWRT_INSTALLATION_ANALYSIS_REPORT.md)를 참조한다.

## 1. 초기 접근 경로

| 시도 | 관측 결과 | 판정과 남은 한계 |
|---|---|---|
| 일반 관리 UI/공통 JavaScript | 조사 범위에서 로컬 펌웨어 업로드 경로 미확보 | ‘장비 전체에 없음’으로 확대하지 않음 |
| 별도 관리자 로그인 | 성공 인증·인증 후 메뉴 미확보 | 준비72개가 모두 소진된 기록 아님. 과거 상태 nextIndex25/요청35회, 잠금 재시험 포함 |
| DDNS/UPnP 등 | UART 제어·임의 명령 실행·업로드 경로 확보 실패 | 전체 취약점 부재 증명 아님; DDNS 시험 후 복원 기록 보존 |
| 초기 UART 공백·ESC·숫자 송신 | 순정 mode0에서 부팅 중단 실패 | PC 송신·Linux TTY 에코와 U-Boot 콘솔을 구분 |
| SW4+SW1 및 반복 중단 문자열 | 시행한 시험에서 U-Boot 프롬프트 미확인 | 버튼↔GPIO 매핑 미확정. 물리 버튼만으로 진입 불가능하다는 증명도 아님 |

## 2. NOR 읽기와 환경 기록

| 시도 | 관측 결과 | 조치 / 판정 |
|---|---|---|
| CH341A JEDEC/2MiB 읽기3회 | ID·용량·세 파일 byte/SHA 일치 | NOR 사용자 영역 백업 성공. 완전 복원 시험 아님 |
| 첫 수동 ESC2012 기록 | 전원 인가 전 Verify 확인 못함 | 다음 부팅에서 `bad CRC, using default environment`; ESC 진입 실패 |
| 첫 실패 후 readback | 유효 CRC의13개 기본 환경, bootdelay2. 원래 환경18개와 다름 | 실제 첫 기록 바이트가 없어 최초 원인 미확정. 기본 환경 로드/후속 saveenv 코드와 부합 |
| 네이티브4096바이트 읽기 | 첫 전송 오류,0바이트 부분 파일 | 쓰기 없이 중단.2048바이트 전송으로 조정 후 독립 전체 읽기3회 일치 |
| 섹터 writer 첫 Apply | AsProgrammer가 실행 중 | 장치 접근/erase/write 전에 중단. 사용자 종료 후 재개 |
| 17:23 제한된 재기록 | 4KiB erase1회,256바이트 page16회; 페이지별 및 전체2MiB 비교 통과 | 별도 device session의 전체3회 읽기도 후보와 일치 |

원본 대비 변경31바이트는 환경 첫4KiB에 한정됐다. 기록 직전 기본 환경과 비교하면248바이트다. 두 숫자의 비교 기준이 다르며 서로 모순이 아니다. 다른17개 원본 환경 항목/순서 및 APPSBL/ART는 보존됐다.

## 3. UART 터미널에서 생긴 별도 실패

| 시점/현상 | 관측 결과 | 수정 / 해석 |
|---|---|---|
| 부팅을 기다리던 터미널 | 프로세스 종료, 상태 파일에는 running=true가 남음. 수신0/ESC0 | 실제 프로세스를 재확인하고 재실행. 이때 ‘부트로더 정지’는 미확인 |
| 17:43 첫 성공 부팅 | `(IPQ40xx) #`가 수신됐으나 뒤의 ESC 되울림 때문에 감지 실패 | PC 감지기 버그. 프롬프트 대기 상태를 장비 고장으로 해석하지 않음 |
| 첫 감지 실패의 자동 송신 | 제한15초까지 총902 ESC, 키보드 잠금 유지 | 정규식에 ESC 되울림 허용. 실제 RX 청크 재생 검사 통과 |
| 이후 두 재부팅 | 자동 시험이 이미 종료돼 일반 Linux 부팅 | 패치가 다시 사라진 증거 아님 |
| 17:50 재시험 | 프롬프트 검출, ESC195바이트에서 중단, 키보드 활성화 | U-Boot 콘솔 진입 성공 |
| version/선택 printenv | TI04-708H, U-Boot2012.07, bootdelay2012, serial 입출력 응답 | 양방향 명령 실행 성공 |

첫 성공 부팅 이후 검토한 구간에는 CRC 경고가 없었다. 전체 복원 가능성이나 모든 향후 부팅의 성공 보장은 아니다.

## 4. 콘솔 진입 후 명령·네트워크

| 시도 | 관측 결과 | 조치 / 판정 |
|---|---|---|
| help / nand read.raw / tftpput | 에코 후 즉시 프롬프트, 실제 작업 없음 | 원본 코드에서 debug_mode 검사 발견. 세션에만 on 설정 후 동작 |
| bdinfo / iminfo | Unknown command | 이 빌드에 없는 명령으로 기록. smeminfo·원본 코드·CRC 조회 활용 |
| NAND geometry / bad block 조회 | page2048/OOB64/erase131072, 조회한 불량 블록0 | NAND device1, 별도 NOR device2를 구분 |
| 초기 TFTP PUT | .part0바이트, 재시도 및 서버 시간 초과 | 제한 시간 후 중단. 요청 블록 크기 협상과 서버 처리 수정 뒤 첫 raw 조각 전송 성공 |
| 블록 크기 협상 | 512 및1468바이트 요청/응답 확인 | 서버 loopback RRQ/WRQ·중복 마지막 DATA·잘못된 크기 거부 검사 수행 |
| 전체 NAND 백업 | ECC main128개, raw+OOB128개 전송 | manifest·coverage·size·SHA·조립 후 재읽기 검사 모두 통과 |
| ECC/raw main 비교 | 174바이트 차이, UART에 ECC corrected 메시지 | 원시 읽기와 ECC 처리 읽기를 별도 보관. 오류로 숨기거나 같은 형식으로 취급하지 않음 |

전송에 사용한 실제 IP·프로세스 ID는 공개 이력에서 제외했다. 해당 주소·상태는 매 작업 시작 때 다시 확인한다.

## 5. RAM 이미지 후보별 결과

| 후보 / 검토 | 실제 실행 범위 | 결과 |
|---|---|---|
| 기존 sysupgrade TAR | 오프라인 해석 | kernel+DTB FIT와 SquashFS root. initramfs 아님 |
| 최소 V1 FIT | 오프라인 구성·검토만 | ramdisk load 누락을 코드 검토로 발견; 그대로 부팅하지 않음 |
| 최소 V2 LZMA FIT | TFTP·전체 CRC·bootm 실행 | payload CRC32/SHA1 통과 후 `Unimplemented compression type 3`; 커널 실행 전 U-Boot 복귀 |
| 최소 V3 gzip FIT | TFTP·CRC까지만 | gzip 출력 한도8MiB를 코드로 확인.12,124,224바이트 kernel이 초과해 부팅하지 않음. gzip 실기 부팅 실패로 기록하면 안 됨 |
| 최소 V4 비압축 FIT | bootm, kernel, initramfs, UART 명령 | **RAM 부팅 성공**. 플래시 노드 disabled, /proc/mtd 비어 있음 |
| devtmpfs mount | 최소 init에서 시도 | `No such device`. /dev/console 준비 후 셸 정상 동작; 전체 환경은 tmpfs /dev 사용 |
| 전체 rootfs, 모든 MTD 읽기 전용 | procd·module·network 부팅 | **OpenWrt RAM 환경 성공**, 유선 ping/HTTP200, 무선 PHY2개 |
| 위 환경의 UBI autoattach | 128MiB 전체 읽기 전용 조회 | 후반 PEB384의 다른 image sequence로 attach 실패. RAM 부팅은 계속됨; 플래시 기록 실패가 아님 |
| 설치용 RAM 환경 | 앞32MiB만 writeable, 나머지 read-only | 정상 부팅 및 경계/flags/UBI 미attach 확인. 아직 NAND 기록 없음 |

후보를 생성한 사실, RAM 전송 완료, 부트로더 해시 검증, kernel 실행, 사용자 환경 부팅, NAND 영구 설치를 각각 별개의 상태로 기록했다.

## 6. 설치 후보 생성 중 검증 실패

- 첫 builder는 원본 환경에서 `ethaddr` 키를 찾지 못해 중단됐다. 실제 키는 `base_mac`이었다.
- 다음 검사에서 base_mac의 unicast 유효성이 통과하지 않아 중단됐다. 원본 값을 수정하지 않고 Linux용 안정적 locally administered MAC을 생성하도록 수정했다.
- 수정 후 kernel/DTB/cpio/FIT/UBI를 새 산출물로 생성했다. UBI EC/VID CRC와 volume payload 재구성, 파일 해시 검증이 통과했다. 이 두 builder 실패는 PC 파일 생성 단계이며 장비 기록 실패가 아니다.
- 후보에는 순정 bootipq용 config 이름과 비압축 kernel,32MiB 설치 경계가 있다. 일반 sysupgrade 재설치를 그대로 허용하지 않는다.

## 7. 실행 도구 차단과 사용자 수동 서버

1. 이미지 전송 서버와 RAM 다운로드를 준비하던 명령이 자동 승인 검토에서 `blocked by policy`로 거절됐다. 구체 사유는 없었고 CreateProcess 이전이라 내부 명령은 실행되지 않았다.
2. 사용자의 재진행 요청 후 현재 유선 대역에 맞춘 명령도 동일하게 거절됐다. 사용자의 설치 의사와 별개의 실행 도구 제한이며 다른 도구로 우회하지 않았다.
3. 사용자 PowerShell에서 호출 줄이 변수 설정보다 먼저 입력돼 `BadExpression`이 발생했다. 이 시도에서는 서버가 시작되지 않았다.
4. 변수 없는 한 줄 명령으로 정정 후 사용자가 직접 실행했고, 지정 포트 LISTEN 상태를 확인했다. 대기 중인 서버 창은 종료하지 않도록 안내했다.
5. **문서 갱신 시점에는 서버 시작까지 확인했다. 설치용 파일의 공유기 RAM 다운로드 완료 및 NAND 영구 기록은 미확인/미실행이다.**

## 8. 기존 문서의 단정 수정

- ‘72종 모두 실패’, ‘8801 기능 부재’, ‘TR-069 전자서명 푸시 전용’, ‘관리자 암호 생성 규칙 확정’을 근거 범위에 맞춰 정정했다.
- GPIO raw 레지스터 검사를 ‘두 핀 접지’로 번역한 부분과 GPIO63=SW4 단정, mode0의 ‘1초’ 단정을 정정했다.
- ‘100% 안전’, ‘언제든100% 복원’, ‘NOR 백업=전체 순정 복구본’ 표현을 제거했다.
- 공통 initramfs 파일 이름/주소만으로 부팅할 수 있다는 안내와 기존 sysupgrade 즉시 설치 경로를 실기 제약으로 대체했다.
- README 3~6절의 원래 실험 제안은 사용자 요청대로 원문을 보존했다. 현재 상태 설명과 분리하고 이 정정 기록을 연결했다.

## 남은 완료 조건

설치 후보 다운로드와 SHA 확인 → 현재 경계/장치 재확인 → 제한된32MiB 기록 → volume 및 NOR/후반96MiB readback → 순정 bootipq NAND 부팅 → 두 번째 재부팅/overlay·설정 유지 → LAN DHCP/관리 UI·WAN·무선 검증. 각 단계의 실제 결과가 생기기 전 성공으로 표시하지 않는다.
