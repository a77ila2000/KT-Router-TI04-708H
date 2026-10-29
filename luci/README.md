# 관리자용 무선 출력 프로필

> 2026-10-29 [공개 r1 이미지](../docs/PUBLIC_RELEASE_R1.md)에는 출력 프로필과 대역 이름 표시를 포함했습니다. 아래 별도 적용 절차는 이전 이미지 사용자를 위한 것입니다. 새 공개 이미지의 실기 부팅은 아직 확인 전입니다.

OpenWrt25.12 LuCI의 **네트워크 → 최대 송신 출력** 메뉴를 추가한다. 네트워크 → 무선에서 사용하는 기존 `wireless.<radio>.txpower` 설정과 연동하며, 무선 드라이버·국가·채널·활성화 설정은 바꾸지 않는다.

| 선택 | 동작 |
|---|---|
| 최대 출력(자동) | 수동 `txpower` 상한을 제거하고 드라이버가 현재 국가·채널·장치 조건에 맞게 결정하도록 함 |
| 수동 상한 | 장치의 `iwinfo.txpowerlist`에서 받은 값으로 최대 출력을 제한 |

자동은 예전 high-power 펌웨어의35dBm 고정 요청 패치와 다르다. 실제 출력은 장치·국가·채널·동작 조건에 따라 낮아질 수 있다. 두 라디오가 원래 자동 상태면 자동을 선택해도 추가로 출력이 올라가는 것은 아니다. 이 페이지는 꺼진 라디오를 켜지 않는다.

한글 기본 UI에서는 한글, English를 선택한 UI에서는 영문으로 표시한다. 메뉴 제목은 LuCI 기본 번역의 `Maximum transmit power`를 사용한다. 국가/무선 상태는 읽기 전용으로 표시하고 출력값만 편집한다. 새 RPC 권한이나 실행 스크립트를 추가하지 않으며 기존 `luci-mod-network-config` 권한을 사용한다.

## 설치

이 디렉터리는 **소스 파일**이며 APK나 펌웨어 이미지가 아니다. TI04 실기25.12.6에는 아래 두 파일을 overlay에 설치했다. 기본 NAND UBI에 포함됐다고 해석하지 않는다.

```text
root/www/luci-static/resources/view/network/ti04-power.js
root/usr/share/luci/menu.d/luci-app-ti04-power.json
```

기존 LuCI25.12와 정상 관리 연결이 있는 장비에 같은 파일을 설치하려면 저장소 루트에서 묶은 뒤 자기 공유기 주소로 전송한다. 예시는 PC에 tar/SSH가 있는 경우이며 root 암호를 직접 입력한다.

```sh
tar -czf ti04-radio-power-ui.tgz -C luci/root www/luci-static/resources/view/network/ti04-power.js usr/share/luci/menu.d/luci-app-ti04-power.json
scp -O ti04-radio-power-ui.tgz root@192.168.1.1:/tmp/
ssh root@192.168.1.1
```

공유기 셸에서 기존 같은 이름의 파일이 없는지 먼저 확인하고 압축을 푼다. 기존 파일이 있으면 그대로 덮어쓰지 말고 버전을 비교한다.

```sh
test ! -e /www/luci-static/resources/view/network/ti04-power.js &&
test ! -e /usr/share/luci/menu.d/luci-app-ti04-power.json &&
tar -xzf /tmp/ti04-radio-power-ui.tgz -C /
rm -f /tmp/luci-indexcache.*.json
/etc/init.d/uhttpd reload
```

