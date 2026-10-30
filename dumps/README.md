# KT GiGA WiFi Wave 2 (TI04-708H) 순정 롬/펌웨어 덤프 안내

KT GiGA WiFi Wave 2 유무선 공유기(제조사: 올래디오, 모델명: **TI04-708H / WGHE010100**, Qualcomm IPQ4019 SoC)의 순정 펌웨어 분석, 역공학 및 OpenWrt 포팅을 위한 원본 플래시 덤프 자산입니다.

전체 대용량 덤프 파일은 **[GitHub Releases: stock-dump-v1.4.0](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/stock-dump-v1.4.0)** 에서 직접 다운로드할 수 있습니다.

---

## 📦 제공 파일 목록 및 체크섬

| 파일명 | 크기 | 포맷 / 설명 | SHA-256 |
|---|---|---|---|
| **`ti04-708h-nor-bootloader.bin`** | 2,097,152 bytes (2.0 MB) | SPI NOR 원본 덤프 (U-Boot, SBL, QSEE, 부트 파티션) | `c33402801b9c4484b20634303675fe7422b0dcde1e6e1d95c4fac790bea9d23e` |
| **`ti04-708h-nand-full-dump.bin.xz`** | 53,013,104 bytes (50.6 MB) | SPI NAND 128MB Main 영역 전체 덤프 (OOB 제외, XZ 압축) | `59c775c4ef0a9ba4424bde96631065731229c1c0e71b7c6379c1c020553c90d2` |
| **`ti04-708h-stock-rootfs.ubifs`** | 23,236,608 bytes (22.2 MB) | UBI 볼륨(`ubi_rootfs`)에서 추출한 순정 SquashFS 루트 파일시스템 | `78f28453ac89e1a1972107295d809be817c9e3e64ebf4967c81ff7f1e9827f28` |
| **`ti04-708h-stock-kernel.ubifs`** | 2,920,448 bytes (2.8 MB) | UBI 볼륨(`kernel`)에서 추출한 순정 FIT 커널 이미지 | `33b8db814605bc48e091f37ef5b9343911361b943bdd1c3fc5ed2d2c2f6796bd` |
| **`SHA256SUMS.txt`** | 387 bytes | 무결성 검증용 SHA-256 해시 목록 | - |

> ⬇️ **다운로드 바로가기**: **[Releases / stock-dump-v1.4.0](https://github.com/a77ila2000/KT-Router-TI04-708H/releases/tag/stock-dump-v1.4.0)**

---

## 🔍 파일별 상세 설명

### 1. SPI NOR 부트로더 (`ti04-708h-nor-bootloader.bin`)
- **실물 칩**: **GigaDevice GD25Q16CSIG** (2 MiB SOP-8 SPI NOR Flash, JEDEC ID: `C8 40 15`, 보드 실물 U33)
- **주요 내용**:
  - Qualcomm Primary Bootloader (SBL)
  - TrustZone / QSEE (`tz.mbn`)
  - 순정 U-Boot 부트로더 바이너리 및 기본 환경 변수
- **용도**:
  - 부트로더 분석, UART 콘솔 부트 딜레이 패치(`bootdelay=2012`), 브릭 시 하드웨어 롬라이터(CH341A 등) 복구용.

### 2. SPI NAND 전체 Main 덤프 (`ti04-708h-nand-full-dump.bin.xz`)
- **실물 칩**: **Macronix MX35LFxGE4AB 계열** (128 MiB SPI NAND Flash, 블록 128 KiB, 페이지 2048 bytes)
- **특징**:
  - **OOB(Out-of-Band / Spare 영역 64 bytes/page)는 미포함**되어 있습니다.
  - 하드웨어 ECC 컨트롤러를 거쳐 읽어낸 순수 128 MiB (정확히 `134,217,728 bytes`)의 논리 Main 영역 전체 덤프입니다.
- **압축 해제**:
  ```bash
  unxz -d ti04-708h-nand-full-dump.bin.xz
  # -> ti04-708h-nand-full-dump.bin (134,217,728 bytes)
  ```
- **용도**:
  - 플래시 파티션 레이아웃 분석, UBI 볼륨 언팩 및 순정 펌웨어 복구용.

### 3. 순정 SquashFS 루트 파일시스템 (`ti04-708h-stock-rootfs.ubifs`)
- **형식**: SquashFS little endian (UBI `ubi_rootfs` 볼륨)
- **언팩/추출 방법** (Linux / WSL 환경):
  ```bash
  # unsquashfs 도구로 즉시 디렉토리에 풀기
  sudo apt-get install -y squashfs-tools
  unsquashfs -d stock-rootfs ti04-708h-stock-rootfs.ubifs
  ```
- **포함된 주요 분석 자산**:
  - 웹서버 설정 및 소스: `/etc/lighttpd.conf`, `/www/` (PHP CGI 파일들)
  - KT 공유기 전용 관리 데몬: `/bin/rc`, `/bin/board`, `/bin/kt_mon` 등
  - 포트 8801 / 8899 관리자 페이지 소스 및 인증 로직 (`ktadmin`, `GIGALAND1409` salt)

### 4. 순정 FIT 커널 (`ti04-708h-stock-kernel.ubifs`)
- **형식**: Flattened Image Tree (FIT) uImage
- **포함 내용**: Linux 커널 바이너리(zImage) 및 디바이스 트리(DTB)
- **분석 도구**:
  ```bash
  dumpimage -l ti04-708h-stock-kernel.ubifs
  dumpimage -T flat_dt -p 0 -i ti04-708h-stock-kernel.ubifs kernel.bin
  ```

---

## 🛠️ 분석 가이드 및 관련 문서

- **[순정 8801 관리자 역공학 노트](../docs/STOCK_FIRMWARE_ADMIN_ANALYSIS_UNVERIFIED.md)**:
  - 8801 포트 방화벽 해제 및 `lighttpd` 라우팅 구조
  - `ktadmin` 인증 알고리즘 (MAC + salt MD5 해시 생성 원리)
  - 히든 관리자 메뉴 (펌웨어 수동 업그레이드, 브릿지 모드 등 35개 이상 화면)
- **[설치 제약 분석 보고서](../OPENWRT_INSTALLATION_ANALYSIS_REPORT.md)**:
  - 제조사 부트로더, FIT 이미지 서명 검증 및 파티션 구조 상세

---

## ⚠️ 면책 및 라이선스 안내 (Disclaimer)

1. 본 덤프 파일은 보안 취약점 연구, 비공식 오픈소스 펌웨어(OpenWrt) 포팅 및 기기 수리/복구 목적으로만 공유됩니다.
2. 덤프 원본에는 덤프 추출 기기의 고유 식별 정보(MAC 주소, 기본 Wi-Fi SSID 등)가 포함되어 있을 수 있습니다. 타 기기에 그대로 플래싱할 경우 MAC 주소 충돌이 발생할 수 있으므로 주의하시기 바랍니다.
3. 펌웨어 플래싱 및 기기 조작에 따른 모든 책임은 사용자 본인에게 있습니다.
