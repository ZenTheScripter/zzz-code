"""Console intro and menu animation for the ZzZ Code launcher.

Three stages, in order:

1. `matrix_rain()`      green code rain filling the console
2. `wordmark()`         the "MADE BY ZZZ" block art
3. `sweep()`            a bright band running across that art, left to right

Everything is opt-in and bounded: `enabled()` is False when stdout is not a TTY,
when `ZZZ_NO_ANIM=1` is set, or when the console refused VT (Windows 10 older
than 1511, a redirected pipe, a CI runner). In that case the caller prints its
static art and nothing loops. Every animation has a hard frame cap derived from
its duration, so a slow terminal cannot stretch the boot into a hang.
"""

from __future__ import annotations

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