관리자 화면을 새로고침하거나 [직접 경로](http://192.168.1.1/cgi-bin/luci/admin/network/ti04-power)를 연다. 각 대역에서 출력 프로필을 선택해 LuCI의 저장/적용을 사용한다. 무선 연결로 관리 중이면 출력 변경·무선 재적용으로 연결이 끊길 수 있으므로 유선 관리 연결에서 적용한다.

## 제거

추가한 두 파일만 제거하고 메뉴 캐시를 갱신한다. 이미 저장한 출력값은 기존 무선 설정에 남으므로 필요하면 제거 전에 최대 출력(자동)을 선택한다.

```sh
rm -f /www/luci-static/resources/view/network/ti04-power.js /usr/share/luci/menu.d/luci-app-ti04-power.json
rm -f /tmp/luci-indexcache.*.json
/etc/init.d/uhttpd reload
```

## 확인 범위

- 실제 TI04-708H/OpenWrt25.12.6: dispatcher 메뉴 `satisfied=true`, view JS HTTP200 및 원본SHA 일치, 인증 요구 경로 확인.
- Node 검사: 자동/수동 필드 매핑, 반환된 출력값만 제공, 기존 수동값 보존, 한국어/영어, 메뉴 ACL 및 radio 설정 분리.
- 실제 장비의 별도 `/tmp` UCI 시험 설정: 수동10 저장 → 자동으로 제거, disabled 유지 통과. 실제 wireless 파일은 SHA 불변이다.
- 브라우저 제어 비활성으로 실제 화면 렌더링·클릭 저장은 미확인이다. 이번 추가 과정에서 라디오 활성화·출력 변경·드라이버 교체·재부팅은 하지 않았다.

로컬 검사는 저장소 루트에서 실행한다.

```sh
node tests/test_radio_power.cjs
```

## 무선 목록의 대역 표시

`patches/render_radio_badge.js`는 무선 목록에서 대역을 굵게 표시하고 내부 식별자는 작은 글씨로 함께 표시한다. 예: **2.4GHz Wi-Fi** / `radio0`, **5GHz Wi-Fi** / `radio1`. 번호를 고정해 해석하지 않고 각 장치의 `band` 설정을 읽으며 없으면 실행 상태의 band를 확인한다. 꺼진 라디오에서도 표시되며 알 수 없는 대역은 기존 식별자를 유지한다.

`patches/patch_wireless_labels.py ORIGINAL.js OUTPUT.js`는 검사한 LuCI25.12 무선 화면에서 해당 표시 함수만 바꾼다. 최종 적용은 **별도 리소스 `network/ti04-wireless-bands`**를 사용한다. `route_wireless_bands.py`는 기존 무선 메뉴의 action 경로만 바꾸고 제목·권한·의존 조건과 다른 메뉴를 보존한다.

최초 같은 파일 경로를 수정했을 때는 서버 SHA 일치와 강제 새로고침만으로 실제 화면이 갱신되지 않았다. 실제 band 설정은 정상이었다. 별도 화면 경로와 실행 상태 fallback 적용 후 **사용자가2.4GHz/5GHz 표시를 확인**했다. 최초 현상의 정확한 캐시/로딩 원인을 확정하지는 않았다. 최종 원본 `wireless.js`는 복원했고 네트워크·무선 설정 파일은 SHA 불변이다. 기본 UBI 이미지에는 아직 포함하지 않았다.

### 대역 표시 적용

PC에서 자기 공유기의 원본 두 파일을 받아 보관하고 새 파일을 생성한다. `YOUR_ROUTER`는 자기 공유기 주소로 바꾼다. SSH 암호는 직접 입력하며 저장하지 않는다.

```sh
ROUTER=root@YOUR_ROUTER
scp -O "$ROUTER:/www/luci-static/resources/view/network/wireless.js" wireless.original.js
scp -O "$ROUTER:/usr/share/luci/menu.d/luci-mod-network.json" luci-mod-network.original.json
python3 luci/patches/patch_wireless_labels.py wireless.original.js ti04-wireless-bands.js
python3 luci/patches/route_wireless_bands.py luci-mod-network.original.json luci-mod-network.bands.json
scp -O ti04-wireless-bands.js luci-mod-network.bands.json "$ROUTER:/tmp/"
```

공유기 셸에서 대상 모델·새 파일을 확인하고 메뉴를 백업한 뒤 적용한다. 같은 확장을 이미 설치했으면 기존 파일/백업을 지우지 말고 버전을 비교한다.

```sh
set -e
[ "$(cat /tmp/sysinfo/board_name)" = 'giga,kt-9200' ]
[ "$(cat /tmp/sysinfo/model)" = 'TI04-708H' ]
view=/www/luci-static/resources/view/network/ti04-wireless-bands.js
menu=/usr/share/luci/menu.d/luci-mod-network.json
backup=/root/ti04-wireless-bands-backup
[ ! -e "$view" ] && [ ! -e "$backup" ]
mkdir -m 700 "$backup"
cp -p "$menu" "$backup/luci-mod-network.json"
cp /tmp/ti04-wireless-bands.js "$view"
chmod 644 "$view"
cp /tmp/luci-mod-network.bands.json "$menu"
chmod 644 "$menu"
for cache in /tmp/luci-indexcache.*.json; do [ ! -f "$cache" ] || rm -f "$cache"; done
sync
```

무선 페이지를 새로고침해 실제 표시를 확인한다. 원래 무선 설정·SSID·암호·라디오 활성화 상태를 저장/변경할 필요가 없다. 원복은 보관했던 메뉴를 복사하고 추가한 view만 제거한 뒤 같은 메뉴 캐시를 갱신한다. 기존 `wireless.js`를 덮어쓰지 않는다.

```sh
cp -p /root/ti04-wireless-bands-backup/luci-mod-network.json /usr/share/luci/menu.d/luci-mod-network.json
rm -f /www/luci-static/resources/view/network/ti04-wireless-bands.js
for cache in /tmp/luci-indexcache.*.json; do [ ! -f "$cache" ] || rm -f "$cache"; done
```

```sh
node tests/test_wireless_band_labels.cjs
python3 -m unittest discover -s tests -p 'test_wireless_label_patch.py'
```
