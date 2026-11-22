#!/usr/bin/env python3
"""
ZzZ Code -- opencode.exe rebrand engine.

bun standalone executables carry an index of module byte-offsets in their
trailer. Any byte inserted or removed invalidates every offset after the edit,
so the process is length-preserving: each rewritten blob is padded back to its
exact original byte length. Padding is ASCII space inserted immediately after
the `var X=` token -- legal JS whitespace that never reaches the rendered art.

Two blobs are rewritten:

  1. `var _={left:[...],right:[...]}`  -> splash / TUI wordmark  (ZZZ + code)
  2. `var O=[...]`                     -> CLI banner            (ZZZCODE)

Public API:
    patch_binary(src, dst) -> PatchReport
    patch_in_place(path)   -> PatchReport
    is_patched(path) -> bool
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

FULL = "\u2588"
UPPER = "\u2580"
LOWER = "\u2584"

LOGO_LOCATOR = b"var _={left:["
LOGO_ANCHOR = "var _="
LOGO_TERM = b"]},t={left:["
LOGO_TAIL = ",t={left:["

BANNER_LOCATOR = b'var O=["\\u2800'
BANNER_ANCHOR = "var O="
BANNER_TERM = b"];class _"
BANNER_TAIL = ";class _"


class PatchError(RuntimeError):
    """Target binary does not match the expected bundle layout."""


@dataclass(frozen=True)
class PatchReport:
    source: Path
    output: Path
    size: int
    sha256: str
    logo_bytes: int
    banner_bytes: int
    logo_pad: int
    banner_pad: int


# ---------------------------------------------------------------- art ------

# 4-wide, 3-row glyph in the same family as the shipped block font. Expanded to
# half-cell pixels it reads:
#     ####
#     ...#
#     ..#.
#     .#..
#     ####
Z = [UPPER * 3 + FULL, " " + LOWER + UPPER + " ", UPPER * 4]

C = [FULL + UPPER * 3, FULL + "_" * 3, UPPER * 4]
O = [FULL + UPPER * 2 + FULL, FULL + "_" * 2 + FULL, UPPER * 4]
D = [FULL + UPPER * 2 + FULL, FULL + "_" * 2 + FULL, UPPER * 4]
E = [FULL + UPPER * 2 + FULL, FULL + "^^^", UPPER * 4]

LEFT_ART = [
    " " * 19,
    " ".join([Z[0]] * 3),
    " ".join([Z[1]] * 3),
    " ".join([Z[2]] * 3),
]

RIGHT_ART = [
    " " * 13 + LOWER + " " * 5,
    " ".join([C[0], O[0], D[0], E[0]]),
    " ".join([C[1], O[1], D[1], E[1]]),
    " ".join([C[2], O[2], D[2], E[2]]),
]

BANNER_ART = [
    "\u2800" + " " * 32 + LOWER + " " * 5,
    " ".join([Z[0]] * 3 + [C[0], O[0], D[0], E[0]]),
    " ".join([Z[1]] * 3 + [C[1], O[1], D[1], E[1]]),
    " ".join([Z[2]] * 3 + [C[2], O[2], D[2], E[2]]),
]


def _esc(text: str) -> str:
    """Escape non-ASCII as \\uXXXX, matching the shipped bundle's encoding."""
    return "".join(c if ord(c) < 0x80 else "\\u%04x" % ord(c) for c in text)


def _jarray(rows: list[str]) -> str:
    return "[" + ",".join('"%s"' % _esc(r) for r in rows) + "]"


def logo_blob() -> str:
    return "var _={left:%s,right:%s}" % (_jarray(LEFT_ART), _jarray(RIGHT_ART))


def banner_blob() -> str:
    return "var O=%s" % _jarray(BANNER_ART)


# ------------------------------------------------------------ patching -----

