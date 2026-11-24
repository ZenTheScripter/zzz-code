from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = ROOT / "ZzZCode.spec"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="build ZzZ Code")
    parser.add_argument("--clean", action="store_true", help="wipe build/ and dist/")
    parser.add_argument("--onedir", action="store_true", help="folder build")
    args = parser.parse_args(argv)

    if not SPEC.is_file():
        print("spec missing: %s" % SPEC, file=sys.stderr)
        return 2

    try:
        import PyInstaller
    except ImportError:
        print("pyinstaller is not installed - run: python -m pip install pyinstaller",
              file=sys.stderr)
        return 2

    if args.clean:
        for name in ("build", "dist"):
            shutil.rmtree(ROOT / name, ignore_errors=True)

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        str(SPEC),
    ]
    if args.onedir:
        print("note: ZzZCode.spec produces a single file, so --onedir has no effect")
    print(" ".join(cmd))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode == 0:
        print("built: %s" % (ROOT / "dist" / "ZzZCode.exe"))
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
