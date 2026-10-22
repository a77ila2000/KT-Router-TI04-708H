import hashlib
import sys
import os

def hash_file(path):
    sha = hashlib.sha256()
    with open(path, 'rb') as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()

def main():
    if len(sys.argv) < 3:
        print("사용법: python verify_dump.py <dump1.bin> <dump2.bin>")
        return

    f1, f2 = sys.argv[1], sys.argv[2]
    if not os.path.exists(f1) or not os.path.exists(f2):
        print("파일을 찾을 수 없습니다.")
        return

    size1 = os.path.getsize(f1)
    size2 = os.path.getsize(f2)
    h1 = hash_file(f1)
    h2 = hash_file(f2)

    print(f"파일 1 ({f1}): {size1:,} bytes | SHA256: {h1}")
    print(f"파일 2 ({f2}): {size2:,} bytes | SHA256: {h2}")

    if h1 == h2 and size1 == size2:
        print("\n[OK] 두 덤프 파일이 100% 완벽하게 일치합니다! (안전한 덤프)")
    else:
        print("\n[경고] 두 덤프 파일이 일치하지 않습니다! 집게 접촉 불량 여부를 확인하고 다시 덤프하십시오.")

if __name__ == "__main__":
    main()