def _find_span(data: bytes, locator: bytes, terminator: bytes) -> tuple[int, int]:
    first = data.find(locator)
    if first < 0:
        raise PatchError("locator %r not found" % locator[:24])
    if data.find(locator, first + 1) >= 0:
        raise PatchError("locator %r is not unique" % locator[:24])
    end = data.find(terminator, first + len(locator))
    if end < 0:
        raise PatchError("terminator %r not found" % terminator[:24])
    return first, end + len(terminator)


def _rewrite(
    data: bytearray,
    locator: bytes,
    anchor: str,
    terminator: bytes,
    tail: str,
    blob: str,
) -> tuple[int, int]:
    start, end = _find_span(bytes(data), locator, terminator)
    original_len = end - start
    body = blob[len(anchor):]
    pad = original_len - len(anchor) - len(body.encode("ascii")) - len(tail)
    if pad < 0:
        raise PatchError("%s overflows the target span by %d bytes" % (anchor, -pad))
    replacement = (anchor + " " * pad + body + tail).encode("ascii")
    if len(replacement) != original_len:
        raise PatchError("span arithmetic drifted for %s" % anchor)
    data[start:end] = replacement
    return original_len, pad


def is_patched(path: Path) -> bool:
    """True when the wordmark already reads ZZZ (idempotent re-run guard)."""
    marker = (_esc(Z[0]) + " " + _esc(Z[0])).encode("ascii")
    try:
        handle = Path(path).open("rb")
    except OSError:
        return False
    with handle:
        carry = b""
        while True:
            block = handle.read(4 * 1024 * 1024)
            if not block:
                return False
            if marker in carry + block:
                return True
            carry = (carry + block)[-len(marker):]


def _apply(data: bytearray) -> tuple[int, int, int, int]:
    """Rewrite both wordmark blobs inside `data`, length-preserving."""
    logo_len, logo_pad = _rewrite(
        data, LOGO_LOCATOR, LOGO_ANCHOR, LOGO_TERM, LOGO_TAIL, logo_blob()
    )
    banner_len, banner_pad = _rewrite(
        data, BANNER_LOCATOR, BANNER_ANCHOR, BANNER_TERM, BANNER_TAIL, banner_blob()
    )
    return logo_len, logo_pad, banner_len, banner_pad


def patch_binary(source: Path, output: Path) -> PatchReport:
    """Copy `source` to `output` and rewrite both wordmark blobs in place."""
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise PatchError("source binary missing: %s" % source)

    if source.resolve() != output.resolve():
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)

    data = bytearray(output.read_bytes())
    size = len(data)
    logo_len, logo_pad, banner_len, banner_pad = _apply(data)

    if len(data) != size:
        raise PatchError("output size drifted: %d != %d" % (len(data), size))

    payload = bytes(data)
    output.write_bytes(payload)

    return PatchReport(
        source=source,
        output=output,
        size=size,
        sha256=hashlib.sha256(payload).hexdigest(),
        logo_bytes=logo_len,
        banner_bytes=banner_len,
        logo_pad=logo_pad,
        banner_pad=banner_pad,
    )


def patch_in_place(path: Path) -> PatchReport:
    """Rewrite an already-placed copy of the runtime, without moving it again.

    The launcher stages `opencode.exe`, patches that staged file, and only then
    renames it to `zzzcode.exe` so a half-written binary never carries the name
    the launcher trusts.
    """
    path = Path(path)
    if not path.is_file():
        raise PatchError("target binary missing: %s" % path)

    data = bytearray(path.read_bytes())
    size = len(data)
    logo_len, logo_pad, banner_len, banner_pad = _apply(data)

    if len(data) != size:
        raise PatchError("output size drifted: %d != %d" % (len(data), size))

    payload = bytes(data)
    path.write_bytes(payload)

    return PatchReport(
        source=path,
        output=path,
        size=size,
        sha256=hashlib.sha256(payload).hexdigest(),
        logo_bytes=logo_len,
        banner_bytes=banner_len,
        logo_pad=logo_pad,
        banner_pad=banner_pad,
    )
