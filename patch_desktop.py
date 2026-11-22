#!/usr/bin/env python3
"""Rebrand the OpenCode desktop wordmark to ZZZCODE, in place.

Two separate inline SVGs live in the renderer bundle
(`out/renderer/assets/main-*.js` inside `app.asar`):

  * `P3t` - viewBox `0 0 234 42`, the hero wordmark. 6-unit cells, 4x5 pixel
    glyphs on a 30-unit pitch. Each glyph is two paths: a `--icon-weak-base`
    inner block plus a `--icon-base` / `--icon-strong-base` outline.
  * `HBn` - viewBox `0 0 720 129`, the first-launch draw-on animation.
    18.46 x 18.43 unit cells.

`app.asar` addresses members by byte offset, so both replacements must be
byte-length identical to the art they replace. The ZZZCODE art is smaller than
the shipped art, so the difference is padded with spaces inside the enclosing
`<g>` - legal SVG text that never renders.

    python patch_desktop.py --check
    python patch_desktop.py             # patch in place, writes a .bak first
    python patch_desktop.py --restore

The launcher never leaves the vendor bundle patched: it applies the art for the
duration of a ZzZ desktop session and restores the pristine `.bak` when the app
exits, so launching OpenCode Desktop any other way stays vanilla. The module is
importable for that lifecycle:

    from patch_desktop import asar_state, patch_asar, restore_asar
"""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path

ASAR = (
    Path.home()
    / "AppData"
    / "Local"
    / "Programs"
    / "ai.opencode.desktop"
    / "resources"
    / "app.asar"
)
BACKUP = ASAR.with_suffix(".asar.zzz.bak")

MARKER_HERO = b"P3t=z(`"
MARKER_SPLASH = b"HBn=z(`"
MARKER_PINS = b"li=["
TERM_PINS = b"],J=78"
VIEWBOX_HERO = b'viewBox="0 0 234 42"'
VIEWBOX_SPLASH = b'viewBox="0 0 720 129"'
PATH_OPEN = b"<path"
PATH_CLOSE = b"</path>"


# ---------------------------------------------------------------- pixel font

# 4x5 bitmaps. The hero art and the splash art share the shapes, only the cell
# size and pitch differ.
GLYPHS = {
    "Z": ["####", "...#", "..#.", ".#..", "####"],
    "C": ["####", "#...", "#...", "#...", "####"],
    "O": ["####", "#..#", "#..#", "#..#", "####"],
    "D": ["####", "#..#", "#..#", "#..#", "####"],  # + right ascender
    "E": ["####", "#..#", "####", "#...", "####"],
}
# letter -> (row_from, row_to, col); row -1 sits one cell above the cap row.
ASCENDER = {"D": (-1, -1, 3)}

WORD = "ZZZCODE"


def _edges(bitmap, ascender=None):
    """Directed cell-boundary edges, clockwise around every filled cell."""
    filled = set()
    for r, row in enumerate(bitmap):
        for c, ch in enumerate(row):
            if ch == "#":
                filled.add((r, c))
    if ascender:
        row_from, row_to, col = ascender
        for r in range(row_from, row_to + 1):
            filled.add((r, col))

    out = []
    for (r, c) in sorted(filled):
        if (r - 1, c) not in filled:
            out.append(((c, r), (c + 1, r)))
        if (r, c + 1) not in filled:
            out.append(((c + 1, r), (c + 1, r + 1)))
        if (r + 1, c) not in filled:
            out.append(((c + 1, r + 1), (c, r + 1)))
        if (r, c - 1) not in filled:
            out.append(((c, r + 1), (c, r)))
    return out


