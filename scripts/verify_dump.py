"""Compare private dump files without accessing a programmer or modifying files."""

import argparse
import hashlib
import os
from pathlib import Path
import sys


def inspect_file(path):
    digest = hashlib.sha256()
    size = 0
    all_zero = all_ff = True
    with path.open("rb") as source:
        while True:
            chunk = source.read(65536)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
            all_zero = all_zero and chunk.count(0) == len(chunk)
            all_ff = all_ff and chunk.count(255) == len(chunk)
    return size, digest.hexdigest(), all_zero or all_ff


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-size", type=int, help="expected bytes per file")
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    if len(args.files) < 2:
        parser.error("at least two independently acquired files are required")
    if args.expected_size is not None and args.expected_size <= 0:
        parser.error("--expected-size must be positive")

    try:
        for index, path in enumerate(args.files):
            if any(os.path.samefile(path, previous) for previous in args.files[:index]):
                print("[FAIL] Supply distinct files, not the same file or aliases.")
                return 1
        results = [inspect_file(path) for path in args.files]
    except OSError as error:
        print(f"[FAIL] Cannot read input: {error}", file=sys.stderr)
        return 1

    failed = False
    for path, (size, digest, blank) in zip(args.files, results):
        print(f"{path}: {size:,} bytes | SHA256: {digest}")
        if size == 0 or blank:
            print("[FAIL] Empty or entirely 00/FF input is not a usable backup.")
            failed = True
        if args.expected_size is not None and size != args.expected_size:
            print(f"[FAIL] Expected {args.expected_size:,} bytes.")
            failed = True
    if any(result[:2] != results[0][:2] for result in results[1:]):
        print("[FAIL] File sizes or SHA-256 digests differ.")
        failed = True
    if failed:
        return 1
    if args.expected_size is None:
        print("[NOTE] Expected chip size was not checked; use --expected-size.")
    print("[OK] Repeatability checks passed; chip identity and content validity remain unverified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
