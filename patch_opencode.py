#!/usr/bin/env python3
"""
patch_opencode.py -- stage the patched runtime under %LOCALAPPDATA%\\ZzZCode.

Thin CLI over `zzz_patch`. Run from anywhere; it never touches the original
binary: it copies opencode.exe into the staging folder, patches that copy, and
renames it to zzzcode.exe.

    python patch_opencode.py                 # opencode.exe -> the staged zzzcode.exe
    python patch_opencode.py --check         # report only, no write
    python patch_opencode.py --src X --out Y
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from zzz_patch import PatchError, is_patched, patch_binary

HERE = Path(__file__).resolve().parent
LOCAL_ROOT = Path(
    os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
) / "ZzZCode"
DEFAULT_SRC = Path.home() / ".opencode" / "bin" / "opencode.exe"
DEFAULT_OUT = LOCAL_ROOT / "bin" / "zzzcode.exe"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="rebuild zzzcode.exe")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--check", action="store_true", help="report state, write nothing")
    args = ap.parse_args(argv)

    print("source : %s" % args.src)
    print("output : %s" % args.out)

    if not args.src.is_file():
        print("ERROR: source binary missing", file=sys.stderr)
        return 1

    if args.check:
        state = "patched" if args.out.is_file() and is_patched(args.out) else "unpatched or absent"
        print("state  : %s" % state)
        return 0

    try:
        report = patch_binary(args.src, args.out)
    except PatchError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 1

    print("  layout %s" % report.profile)
    print("  logo   blob %d bytes (pad %d)" % (report.logo_bytes, report.logo_pad))
    if report.banner_bytes:
        print("  banner blob %d bytes (pad %d)" % (report.banner_bytes, report.banner_pad))
    else:
        print("  banner not present in this build")
    print("  size   %d bytes (unchanged)" % report.size)
    print("  sha256 %s" % report.sha256)
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