def _loops(edges):
    """Chain directed edges into closed loops, preferring the tightest right turn."""
    by_start = {}
    for a, b in edges:
        by_start.setdefault(a, []).append(b)

    def turn_rank(prev, cur, nxt):
        din = (cur[0] - prev[0], cur[1] - prev[1])
        dout = (nxt[0] - cur[0], nxt[1] - cur[1])
        cross = din[0] * dout[1] - din[1] * dout[0]
        dot = din[0] * dout[0] + din[1] * dout[1]
        if cross < 0:
            return 0      # right turn keeps the filled region on the right
        if cross == 0 and dot > 0:
            return 1      # straight
        return 2          # left turn

    loops = []
    remaining = {k: list(v) for k, v in by_start.items()}
    for start, targets in by_start.items():
        for target in list(targets):
            if target not in remaining.get(start, []):
                continue
            remaining[start].remove(target)
            loop = [start, target]
            prev, cur = start, target
            while cur != start:
                options = remaining.get(cur, [])
                if not options:
                    break
                nxt = min(options, key=lambda o: turn_rank(prev, cur, o))
                remaining[cur].remove(nxt)
                prev, cur = cur, nxt
                if cur != start:
                    loop.append(cur)
            if cur == start and len(loop) > 3:
                loops.append(loop)
    return loops


def _simplify(loop):
    """Drop collinear midpoints from a closed integer loop."""
    n = len(loop)
    out = []
    for i in range(n):
        prev = loop[(i - 1) % n]
        cur = loop[i]
        nxt = loop[(i + 1) % n]
        cross = (cur[0] - prev[0]) * (nxt[1] - cur[1]) - (cur[1] - prev[1]) * (nxt[0] - cur[0])
        if cross != 0:
            out.append(cur)
    return out


def outline(bitmap, ox, oy, sx, sy, ascender=None, fmt=lambda v: "%.2f" % v) -> str:
    """Tight contour `d` for one glyph, one subpath per disjoint lobe."""
    parts = []
    for loop in _loops(_edges(bitmap, ascender)):
        pts = _simplify(loop)
        if len(pts) < 3:
            continue
        xs = [ox + p[0] * sx for p in pts]
        ys = [oy + p[1] * sy for p in pts]
        n = len(pts)
        d = ["M%s %s" % (fmt(xs[0]), fmt(ys[0]))]
        for i in range(1, n):
            if ys[i] == ys[i - 1]:
                d.append("H%s" % fmt(xs[i]))
            elif xs[i] == xs[i - 1]:
                d.append("V%s" % fmt(ys[i]))
            else:
                d.append("L%s %s" % (fmt(xs[i]), fmt(ys[i])))
        d.append("Z")
        parts.append("".join(d))
    return "".join(parts)


# --------------------------------------------------------------- hero (234x42)

HERO_CELL = 6
HERO_PITCH = 30
HERO_VIEWBOX_W = 234
# Weak underlay each letter carries in the shipped art, in cell coordinates
# relative to the glyph origin: (col0, row0, col1, row1).
HERO_WEAK = {
    "C": (1, 3, 4, 5),
    "O": (1, 3, 3, 5),
    "D": (1, 3, 3, 5),
    "E": (1, 4, 4, 5),
}


def _num(value) -> str:
    return str(int(value))


def build_hero(word: str) -> bytes:
    width = len(word) * HERO_PITCH - (HERO_PITCH - 4 * HERO_CELL)
    ox0 = (HERO_VIEWBOX_W - width) // 2
    oy = HERO_CELL  # cap row starts one cell below the ascender row
    out = []
    for index, letter in enumerate(word):
        ox = ox0 + index * HERO_PITCH
        weak = HERO_WEAK.get(letter)
        if weak:
            c0, r0, c1, r1 = weak
            x1 = ox + c0 * HERO_CELL
            x2 = ox + c1 * HERO_CELL
            y1 = oy + r0 * HERO_CELL
            y2 = oy + r1 * HERO_CELL
            out.append(
                '<path d="M%s %sH%sV%sH%sZ"fill=var(--icon-weak-base)></path>'
                % (_num(x2), _num(y1), _num(x1), _num(y2), _num(x2))
            )
        d = outline(
            GLYPHS[letter],
            ox,
            oy,
            HERO_CELL,
            HERO_CELL,
            ASCENDER.get(letter),
            fmt=_num,
        )
        out.append('<path d="%s"fill=var(--icon-base)></path>' % d)
    return "".join(out).encode("ascii")


