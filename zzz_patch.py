#!/usr/bin/env python3
"""
ZzZ Code -- opencode.exe rebrand engine.

bun standalone executables carry an index of module byte-offsets in their
trailer. Any byte inserted or removed invalidates every offset after the edit,
so the process is length-preserving: each rewritten blob is padded back to its
exact original byte length. Padding is ASCII space inserted immediately after
the `var X=` token -- legal JS whitespace that never reaches the rendered art.

Two bundle layouts are supported, probed in order:

  v1  `var _={left:[...],right:[...]}`   splash wordmark      (ZZZ + code)
      `var O=[...]`                      CLI brailled banner  (ZZZCODE)

  v2  `var cw={left:[...],right:[...]}`  splash wordmark      (ZZZ + code)
      -- the brailled banner was dropped upstream in the 2.x line

The v2 art is emitted as literal UTF-8 block characters rather than `\\uXXXX`
escapes: the v2 span is 590 bytes, and escaping every glyph would overflow it.

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

V1_LOGO_LOCATOR = b"var _={left:["
V1_LOGO_TERM = b"]},t={left:["
V1_LOGO_TAIL = ",t={left:["
V1_BANNER_LOCATOR = b'var O=["\\u2800'
V1_BANNER_TERM = b"];class _"
V1_BANNER_TAIL = ";class _"

V2_LOGO_LOCATOR = b"var cw={left:["
V2_LOGO_TERM = b"]},Z$={left:["
V2_LOGO_TAIL = ",Z$={left:["


class PatchError(RuntimeError):
    """Target binary does not match the expected bundle layout."""


@dataclass(frozen=True)
class PatchReport:
    source: Path
    output: Path
    size: int
    sha256: str
    profile: str
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

# v2 lays the splash out as two 19-column blocks side by side, so the left one
# has to be padded to the same width or the right block shifts under it.
V2_LEFT = [LEFT_ART[0]] + [row.ljust(19) for row in LEFT_ART[1:]]
V2_RIGHT = RIGHT_ART


def _esc(text: str) -> str:
    """Escape non-ASCII as \\uXXXX, matching the v1 bundle's encoding."""
    return "".join(c if ord(c) < 0x80 else "\\u%04x" % ord(c) for c in text)


def _lit(text: str) -> str:
    """Escape only what a JS string literal cannot carry; keep glyphs as UTF-8."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _jarray(rows: list[str], escape: bool = True) -> str:
    enc = _esc if escape else _lit
    return "[" + ",".join('"%s"' % enc(r) for r in rows) + "]"


def logo_blob(escape: bool = True, left: list[str] | None = None,
              right: list[str] | None = None) -> str:
    left = LEFT_ART if left is None else left
    right = RIGHT_ART if right is None else right
    return "var _={left:%s,right:%s}" % (_jarray(left, escape), _jarray(right, escape))


def v2_logo_blob() -> str:
    return "var cw={left:%s,right:%s}" % (
        _jarray(V2_LEFT, escape=False),
        _jarray(V2_RIGHT, escape=False),
    )


def banner_blob() -> str:
    return "var O=%s" % _jarray(BANNER_ART)


# ------------------------------------------------------------ patching -----

def _count(data: bytes, needle: bytes) -> int:
    return data.count(needle)


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
    # Padding goes between the `var X=` token and the object: plain whitespace,
    # invisible to the renderer, keeps every following module offset intact.
    pad = original_len - len(anchor.encode("ascii")) - len(body.encode("utf-8")) \
        - len(tail.encode("utf-8"))
    if pad < 0:
        raise PatchError(
            "%s overflows the target span by %d bytes" % (anchor, -pad)
        )
    replacement = (anchor + " " * pad).encode("ascii") + body.encode("utf-8") \
        + tail.encode("utf-8")
    if len(replacement) != original_len:
        raise PatchError("span arithmetic drifted for %s" % anchor)
    data[start:end] = replacement
    return original_len, pad


def is_patched(path: Path) -> bool:
    """True when the wordmark already reads ZZZ (idempotent re-run guard)."""
    markers = [
        (_esc(Z[0]) + " " + _esc(Z[0])).encode("ascii"),
        (Z[0] + " " + Z[0]).encode("utf-8"),
    ]
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
            window = carry + block
            for marker in markers:
                if marker in window:
                    return True
            carry = window[-64:]
    return False


def _apply(data: bytearray) -> tuple[str, int, int, int, int]:
    """Rewrite the wordmark blobs inside `data`, length-preserving.

    The profile is picked by probing the bundle, not by version string: a build
    either carries the v1 pair of blobs or the v2 splash, and the locator count
    says which before anything is written.
    """
    v1_logo = _count(bytes(data), V1_LOGO_LOCATOR) == 1
    v2_logo = _count(bytes(data), V2_LOGO_LOCATOR) == 1

    if v1_logo:
        logo_len, logo_pad = _rewrite(
            data, V1_LOGO_LOCATOR, "var _=", V1_LOGO_TERM, V1_LOGO_TAIL,
            logo_blob(),
        )
        banner_len = banner_pad = 0
        if _count(bytes(data), V1_BANNER_LOCATOR) == 1:
            banner_len, banner_pad = _rewrite(
                data, V1_BANNER_LOCATOR, "var O=", V1_BANNER_TERM,
                V1_BANNER_TAIL, banner_blob(),
            )
        return "v1", logo_len, logo_pad, banner_len, banner_pad

    if v2_logo:
        logo_len, logo_pad = _rewrite(
            data, V2_LOGO_LOCATOR, "var cw=", V2_LOGO_TERM, V2_LOGO_TAIL,
            v2_logo_blob(),
        )
        return "v2", logo_len, logo_pad, 0, 0

    raise PatchError(
        "unknown bundle layout: neither %r nor %r found exactly once"
        % (V1_LOGO_LOCATOR, V2_LOGO_LOCATOR)
    )


def patch_binary(source: Path, output: Path) -> PatchReport:
    """Copy `source` to `output` and rewrite the wordmark blobs in place."""
    source = Path(source)
    output = Path(output)
    if not source.is_file():
        raise PatchError("source binary missing: %s" % source)

    if source.resolve() != output.resolve():
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, output)

    data = bytearray(output.read_bytes())
    size = len(data)
    profile, logo_len, logo_pad, banner_len, banner_pad = _apply(data)

    if len(data) != size:
        raise PatchError("output size drifted: %d != %d" % (len(data), size))

    payload = bytes(data)
    output.write_bytes(payload)

    return PatchReport(
        source=source,
        output=output,
        size=size,
        sha256=hashlib.sha256(payload).hexdigest(),
        profile=profile,
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
    profile, logo_len, logo_pad, banner_len, banner_pad = _apply(data)

    if len(data) != size:
        raise PatchError("output size drifted: %d != %d" % (len(data), size))

    payload = bytes(data)
    path.write_bytes(payload)

    return PatchReport(
        source=path,
        output=path,
        size=size,
        sha256=hashlib.sha256(payload).hexdigest(),
        profile=profile,
        logo_bytes=logo_len,
        banner_bytes=banner_len,
        logo_pad=logo_pad,
        banner_pad=banner_pad,
    )
