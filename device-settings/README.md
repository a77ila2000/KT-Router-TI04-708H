# TI04 설치 후 LED·시간 설정

> 2026-10-29 [공개 r1 이미지](../docs/PUBLIC_RELEASE_R1.md)에는 이 설정을 포함했습니다. 아래의 ‘기존 UBI’와 별도 적용 절차는 이전 개인용 이미지 기준입니다. 새 공개 이미지의 실기 부팅은 아직 확인 전입니다.

OpenWrt25.12.6을 설치한 **allRadio TI04-708H / WGHE010100 한 대**에서 적용한 후속 설정이다. 기존 UBI 이미지에는 포함하지 않았으며, 공개 설치 이미지나 범용 설치기를 대신하지 않는다. 첫 설치는 [설치 안내](../INSTALLATION.md)를 따른다.

## 적용 결과와 범위

| 기능 | 동작 | 확인 범위 |
|---|---|---|
| WAN | 연결 시 점등, 송수신 시 점멸 | 사용자 실물 확인 |
| LAN1~4 | 각 인터페이스의 연결 시 점등, 활동 시 점멸, 미연결 시 소등 | LED 번호 순서 실물 확인, 실제 LAN4 연결·점멸 확인. 나머지 케이블 포트 시험은 남음 |
| 공용 Wi-Fi | 어느 대역이든 활성화되면 점등, 무선 송수신 시 점멸, 두 대역 모두 비활성화면 소등 | 2.4/5GHz 각각 밝기 변화·송신 카운터 확인, 원래 무선 설정 복원 |
| 시간 | OpenWrt 기본 NTP 클라이언트 | 서비스 실행, UTC 시각 오차5초 이내 확인 |

LAN 표시등 제어 채널은 PHY1→4가 실제 **LAN4→1** 순서였다. `src/ti04-phy-led.c`는 `lan1`의 연결·바이트 수를 PHY4 LED1에, `lan2`를 PHY3에, `lan3`을 PHY2에, `lan4`를 PHY1에 연결한다. 이 실물 매핑은 다른 모델에 적용하지 않는다. 이전 문서의 ‘실물 LAN1’ 표기는 내부 인터페이스와 실물 번호를 구분하지 못했던 당시 기록이며, 최종 케이블 위치는 사용자 확인 기준 **실물 LAN4**다.