# ------------------------------------------------- flat hero (route chunk, 234x42)
#
# The wordmark the user actually sees on the new-session screen is not a
# template: it is this array of glyph records, rendered one <g> per entry so the
# draw-on animation can transform each letter. The `P3t` SVG above it is only
# the shimmer overlay, so both have to be rewritten or the flat art shows
# through underneath.

FLAT_MARKER = b"ta=[{cx:"
FLAT_TERMINATOR = b"],na=234"


def build_flat(word: str) -> bytes:
    """Glyph records for the draw-on wordmark, aligned with build_hero()."""
    width = len(word) * HERO_PITCH - (HERO_PITCH - 4 * HERO_CELL)
    ox0 = (HERO_VIEWBOX_W - width) // 2
    oy = HERO_CELL
    out = []
    for index, letter in enumerate(word):
        ox = ox0 + index * HERO_PITCH
        cx = ox + 2 * HERO_CELL  # pivot: the component scales each glyph there
        weak_d = ""
        weak = HERO_WEAK.get(letter)
        if weak:
            c0, r0, c1, r1 = weak
            weak_d = "M%s %sH%sV%sH%sZ" % (
                _num(ox + c1 * HERO_CELL),
                _num(oy + r0 * HERO_CELL),
                _num(ox + c0 * HERO_CELL),
                _num(oy + r1 * HERO_CELL),
                _num(ox + c1 * HERO_CELL),
            )
        stem = outline(
            GLYPHS[letter], ox, oy, HERO_CELL, HERO_CELL, ASCENDER.get(letter), fmt=_num
        )
        out.append(
            "{cx:%s,weak:`%s`,fill:`var(--icon-base)`,stem:`%s`}" % (_num(cx), weak_d, stem)
        )
    # The component indexes glyph 7 for its cursor notch, so the slot has to
    # exist; empty path data draws nothing and costs almost no bytes.
    out.append("{cx:222,weak:``,fill:`var(--icon-base)`,stem:``}")
    return ",".join(out).encode("ascii")


# ------------------------------------------------------------ splash (720x129)

SPLASH_CELL_X = 720 / 39.0
SPLASH_CELL_Y = 129 / 7.0


def _dec2(value: float) -> str:
    text = "%.2f" % value
    text = text.rstrip("0").rstrip(".")
    return text or "0"


def build_splash(word: str) -> bytes:
    width = (len(word) * 5 - 1) * SPLASH_CELL_X
    ox0 = (720 - width) / 2
    oy = SPLASH_CELL_Y
    out = []
    for index, letter in enumerate(word):
        ox = ox0 + index * 5 * SPLASH_CELL_X
        d = outline(
            GLYPHS[letter],
            ox,
            oy,
            SPLASH_CELL_X,
            SPLASH_CELL_Y,
            ASCENDER.get(letter),
            fmt=_dec2,
        )
        out.append('<path d="%s"></path>' % d)
    return "".join(out).encode("ascii")


# --------------------------------------------------------------- pins (78x14)

# The pull animation is not vector art: while the wordmark is dragged a WebGL
# canvas paints a board of little pegs, one peg per half-cell, decoded from 14
# fixed-width strings of digits. `1` is a recessed peg, `2`/`3` are raised pegs
# at two depths, `.` is an empty hole.
#
# Each glyph owns 8 columns and 10 rows: a 4x5 bitmap at 2x, an ascender band
# one row above the cap block and a descender band one row below. Glyph i starts
# at column 10*i, so the board left edge is the wordmark's left edge - both the
# SVG art and the peg board begin at x=15 in the 234-wide hero viewBox.

PIN_COLS = 78
PIN_ROWS = 14
PIN_PITCH = 10
PIN_CAP_ROW = 2      # first row of the five cap bands
PIN_ASC_ROW = 0      # the single ascender band
PIN_INK_SPLIT = 4    # glyphs before this index use peg depth 2, after use 3


