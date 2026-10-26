# 관리자용 무선 출력 프로필

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