LAN 상태는1초마다 확인하고, 실제 점멸은 PHY 하드웨어 모드로 수행한다. 짧은 트래픽도 다음 조회 때 바이트 증가로 감지하지만 패킷마다 정확히 점멸하는 방식은 아니다. 제어 프로그램은 QCA8075 ID `004dd0b1` 다섯 개를 검사하고 MMD7 LED1 제어만 사용한다. 종료 신호를 받으면 시작 전 값을 복원한다. 확인된 PHY LED1 강제 모드의 정의는 [Linux6.12 Qualcomm PHY 헤더](https://github.com/torvalds/linux/blob/v6.12/drivers/net/phy/qcom/qcom.h)와 [드라이버](https://github.com/torvalds/linux/blob/v6.12/drivers/net/phy/qcom/qca807x.c)에 근거한다.

Wi-Fi는 실제 `phy80211` 인터페이스의 carrier와 송수신 카운터만 합산한다. 유선 `br-lan` 트래픽으로 Wi-Fi 표시등을 켜지 않는다.1초 조회 간격과75ms 커널 timer를 사용한다. 꺼진 무선을 켜거나 SSID·암호·출력 설정을 바꾸지 않는다.

## LED 소스 빌드

빌드용 Linux에서 ARM 하드플로트 정적 링크를 지원하는 GCC를 사용한다. 개발 환경에서는 `arm-linux-gnueabihf-gcc`로 빌드했다. 생성한 바이너리·압축 파일은 Git에 포함하지 않는다.

```sh
cd device-settings
sh build.sh
sha256sum ti04-led-settings.tgz
```

다른 크로스 컴파일러는 `CC`로 지정할 수 있지만, 대상 ARMv7/ABI와 정적 실행 가능 여부를 확인해야 한다. 생성한 자기 패키지를 공유기의 `/tmp`로 전송하고 같은 SHA256인지 대조한다. SSH/SCP 주소는 자기 장비를 사용한다. 비밀번호·SSH 키는 공유하거나 저장소에 넣지 않는다.

## LED 적용

아래 명령은 자기 패키지와 이 저장소의 `apply-leds.sh`를 장비에 전달한 뒤 **공유기 셸에서** 실행한다. 기존 LED 서비스/파일/설정 항목 또는 미완료 system 변경이 있으면 적용기가 중단한다. 자동으로 덮어쓰거나 삭제하지 않는다.

```sh
mkdir -p /tmp/ti04-led-package
tar -xzf /tmp/ti04-led-settings.tgz -C /tmp/ti04-led-package
sh /tmp/apply-leds.sh /tmp/ti04-led-package
cat /var/run/ti04-lan-led.status
cat /var/run/ti04-wifi-led.status
ubus call service list '{"name":"ti04-leds"}'
```

적용기는 기기 모델/board, LED sysfs, QCA8075, 기존 대상 파일을 검사하고 `/root/ti04-led-settings-backup/system`에 기존 system 설정을 저장한다. OpenWrt 기본 LED 서비스에는 WAN과 공용 Wi-Fi 항목을 추가하고, LAN·Wi-Fi 감시 서비스는 `S97ti04-leds`로 등록한다. 기존 NTP·무선 설정은 유지한다.

**소스의 최종 동작은 실기 검증됐으나, 이번에 공개용으로 묶은 빌드·적용 스크립트를 다른 순정 장비에서 처음부터 재현한 시험은 아직 없다.** 자동 시작 등록은 확인했지만 LED 변경 후 물리 전원 재인가까지 검증했다고 해석하지 않는다. 개발 중 사용한 `--restore-led0`는 실패했던 LED0 시험을 원복하기 위한 유지보수 옵션이며 정상 설치 명령에 포함하지 않는다.

## LED 제거·복원

```sh
/etc/init.d/ti04-leds stop
/etc/init.d/ti04-leds disable
uci delete system.led_ti04_wan
uci delete system.led_ti04_wlan
uci commit system
/etc/init.d/led restart
rm -f /usr/sbin/ti04-phy-led /usr/sbin/ti04-wifi-led /etc/init.d/ti04-leds
```

위 제거는 이 설치에서 추가한 두 설정 항목과 세 파일만 대상으로 한다. 설치 전 system 설정 전체를 복원해야 한다면 보관본과 현재 변경을 비교한 뒤 선택한다. 보관본을 무조건 덮어쓰면 이후 NTP 등 다른 변경도 사라질 수 있다.

## 누락된 NTP 기본값 보완

개발 이미지의 system 구성에는 NTP 항목이 빠져 있었다. `apply-ntp.sh`는 timeserver 구성이 없을 때만 기본 클라이언트를 추가한다. 기존 서버 선택은 보존하며 system 설정이 저장 대기 중이면 중단한다.

```sh
sh /tmp/apply-ntp.sh
ubus call service list '{"name":"sysntpd"}'
date -u
```

OpenWrt 기본 pool 서버4개, 클라이언트 활성화, NTP 서버 제공 비활성화 구성이며 [공식 기본 구성 생성 코드](https://github.com/openwrt/openwrt/blob/v25.12.6/package/base-files/files/bin/config_generate)를 따른다. 장비에 인터넷이 연결된 뒤 시각을 실제로 대조한다. 정상화된 개발 실기와 로컬 빌드 원본에는 반영했지만 이전 개인용 UBI 파일을 다시 만들거나 NAND를 다시 기록하지 않았다.

설치 전 구성은 `/root/ti04-system-before-ntp`에 보관한다. 되돌릴 때는 추가한 `system.ntp`만 제거하고 `sysntpd`를 재시작하거나, 이후 변경과 비교해 보관본을 선택 복원한다.

자세한 통신 결과·실패 이력·시각적 확인 범위는 [후속 검증 기록](../docs/POST_INSTALL_SETTINGS_20261027.md)을 본다.