def _counters(bitmap):
    """Cells inside the letter that are empty but not reachable from outside."""
    height, width = len(bitmap), len(bitmap[0])
    filled = {
        (r, c)
        for r, row in enumerate(bitmap)
        for c, ch in enumerate(row)
        if ch == "#"
    }
    outside = set()
    stack = [
        (r, c)
        for r in range(height)
        for c in range(width)
        if (r in (0, height - 1) or c in (0, width - 1)) and (r, c) not in filled
    ]
    while stack:
        cell = stack.pop()
        if cell in outside or cell in filled:
            continue
        outside.add(cell)
        r, c = cell
        for n in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if 0 <= n[0] < height and 0 <= n[1] < width:
                stack.append(n)
    return {
        (r, c)
        for r in range(height)
        for c in range(width)
        if bitmap[r][c] == "." and (r, c) not in outside
    }


def build_pins(word: str) -> bytes:
    grid = [["." for _ in range(PIN_COLS)] for _ in range(PIN_ROWS)]
    for index, letter in enumerate(word):
        bitmap = GLYPHS[letter]
        ink = "2" if index < PIN_INK_SPLIT else "3"
        holes = _counters(bitmap)
        origin_x = index * PIN_PITCH
        for row in range(5):
            for col in range(4):
                if bitmap[row][col] == "#":
                    cell = ink
                elif (row, col) in holes:
                    cell = "1"
                else:
                    continue
                x = origin_x + col * 2
                y = PIN_CAP_ROW + row * 2
                for dy in (0, 1):
                    for dx in (0, 1):
                        grid[y + dy][x + dx] = cell
        ascender = ASCENDER.get(letter)
        if ascender:
            _, _, col = ascender
            for dx in (col * 2, col * 2 + 1):
                grid[PIN_ASC_ROW][origin_x + dx] = ink
                grid[PIN_ASC_ROW + 1][origin_x + dx] = ink
    return ",".join(
        "`" + "".join(row) + "`" for row in grid
    ).encode("ascii")


# -------------------------------------------------------------------- asar io


def asar_base(data: bytes) -> int:
    """Absolute offset of the first member's bytes.

    The header is two Pickles: a size word, then the JSON header string. The
    string body starts at 16 and is padded to a 4-byte boundary, so the data
    section does not begin at `8 + json_len` - that shortcut is 10 bytes early
    on this bundle and shifts every splice into the tail of the previous member.
    """
    json_len = struct.unpack("<I", data[12:16])[0]
    return 16 + json_len + ((4 - json_len % 4) % 4)


def load_asar():
    data = ASAR.read_bytes()
    json_len = struct.unpack("<I", data[12:16])[0]
    index = json.loads(data[16:16 + json_len].decode("utf-8", "replace"))
    return data, index, asar_base(data)


def parse_asar(data: bytes):
    """Split an asar image that is already in memory."""
    json_len = struct.unpack("<I", data[12:16])[0]
    index = json.loads(data[16:16 + json_len].decode("utf-8", "replace"))
    return index, asar_base(data)


def renderer_bundle(index):
    assets = index["files"]["out"]["files"]["renderer"]["files"]["assets"]["files"]
    for name, entry in assets.items():
        if name.startswith("main-") and name.endswith(".js") and entry.get("size", 0) > 1_000_000:
            return name, int(entry["offset"]), int(entry["size"])
    raise RuntimeError("renderer bundle not found")


def flat_route(index):
    """The lazily loaded route chunk that carries the draw-on wordmark."""
    assets = index["files"]["out"]["files"]["renderer"]["files"]["assets"]["files"]
    for name, entry in assets.items():
        size = int(entry.get("size", 0))
        if not name.startswith("route-") or not name.endswith(".js"):
            continue
        return name, int(entry["offset"]), size
    raise RuntimeError("route chunk not found")


