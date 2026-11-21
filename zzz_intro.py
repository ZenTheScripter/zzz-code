"""Console intro and menu animation for the ZzZ Code launcher.

Stages, in order:

1. `rain_reveal()`  green rain that carves "MADE BY ZZZ" out of the field, one
                    column at a time, then drains and leaves the art behind
2. `word_glow()`    a band of light crossing that art while it breathes
3. `menu_banner()`  the travelling rule and decoding tagline above a menu page

Everything is opt-in and bounded: `enabled()` is False when stdout is not a TTY,
when `ZZZ_NO_ANIM=1` is set, or when the console refused VT (Windows 10 older
than 1511, a redirected pipe, a CI runner). In that case the caller prints its
static art and nothing loops. Every animation has a hard frame cap derived from
its duration, so a slow terminal cannot stretch the boot into a hang.
"""

from __future__ import annotations

import math
import os
import random
import shutil
import sys
import time

# 5x7 cap bitmap, one column of gutter between glyphs, rendered as four text
# rows of half blocks. Full A-Z plus digits so any status word can be drawn.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("11111", "00100", "00100", "00100", "00100", "00100", "11111"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    " ": ("000", "000", "000", "000", "000", "000", "000"),
}

FONT_H = 7
FONT_W = 5

# Green ramp for the rain: darkest trail tail -> brightest head.
RAIN_RAMP = ("22", "22", "28", "28", "34", "34", "40", "46", "46", "231")
RAIN_GLYPHS = "01<>[]{}/\\|=+-*#$%&@;:!?0123456789"

WORD_RAMP = ("28", "34", "40", "46", "46", "46", "82")
SWEEP_COLOR = "231"
BASE_COLOR = "22"

# Printed above every menu page once the boot animation has had its run.
MENU_TAGLINE = "abliterated sheet  \u00b7  35 themes  \u00b7  warp lane  \u00b7  self update"


def _c(code: str, text: str) -> str:
    return "\x1b[38;5;%sm%s\x1b[0m" % (code, text)


def enabled() -> bool:
    """Animations are opt-out by flag and impossible without a terminal."""
    if os.environ.get("ZZZ_NO_ANIM") == "1":
        return False
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def size() -> tuple[int, int]:
    try:
        cols, rows = shutil.get_terminal_size((100, 32))
    except Exception:
        cols, rows = 100, 32
    return max(20, cols), max(10, rows)


# ---------------------------------------------------------------------- font


def _grid(word: str) -> list[list[bool]]:
    cells = []
    width = 0
    for ch in word.upper():
        bitmap = FONT.get(ch)
        if bitmap is None:
            bitmap = FONT[" "]
        advance = 4 if ch == " " else FONT_W + 1
        cells.append((bitmap, advance))
        width += advance
    width = max(1, width - 1)

    # Padded to an even height: a 7-row font rendered as half blocks would drop
    # its last pixel row, which cuts the baseline off every glyph.
    height = FONT_H + (FONT_H % 2)
    grid = [[False] * width for _ in range(height)]
    x = 0
    for bitmap, advance in cells:
        for row in range(FONT_H):
            for col in range(FONT_W):
                if col < len(bitmap[row]) and bitmap[row][col] == "1":
                    grid[row][x + col] = True
        x += advance
    return grid


def _half(top: bool, bottom: bool) -> str:
    if top and bottom:
        return "\u2588"
    if top:
        return "\u2580"
    if bottom:
        return "\u2584"
    return " "