def locate_flat(data, offset, size, base):
    """Resolve the glyph-record array of the draw-on wordmark."""
    body_start = base + offset
    body = data[body_start: body_start + size]

    at = body.find(FLAT_MARKER)
    if at < 0:
        raise RuntimeError("flat wordmark array not found")
    arr_start = at + len(b"ta=")
    tail = body.find(FLAT_TERMINATOR, arr_start)
    if tail < 0:
        raise RuntimeError("flat wordmark array is unterminated")
    arr_end = tail + 1  # past the closing ]

    block = body[arr_start:arr_end]
    return {
        "file_start": body_start + arr_start,
        "literal": block,
        "prefix": block[:1],          # the opening [
        "suffix": block[-1:],         # the closing ]
        "budget": len(block) - 2,
        "current": block[1:-1],
    }


def locate_pins(data, offset, size, base):
    """Resolve the 14-string peg board literal in byte space."""
    body_start = base + offset
    body = data[body_start: body_start + size]

    at = body.find(MARKER_PINS)
    if at < 0:
        raise RuntimeError("peg board literal not found")
    lit_start = at + len(b"li=")
    lit_end = body.find(TERM_PINS, lit_start)
    if lit_end < 0:
        raise RuntimeError("peg board literal is unterminated")

    block = body[lit_start: lit_end + 1]
    if not block.endswith(b"]"):
        raise RuntimeError("peg board literal is malformed")
    return {
        "file_start": body_start + lit_start,
        "literal": block,
        "prefix": b"[",
        "suffix": b"]",
        "budget": len(block) - 2,
        "current": block[1:-1],
    }


# The creature that rides the wordmark is placed by a run of flat constants:
# Y = hover anchor and neck base, X = pack target, Z = notch home. The notch
# rect and the two drag-grip rects are expressed separately. Every span below
# is byte-length identical to the shipped one, so the bundle never shifts.
#
# `legacy` holds shapes this tool wrote in an earlier pass. The grip span is the
# one that moved the crew: the first release rewrote BOTH branches of the hit
# rect, which parked the visible grab zone on the wordmark while the creature
# rests at `ia` (x=246, past the viewBox). Pulled out, it had no grabbable
# surface left, so it could never be dropped back into the notch. Only the
# hidden branch needs to follow the notch; the visible branch keeps the shipped
# park geometry.
ROUTE_SPANS = (
    {
        "label": "lodger anchors",
        "old": b"Y={x:222,y:15},X={x:222,y:21},Z={x:226.5,y:10.5}",
        "new": b"Y={x:207,y:15},X={x:207,y:21},Z={x:207.0,y:10.5}",
        "legacy": (),
    },
    {
        "label": "lodger notch",
        "old": b"<rect x=224.6 y=8.6 width=3.8 height=3.8",
        "new": b"<rect x=205.1 y=8.6 width=3.8 height=3.8",
        "legacy": (),
    },
    {
        "label": "lodger grip",
        "old": b"t===`hidden`?{x:213,y:8,w:18,h:14}:{x:234,y:18,w:24,h:24}",
        "new": b"t===`hidden`?{x:195,y:6,w:24,h:30}:{x:234,y:18,w:24,h:24}",
        "legacy": (b"t===`hidden`?{x:195,y:6,w:24,h:30}:{x:195,y:6,w:24,h:30.}",),
    },
    # The pin-drop leg of the carry animation lerps to a bare literal pair
    # (233, 18) that sits past the end of the old eight-glyph wordmark. ZZZCODE
    # ends at x=219, so the drop has to happen over the final E, not beyond it.
    {
        "label": "pin drop out",
        "old": b"$(ia,233,ya(t))",
        "new": b"$(ia,207,ya(t))",
        "legacy": (),
    },
    {
        "label": "pin drop back",
        "old": b"$(233,ia,ya(r))",
        "new": b"$(207,ia,ya(r))",
        "legacy": (),
    },
)


def locate_spans(data, offset, size, base):
    """Resolve the flat route-chunk constant spans.

    A span is in one of two states: shipped (`old`) or patched (`new`). A span
    written by an earlier release still resolves, so an install that predates a
    fix gets corrected instead of refused.
    """
    body_start = base + offset
    body = data[body_start: body_start + size]

    out = []
    for span in ROUTE_SPANS:
        old, new, label = span["old"], span["new"], span["label"]
        if len(old) != len(new):
            raise RuntimeError("%s: replacement is not length preserving" % label)
        for candidate in (old, *span["legacy"]):
            if len(candidate) != len(new):
                raise RuntimeError("%s: legacy literal is not length preserving" % label)

        hit = None
        for candidate in (old, *span["legacy"]):
            if body.count(candidate) == 1:
                hit = candidate
                break
        if hit is None:
            if body.count(new) == 1:
                hit = new
            else:
                raise RuntimeError("%s: no unique anchor found" % label)

        out.append(
            {
                "kind": "span",
                "label": label,
                "file_start": body_start + body.find(hit),
                "literal": hit,
                "span_new": new,
                "member": "",
            }
        )
    return out



def locate(data, offset, size, base, marker, viewbox):
    """Resolve one wordmark template in byte space.

    Byte offsets matter: the bundle carries multi-byte UTF-8 ahead of the
    template, so character indexes do not line up with asar offsets.
    """
    body_start = base + offset
    body = data[body_start: body_start + size]

    at = body.find(marker)
    if at < 0:
        raise RuntimeError("template %r not found" % marker)
    lit_start = at + len(marker)
    lit_end = body.find(b"`", lit_start)
    if lit_end < 0:
        raise RuntimeError("template literal is unterminated")

    literal = body[lit_start:lit_end]
    if viewbox not in literal:
        raise RuntimeError("viewBox %r not found in template" % viewbox)

    first = literal.find(PATH_OPEN)
    if first < 0:
        raise RuntimeError("path block not found inside the template")

    # Closes are not reliable: the templates are lit-html fragments, so the
    # final <path> is left unterminated for the parser to close. If anything
    # after the last </path> still opens a path, it is art, not template
    # markup, and it has to be replaced too - otherwise the tail of the old
    # wordmark keeps drawing on the right edge.
    last = literal.rfind(PATH_CLOSE)
    if last < 0:
        last = len(literal)
    else:
        last += len(PATH_CLOSE)
        if PATH_OPEN in literal[last:]:
            last = len(literal)

    return {
        "file_start": body_start + lit_start,
        "literal": literal,
        "prefix": literal[:first],
        "suffix": literal[last:],
        "budget": last - first,
        "current": literal[first:last],
    }


def plan(data, index, base):
    main_name, main_off, main_size = renderer_bundle(index)
    route_name, route_off, route_size = flat_route(index)
    jobs = []

    for label, marker, viewbox, art in (
        ("hero", MARKER_HERO, VIEWBOX_HERO, build_hero(WORD)),
        ("splash", MARKER_SPLASH, VIEWBOX_SPLASH, build_splash(WORD)),
    ):
        spot = locate(data, main_off, main_size, base, marker, viewbox)
        spot.update(kind="art", label=label, member=main_name, art=art)
        jobs.append(spot)

    flat = locate_flat(data, route_off, route_size, base)
    flat.update(kind="art", label="flat", member=route_name, art=build_flat(WORD))
    jobs.append(flat)

    pins = locate_pins(data, route_off, route_size, base)
    pins.update(kind="art", label="pins", member=route_name, art=build_pins(WORD))
    jobs.append(pins)

    spans = locate_spans(data, route_off, route_size, base)
    for span in spans:
        span["member"] = route_name
    jobs.extend(spans)

    return [main_name, route_name], jobs