def art(word: str, ramp: tuple[str, ...] = WORD_RAMP) -> list[str]:
    """Block art rows, shaded left to right, no ANSI (plain text)."""
    grid = _grid(word)
    height = len(grid)
    width = len(grid[0])
    rows = []
    for text_row in range(height // 2):
        top_row, bottom_row = text_row * 2, text_row * 2 + 1
        out = []
        for x in range(width):
            top = grid[top_row][x]
            bottom = bottom_row < height and grid[bottom_row][x]
            out.append(_half(top, bottom))
        rows.append("".join(out).rstrip())
    return rows


def tinted(word: str, ramp: tuple[str, ...] = WORD_RAMP) -> list[str]:
    """Block art rows with a left-to-right colour ramp baked in."""
    plain = art(word)
    width = max((len(r) for r in plain), default=1)
    rows = []
    for line in plain:
        chunks = []
        run, run_color = "", None
        for x, ch in enumerate(line):
            if ch == " ":
                color = None
            else:
                idx = min(len(ramp) - 1, x * len(ramp) // max(1, width))
                color = ramp[idx]
            if color != run_color:
                if run:
                    chunks.append(_c(run_color, run) if run_color else run)
                run, run_color = "", color
            run += ch
        if run:
            chunks.append(_c(run_color, run) if run_color else run)
        rows.append("".join(chunks))
    return rows


# --------------------------------------------------------------------- rain


def matrix_rain(duration: float = 2.4, fps: int = 24) -> None:
    """Green code rain, then leave the cursor on a clean line.

    Three details make it read like the film instead of a screensaver: the head
    glyph is white and the two behind it are bright green, so every column has a
    visible leading edge; a handful of columns get a random bright flash per
    frame; and the first quarter of the run ramps the density up from a few
    drops so the screen fills instead of starting full.
    """
    if not enabled():
        return
    w, h = size()
    cols = max(24, min(w - 1, 150))
    rows = max(8, h - 2)
    frames = max(1, min(int(duration * fps), 160))
    delay = 1.0 / max(1, fps)

    rng = random.Random()
    head = [rng.randint(-rows, 0) for _ in range(cols)]
    speed = [rng.choice((1, 1, 2, 2, 3)) for _ in range(cols)]
    trail = [rng.randint(6, max(9, rows - 2)) for _ in range(cols)]
    cells = [[" "] * cols for _ in range(rows)]
    ramp = ("22", "22", "28", "34", "40", "46", "231")
    lead = ("231", "46", "40")
    ramp_in = max(1, frames // 4)
    # A few columns restart with a visible flash so the field never looks even.
    flash = [rng.randint(0, frames - 1) for _ in range(max(2, cols // 10))]

    out = sys.stdout
    out.write("\x1b[?25l\x1b[2J\x1b[H")
    out.flush()
    try:
        for frame in range(frames):
            active = cols if frame >= ramp_in else max(6, cols * frame // ramp_in)
            for c in range(cols):
                if c >= active:
                    for r in range(rows):
                        cells[r][c] = " "
                    continue
                head[c] += speed[c]
                if head[c] - trail[c] > rows:
                    head[c] = rng.randint(-2 * rows, 0)
                    speed[c] = rng.choice((1, 1, 2, 2, 3))
                    trail[c] = rng.randint(6, max(9, rows - 2))

            for r in range(rows):
                row_cells = cells[r]
                for c in range(cols):
                    dist = head[c] - r
                    if 0 <= dist < trail[c]:
                        if row_cells[c] == " " or rng.random() < 0.04:
                            row_cells[c] = rng.choice(RAIN_GLYPHS)
                    else:
                        row_cells[c] = " "

            lines = []
            fade = frame > frames - max(2, frames // 5)
            for r in range(rows):
                row_cells = cells[r]
                chunks = []
                run, run_color = "", None
                for c in range(cols):
                    ch = row_cells[c]
                    if ch == " ":
                        color = None
                    else:
                        dist = head[c] - r
                        if dist < len(lead):
                            color = lead[dist]
                        else:
                            idx = min(len(ramp) - 1, 2 + (dist - 2) // 2)
                            color = ramp[idx]
                        if any(c == f % cols and frame >= flash[f % len(flash)] for f in range(len(flash))):
                            color = "46"
                        if fade and (c + frame) % 3 == 0:
                            color = "22"
                    if color != run_color or ch == " ":
                        if run:
                            chunks.append(_c(run_color, run) if run_color else run)
                        run, run_color = "", color
                    run += ch
                if run:
                    chunks.append(_c(run_color, run) if run_color else run)
                lines.append("".join(chunks))

            out.write("\x1b[H" + "\n".join(lines) + "\x1b[0m")
            out.flush()
            time.sleep(delay)
    finally:
        out.write("\x1b[0m\x1b[?25h")
        out.flush()


# ------------------------------------------------------------- rain reveal


def _place(art_rows: list[str], cols: int, rows: int) -> tuple[int, int]:
    """Where the word sits: centred on both axes, one row below dead centre."""
    width = max((len(r) for r in art_rows), default=1)
    left = max(0, (cols - width) // 2)
    top = max(1, (rows - len(art_rows)) // 2 + 1)
    if top + len(art_rows) > rows - 1:
        top = max(1, rows - 1 - len(art_rows))
    return left, top


def _pack(chars: list[tuple[str, str | None]]) -> str:
    """Join (char, colour) pairs into colour runs."""
    chunks: list[str] = []
    run, run_color = "", None
    for ch, color in chars:
        if color != run_color:
            if run:
                chunks.append(_c(run_color, run) if run_color else run)
            run, run_color = "", color
        run += ch
    if run:
        chunks.append(_c(run_color, run) if run_color else run)
    return "".join(chunks)


def rain_reveal(
    word: str = "MADE BY ZZZ", duration: float = 3.6, fps: int = 24
) -> tuple[list[str], int, int] | None:
    """Rain that carves `word` out of the field, column by column.

    A column's letter cells lock the moment its drop passes the word band, so the
    art assembles left to right inside the falling code instead of fading in as a
    separate layer. The last third drains: drops stop respawning, trails collapse,
    and what is left standing is the word, centred in the lower half of the
    console with the empty rain above it.

    Returns the plain art rows and their origin so `word_glow()` can animate the
    same art in place, or None when animations are off.
    """
    art_rows = art(word)
    if not enabled():
        for line in tinted(word):
            print("   " + line)
        return None

    w, h = size()
    cols = max(24, min(w - 1, 150))
    rows = max(12, h - 2)
    count = len(art_rows)
    width = max((len(r) for r in art_rows), default=1)
    left, top = _place(art_rows, cols, rows)

    frames = max(1, min(int(duration * fps), 200))
    delay = 1.0 / max(1, fps)
    drain = frames * 2 // 3
    band_bottom = top + count            # the row the first letter needs cleared

    rng = random.Random()
    head = [rng.randint(-rows, -1) for _ in range(cols)]
    speed = [rng.choice((1, 1, 2, 2, 3)) for _ in range(cols)]
    trail = [rng.randint(6, max(9, rows // 2)) for _ in range(cols)]
    # Deepest row each column's drop has ever reached. A letter cell is carved
    # once its own row is at or above that mark, so the art grows behind the
    # drops instead of switching on all at once, and never un-carves when the
    # column dies.
    reached = [-(10 ** 6)] * cols
    cells = [[" "] * cols for _ in range(rows)]
    ramp = ("22", "22", "28", "34", "40", "46", "231")
    lead = ("231", "46", "40")

    out = sys.stdout
    out.write("\x1b[?25l\x1b[2J\x1b[H")
    out.flush()
    try:
        for frame in range(frames):
            for c in range(cols):
                if frame >= drain:
                    if reached[c] < band_bottom:
                        # Drain phase: hurry the stragglers down through the word
                        # so every column has carved its letters before the rain
                        # stops.
                        head[c] = max(head[c], 0) + 5
                    else:
                        # Carved: run the drop out of the frame and collapse the
                        # trail behind it, which is what leaves the art clean.
                        head[c] += 5
                        trail[c] = max(1, trail[c] - 2)
                else:
                    head[c] += speed[c]
                if head[c] > reached[c]:
                    reached[c] = head[c]
                if head[c] - trail[c] > rows:
                    if frame >= drain:
                        head[c] = -(10 ** 6)      # out of play, never respawns
                    else:
                        head[c] = rng.randint(-2 * rows, 0)
                        speed[c] = rng.choice((1, 1, 2, 2, 3))
                        trail[c] = rng.randint(6, max(9, rows // 2))

            for r in range(rows):
                row_cells = cells[r]
                for c in range(cols):
                    dist = head[c] - r
                    if 0 <= dist < trail[c]:
                        if row_cells[c] == " " or rng.random() < 0.04:
                            row_cells[c] = rng.choice(RAIN_GLYPHS)
                    else:
                        row_cells[c] = " "

            lines: list[str] = []
            for r in range(rows):
                row_cells = cells[r]
                band_row = r - top
                art_line = art_rows[band_row] if 0 <= band_row < count else ""
                pair: list[tuple[str, str | None]] = []
                for c in range(cols):
                    x = c - left
                    if (
                        art_line
                        and 0 <= x < len(art_line)
                        and art_line[x] != " "
                        and reached[c] >= r
                    ):
                        # How far the drop has run past this cell: bright right
                        # behind the head, cooling as the trail falls away.
                        age = reached[c] - r
                        if age <= 2:
                            color = "231"
                        elif age <= 7:
                            color = "82"
                        elif age <= 14:
                            color = "46"
                        elif (frame // 4 + x + r) % 11 == 0:
                            color = "82"
                        else:
                            color = "40"
                        pair.append((art_line[x], color))
                        continue
                    ch = row_cells[c]
                    if ch == " ":
                        pair.append((" ", None))
                        continue
                    dist = head[c] - r
                    if dist < len(lead):
                        pair.append((ch, lead[dist]))
                    else:
                        pair.append((ch, ramp[min(len(ramp) - 1, 2 + (dist - 2) // 2)]))
                lines.append(_pack(pair))

            out.write("\x1b[H" + "\n".join(lines) + "\x1b[0m")
            out.flush()
            time.sleep(delay)

        out.write("\x1b[%d;%dH\x1b[0m\n" % (top + count + 1, 1))
        out.flush()
    finally:
        out.write("\x1b[0m\x1b[?25h")
        out.flush()
    return art_rows, left, top


def word_glow(
    art_rows: list[str], left: int, top: int, cycles: float = 2.0, delay: float = 0.028
) -> None:
    """A band of light crosses the standing word while it breathes.

    Absolute cursor addressing keeps the art where the rain left it, so the glow
    reads as the same object being lit rather than a second drawing.
    """
    if not enabled() or not art_rows:
        return
    width = max((len(r) for r in art_rows), default=1)
    frames = max(8, min(int(18 * cycles), 64))
    out = sys.stdout
    out.write("\x1b[?25l")
    try:
        for frame in range(frames):
            band = -8.0 + (width + 16.0) * frame / max(1, frames - 1)
            pulse = 0.5 - 0.5 * math.cos(frame / 2.6)
            for i, line in enumerate(art_rows):
                pair: list[tuple[str, str | None]] = []
                for x, ch in enumerate(line):
                    if ch == " ":
                        pair.append((" ", None))
                        continue
                    d = abs(x - band)
                    if d < 1.5:
                        color = "231"
                    elif d < 4.5:
                        color = "82"
                    elif d < 9.0:
                        color = "46"
                    else:
                        color = "46" if pulse > 0.45 else "40"
                    pair.append((ch, color))
                out.write("\x1b[%d;%dH%s" % (top + i + 1, left + 1, _pack(pair)))
            out.write("\x1b[0m")
            out.flush()
            time.sleep(delay)

        for i, line in enumerate(art_rows):
            pair = [(ch, WORD_RAMP[min(len(WORD_RAMP) - 1, x * len(WORD_RAMP) // max(1, width))]
                     if ch != " " else None) for x, ch in enumerate(line)]
            out.write("\x1b[%d;%dH%s" % (top + i + 1, left + 1, _pack(pair)))
        out.write("\x1b[0m\n")
        out.flush()
    finally:
        out.write("\x1b[0m\x1b[?25h")
        out.flush()


def intro_sequence(word: str = "MADE BY ZZZ", duration: float = 3.6, fps: int = 24) -> None:
    """Rain reveal, then the light crossing the art it left behind."""
    geometry = rain_reveal(word, duration=duration, fps=fps)
    if geometry:
        word_glow(*geometry)


# ------------------------------------------------------------- menu banner


def _wave(width: int, head: float) -> str:
    """A rule with a bright head running along it, gradient trailing both ways."""
    pair: list[tuple[str, str]] = []
    for x in range(width):
        d = abs(x - head)
        if d < 2.0:
            color = "231"
        elif d < 5.0:
            color = "82"
        elif d < 9.0:
            color = "46"
        elif d < 14.0:
            color = "34"
        else:
            color = "22"
        pair.append(("\u2500", color))
    return _pack(pair)


def menu_banner(tagline: str = MENU_TAGLINE, width: int = 0, indent: int = 2, animate: bool = True) -> None:
    """Travelling rule plus a tagline that decodes, printed above a menu page.

    Static on every repaint except the first few after boot, so navigation stays
    instant and the movement only happens when it is worth watching.
    """
    width = width or len(tagline)
    try:
        avail = max(20, size()[0] - indent - 1)
    except Exception:
        avail = 78
    if width > avail:
        width = avail
    if len(tagline) > avail:
        tagline = tagline[: max(0, avail - 1)].rstrip(" .")
    pad = " " * indent
    if not animate or not enabled():
        print(pad + _c("22", "\u2500" * width))
        print(pad + _c("46", tagline))
        return

    out = sys.stdout
    frames = 16
    out.write("\x1b[?25l")
    try:
        for f in range(frames):
            head = -6.0 + (width + 12.0) * f / max(1, frames - 1)
            out.write("\r" + pad + _wave(width, head))
            out.flush()
            time.sleep(0.018)
        out.write("\r" + pad + _c("22", "\u2500" * width) + "\n")

        rng = random.Random()
        glyphs = "01<>[]{}/\\|=+-*#$%&;:!?"
        for frame in range(5):
            locked = len(tagline) * frame // 5
            text = "".join(
                ch if x < locked or ch == " " else rng.choice(glyphs)
                for x, ch in enumerate(tagline)
            )
            out.write("\r" + pad + _c("46", text))
            out.flush()
            time.sleep(0.028)
        out.write("\r" + pad + _c("46", tagline) + "\n")
        out.flush()
    finally:
        out.write("\x1b[0m\x1b[?25h")
        out.flush()


# -------------------------------------------------------------------- sweep


def _paint_band(plain: list[str], band: int) -> list[str]:
    """One frame of the sweep: colour by distance from the band column."""
    rows = []
    for line in plain:
        chunks = []
        run, run_color = "", None
        for x, ch in enumerate(line):
            if ch == " ":
                color = BASE_COLOR
            else:
                d = abs(x - band)
                if d == 0:
                    color = SWEEP_COLOR
                elif d < 3:
                    color = "46"
                elif d < 7:
                    color = "40"
                elif d < 12:
                    color = "34"
                else:
                    color = BASE_COLOR
            if color != run_color:
                if run:
                    chunks.append(_c(run_color, run))
                run, run_color = "", color
            run += ch
        if run:
            chunks.append(_c(run_color, run))
        rows.append("".join(chunks))
    return rows


def sweep(word: str, step: int = 4, delay: float = 0.022, indent: int = 3) -> list[str]:
    """Paint `word` dark, then run a bright band across it.

    Returns the plain art rows so the caller can reuse them without a second
    rasterisation pass. When animations are off this prints the static tinted
    art and returns immediately.
    """
    plain = art(word)
    pad = " " * indent
    if not enabled():
        for line in plain:
            print(pad + line)
        return plain

    width = max((len(r) for r in plain), default=1)
    back = "\r\x1b[%dA" % max(0, len(plain) - 1)
    out = sys.stdout
    out.write("\x1b[?25l")
    try:
        first = _paint_band(plain, -10)
        out.write("\n".join(pad + line for line in first))
        out.flush()
        band = -4
        while band <= width + 12:
            band += step
            frame = _paint_band(plain, band)
            out.write(back + "\n".join(pad + line for line in frame) + "\x1b[0m")
            out.flush()
            time.sleep(delay)
        final = tinted(word)
        out.write(back + "\n".join(pad + line for line in final) + "\x1b[0m\n")
        out.flush()
    finally:
        out.write("\x1b[?25h")
        out.flush()
    return plain


def reveal(line: str, delay: float = 0.018) -> None:
    """Print one line, pause, so a panel assembles itself instead of popping."""
    if enabled() and delay > 0:
        print(line)
        sys.stdout.flush()
        time.sleep(delay)
    else:
        print(line)

def decode_lines(lines: list[str], delay: float = 0.016, passes: int = 5) -> None:
    """Paint lines as scrambling glyphs that resolve into the real text.

    Used for the first menu page: every row starts as noise, then locks in from
    the left one column at a time while the unlocked tail keeps mutating. Box
    drawing characters are exempt - a frame border that flickers is unreadable,
    so borders paint immediately and only the content resolves.
    """
    if not enabled() or not lines:
        for line in lines:
            print(line)
        return

    out = sys.stdout
    plain = [line for line in lines]
    width = max((len(line) for line in plain), default=1)
    rng = random.Random()
    frames = max(1, min(passes, 8))
    glyphs = "01<>[]{}/\\|=+-*#$%&;:!?"
    out.write("\x1b[?25l")
    try:
        for frame in range(frames):
            locked = 0 if frame == 0 else (width * frame // frames)
            rows = []
            for line in plain:
                buf = []
                for x, ch in enumerate(line):
                    if ch in " \u2500\u2502\u250c\u2510\u2514\u2518\u25b8\u00b7" or x < locked:
                        buf.append(ch)
                    else:
                        buf.append(rng.choice(glyphs))
                rows.append("   " + "".join(buf))
            out.write("\x1b[H" + "\n".join(rows) + "\x1b[0m")
            out.flush()
            time.sleep(delay)
        out.write("\x1b[H" + "\n".join("   " + line for line in plain) + "\x1b[0m\n")
        out.flush()
    finally:
        out.write("\x1b[?25h")
        out.flush()