def classify(jobs) -> None:
    """Mark every job done/pending and reject art that overflows its budget."""
    over = []
    for job in jobs:
        if job["kind"] == "span":
            job["done"] = job["literal"] == job["span_new"]
            continue
        job["pad"] = job["budget"] - len(job["art"])
        job["done"] = job["current"].rstrip(b" ") == job["art"]
        if job["pad"] < 0:
            over.append(job)
    if over:
        raise RuntimeError(
            "; ".join(
                "%s: art is %d bytes over budget" % (job["label"], -job["pad"])
                for job in over
            )
        )


def apply_jobs(data, jobs):
    """Splice every replacement in place. All jobs are length preserving."""
    out = bytearray(data)
    for job in jobs:
        if job["done"]:
            continue
        if job["kind"] == "span":
            payload = job["span_new"]
        else:
            payload = job["prefix"] + job["art"] + b" " * job["pad"] + job["suffix"]
        if len(payload) != len(job["literal"]):
            raise RuntimeError("%s: literal length drifted" % job["label"])
        start = job["file_start"]
        out[start: start + len(job["literal"])] = payload
    if len(out) != len(data):
        raise RuntimeError("asar size drifted")
    return bytes(out)



# ------------------------------------------------------------- lifecycle API
#
# The launcher applies the art for one desktop session and restores the pristine
# bundle afterwards, so the vendor install is never left rebranded. These three
# functions are the whole surface it needs; the CLI below is for humans.


def sha256_file(path: Path, chunk: int = 8 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(chunk)
            if not block:
                break
            digest.update(block)
    return digest.hexdigest()


def asar_state() -> dict:
    """Everything the launcher needs to decide what to do, without writing.

    `pristine_sha` fingerprints the vendor art: the backup when one exists,
    otherwise the live bundle when it is still untouched. A changed value means
    the desktop app updated itself.
    """
    state = {
        "available": ASAR.is_file(),
        "patched": False,
        "modified": False,
        "pending": 0,
        "backup": BACKUP.is_file(),
        "pristine_sha": "",
        "stale": False,
        "error": "",
    }
    if not state["available"]:
        return state
    try:
        if BACKUP.is_file():
            state["pristine_sha"] = sha256_file(BACKUP)
        data, index, base = load_asar()
        names, jobs = plan(data, index, base)
        classify(jobs)
    except (RuntimeError, OSError, ValueError) as exc:
        # A bundle written by an older pass resolves to nothing; the patch run
        # rolls it back before retrying, so this is not a dead end.
        try:
            state["stale"] = BACKUP.is_file() and _carries_zzz(ASAR.read_bytes())
        except OSError:
            state["stale"] = False
        if not state["stale"]:
            state["error"] = str(exc)[:160]
            return state
        return state

    done = sum(1 for job in jobs if job["done"])
    state["patched"] = done == len(jobs)
    state["modified"] = done > 0
    state["pending"] = len(jobs) - done
    if not state["pristine_sha"] and done == 0:
        state["pristine_sha"] = sha256_file(ASAR)
    return state


def patch_asar(retry: bool = True) -> tuple[bool, str]:
    """Apply the ZZZCODE art to the installed desktop bundle, in place."""
    if not ASAR.is_file():
        return False, "desktop bundle not installed"
    data = b""
    try:
        data = ASAR.read_bytes()
        index, base = parse_asar(data)
        names, jobs = plan(data, index, base)
        classify(jobs)
    except (RuntimeError, OSError, ValueError) as exc:
        # A bundle left behind by an older release carries our art but no longer
        # matches the current anchors. Roll it back and take a clean run at it
        # instead of refusing the install.
        if retry and BACKUP.is_file() and _carries_zzz(data):
            ok, _ = restore_asar()
            if ok:
                return patch_asar(False)
        return False, str(exc)[:160]

    done = sum(1 for job in jobs if job["done"])
    if done == len(jobs):
        return True, "wordmark already patched"

    # A bundle that is still fully shipped is the only valid restore source; a
    # partially patched one is never written over a good backup.
    if done == 0:
        try:
            BACKUP.write_bytes(data)
        except OSError as exc:
            return False, "backup failed: %s" % str(exc)[:64]

    try:
        patched = apply_jobs(data, jobs)
        ASAR.write_bytes(patched)
    except (RuntimeError, OSError) as exc:
        return False, str(exc)[:160]
    return True, "patched %d block(s)" % (len(jobs) - done)


def _art_signatures():
    """Byte prefixes unique to this project's art, used to recognise our writes.

    A bundle patched by an older release no longer resolves against the current
    literal anchors, so the markers have to be searched for outright. The art is
    deterministic, and each payload lands as one contiguous run, so the head of
    the run survives even when the whole block sits at the wrong offset.
    """
    return (build_hero(WORD)[:64], build_flat(WORD)[:64])


def _carries_zzz(data: bytes) -> bool:
    """True when the live bundle still holds bytes this project wrote.

    The old guard compared file sizes, which stopped working the moment the
    composer toggle repacked the archive. What actually matters is whether the
    bundle is ours: if a vendor update replaced it, none of these markers survive
    and restoring would downgrade the app.
    """
    try:
        json_len = struct.unpack("<I", data[12:16])[0]
        index = json.loads(data[16:16 + json_len].decode("utf-8"))
        base = asar_base(data)
    except (struct.error, ValueError, UnicodeDecodeError):
        return False

    try:
        _, jobs = plan(data, index, base)
        classify(jobs)
        if any(job["done"] for job in jobs):
            return True
    except (KeyError, RuntimeError, ValueError):
        pass

    try:
        page = index["files"]["out"]["files"]["renderer"]["files"]["index.html"]
        start = base + int(page["offset"])
        if b"zzz-gui.js" in data[start:start + int(page["size"])]:
            return True
    except (KeyError, TypeError, ValueError):
        pass

    for signature in _art_signatures():
        if data.find(signature) >= 0:
            return True
    return False


def restore_asar() -> tuple[bool, str]:
    """Put the vendor wordmark back from the pristine backup."""
    if not ASAR.is_file():
        return False, "desktop bundle not installed"
    if not BACKUP.is_file():
        return False, "no pristine backup to restore"
    try:
        data = ASAR.read_bytes()
        pristine = BACKUP.read_bytes()
    except OSError as exc:
        return False, "restore read failed: %s" % str(exc)[:64]
    if not _carries_zzz(data):
        return False, "backup is stale (app updated) - re-patch first"
    try:
        ASAR.write_bytes(pristine)
    except OSError as exc:
        return False, "restore write failed: %s" % str(exc)[:64]
    return True, "vendor wordmark restored"


# ----------------------------------------------------------------------- cli


def main(argv):
    if not ASAR.is_file():
        print("desktop bundle not found: %s" % ASAR, file=sys.stderr)
        return 1

    if "--state" in argv:
        state = asar_state()
        for key in ("available", "patched", "modified", "pending", "backup", "pristine_sha", "error"):
            print("%-12s: %s" % (key, state[key]))
        return 0

    if "--restore" in argv:
        ok, message = restore_asar()
        print(("restored %s (%d bytes)" % (ASAR, ASAR.stat().st_size)) if ok else message)
        return 0 if ok else 1

    try:
        data, index, base = load_asar()
        names, jobs = plan(data, index, base)
        classify(jobs)
    except (RuntimeError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if "--check" in argv:
        for name in names:
            print("member      : %s" % name)
        for job in jobs:
            if job["kind"] == "span":
                print(
                    "%-14s: %d bytes, %s"
                    % (job["label"], len(job["literal"]),
                       "patched" if job["done"] else "patchable")
                )
            else:
                print(
                    "%-14s: block %d, art %d, pad %d, %s"
                    % (job["label"], job["budget"], len(job["art"]), job["pad"],
                       "patched" if job["done"] else "patchable")
                )
        return 0

    ok, message = patch_asar()
    if not ok:
        print(message, file=sys.stderr)
        return 1
    print("asar        : %s" % ASAR)
    print("wordmark    : %s" % WORD)
    print("result      : %s" % message)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
