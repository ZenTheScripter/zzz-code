# Themes

The guide the app writes to `~/.zzzcode/themes/README.md` on first run. The same
text ships in the binary, so this file is a copy for readers of the repo.

# ZzZ Code themes

Every `.json` file dropped in this folder appears in **Settings > Themes**.
Pick one and the renderer repaints instantly; `Default` hands the vendor theme
back. Files are read on every open, so edit a file and hit `Reload`.

Nothing is installed and nothing is patched into the app. The renderer writes
one stylesheet into `<head>` for the length of the session:

```
:root,[data-color-scheme],[data-theme]{--v2-background-bg-base:#06121a !important;...}
```

Because it is a stylesheet rather than an inline style, it survives the shell
re-rendering `<html data-color-scheme>` on a scheme flip. Closing the app drops
the sheet and the vendor palette comes back by itself.

## The smallest possible theme

```json
{
  "name": "Mine",
  "author": "me",
  "colors": {
    "--v2-background-bg-base": "#0b0b10",
    "--v2-text-text-base": "#f5f5ff"
  }
}
```

That is the whole format. `name` is what the tab shows, `author` is free text,
`colors` maps CSS custom properties to values. A theme with three keys is legal
- everything it does not set keeps the vendor value.

## The file format

| key | required | type | notes |
| --- | --- | --- | --- |
| `name` | no | string | tab label, 48 chars max, falls back to the filename |
| `author` | no | string | 32 chars max, shown in the swatch tooltip |
| `kind` | no | string | `light`, `dark`, `custom`; drives `color-scheme` and the scrollbars |
| `colors` | yes | object | at least one entry, keys start with `--` |

Unknown top-level keys are ignored, so a file can carry a `notes` field for
yourself. A file without a usable `colors` object is skipped silently rather
than breaking the tab.

## Which properties to set

The shell is painted from a small set of `--v2-*` custom properties. The ones
worth knowing, in the order they matter:

| property | what it paints |
| --- | --- |
| `--v2-background-bg-base` | window background |
| `--v2-background-bg-deep` | the well behind the window, composer edge |
| `--v2-background-bg-layer-01` | sidebar, panels |
| `--v2-background-bg-layer-02` | raised cards |
| `--v2-background-bg-layer-03` | hover rows, tab pills |
| `--v2-background-bg-layer-04` | pressed rows, borders of inputs |
| `--v2-background-bg-contrast` | inverted blocks: code chips, badges |
| `--v2-background-bg-accent` | primary button fill |
| `--v2-text-text-base` | body text |
| `--v2-text-text-muted` | secondary text |
| `--v2-text-text-faint` | timestamps, hints |
| `--v2-text-text-contrast` | text on `--v2-background-bg-contrast` |
| `--v2-text-text-accent` | links, active labels |
| `--v2-text-text-accent-hover` | the same labels under the cursor |
| `--v2-text-text-code-accent` | inline code colour |
| `--v2-border-border-base` | hairlines |
| `--v2-border-border-strong` | dividers, input outlines |
| `--v2-border-border-focus` | focus rings |
| `--v2-icon-icon-base` | nav icons |
| `--v2-icon-icon-muted` | disabled icons |
| `--v2-icon-icon-accent` | active nav icons |
| `--v2-blue-300` | accent ramp: hover |
| `--v2-blue-400` | accent ramp: base |
| `--v2-blue-500` | accent ramp: fill |
| `--v2-blue-600` | accent ramp: pressed |

Another hundred tokens exist (`--v2-red-500`, `--v2-elevation-raised`,
`--v2-avatar-bg-gray`, spacing and radius variables). They all work exactly the
same way: override a name and the shell uses your value. Two rules keep you out
of trouble:

- Anything that is a colour belongs on a `--v2-*` colour token. Overriding a
  spacing or radius token repaints the layout and will fight the vendor CSS.
- If you set `kind` to `light` or `dark`, the sheet also emits
  `color-scheme`, which flips the scrollbars and the caret to match the palette.

Values must be plain CSS (hex, `rgb()`, `hsl()`, `var(--something)`); anything
with `;`, `}`, `<`, `>` or a newline is stripped by the loader, so a theme
cannot break out of its declaration.

## Reading the palette, layer by layer

Every surface in the shell is one of four layers stacked on a base. Get the
steps right and the rest follows:

- `base` — the page. This is the colour you see behind everything.
- `layer-01` — one step away from the page: the sidebar, the settings rail.
- `layer-02` — two steps: cards, the composer, list rows at rest.
- `layer-03` — three steps: a row under the pointer, the selected tab pill.
- `layer-04` — four steps: a row being clicked, the outline of a text input.

A dark palette steps **up** in lightness (each layer a touch lighter than the
one below). A light palette steps **down** (each layer a touch darker). Six to
ten percent apart is the sweet spot; anything tighter than four percent reads
as a flat slab, and anything wider than fourteen percent makes hover states
look like separate panels.

Text follows the same logic in reverse: `base` text near the extreme of the
palette (near-white on dark, near-black on light), `muted` about 60 percent of
that contrast, `faint` about 35 percent. If `muted` and `faint` are close
together, every hint and timestamp in the app goes unreadable.

## A dark theme that actually reads

```json
{
  "name": "Deep Water",
  "author": "me",
  "kind": "dark",
  "colors": {
    "--v2-background-bg-base": "#06121a",
    "--v2-background-bg-deep": "#04101a",
    "--v2-background-bg-layer-01": "#0b1a24",
    "--v2-background-bg-layer-02": "#11232f",
    "--v2-background-bg-layer-03": "#172c3a",
    "--v2-background-bg-layer-04": "#1e3746",
    "--v2-background-bg-contrast": "#d9ecf7",
    "--v2-text-text-base": "#d9ecf7",
    "--v2-text-text-muted": "#8fb3c6",
    "--v2-text-text-faint": "#5d7d8e",
    "--v2-text-text-contrast": "#06121a",
    "--v2-border-border-base": "#1b3644",
    "--v2-border-border-strong": "#27485a",
    "--v2-border-border-focus": "#5fd0e6",
    "--v2-background-bg-accent": "#1f6f8b",
    "--v2-text-text-accent": "#5fd0e6",
    "--v2-text-text-accent-hover": "#9de8f7",
    "--v2-icon-icon-base": "#8fb3c6",
    "--v2-icon-icon-muted": "#5d7d8e",
    "--v2-icon-icon-accent": "#5fd0e6",
    "--v2-blue-300": "#9de8f7",
    "--v2-blue-400": "#5fd0e6",
    "--v2-blue-500": "#1f6f8b",
    "--v2-blue-600": "#1f6f8b"
  }
}
```

## A light theme, same procedure

```json
{
  "name": "Sand",
  "author": "me",
  "kind": "light",
  "colors": {
    "--v2-background-bg-base": "#faf7f0",
    "--v2-background-bg-layer-01": "#f2eee4",
    "--v2-background-bg-layer-02": "#e9e4d8",
    "--v2-background-bg-layer-03": "#ded8ca",
    "--v2-background-bg-layer-04": "#cfc8b8",
    "--v2-text-text-base": "#241f18",
    "--v2-text-text-muted": "#5f574a",
    "--v2-text-text-faint": "#8a8071",
    "--v2-border-border-base": "#ded8ca",
    "--v2-border-border-strong": "#c4bcaa",
    "--v2-background-bg-accent": "#8a6a2f",
    "--v2-text-text-accent": "#7a5c26",
    "--v2-blue-400": "#7a5c26",
    "--v2-blue-500": "#8a6a2f"
  }
}
```

## Building one from scratch

1. Pick the page colour. Sample it from an image you like, or take the darkest
   neutral in a palette you trust. That is `--v2-background-bg-base`.
2. Walk four layers away from it in one direction, six to ten percent lightness
   per step. Write them into `layer-01` through `layer-04`.
3. Set `--v2-text-text-base` to the palette's lightest ink on a dark background
   (or darkest ink on light). Then drop 40 percent for `muted` and 65 percent
   for `faint`.
4. Pick one accent. Put it on `--v2-text-text-accent`, its lighter sibling on
   `--v2-text-text-accent-hover`, a desaturated version on
   `--v2-background-bg-accent`, and fill the `--v2-blue-300..600` ramp with
   hover / base / fill / pressed.
5. Hairlines: `--v2-border-border-base` one step past `layer-02`,
   `--v2-border-border-strong` one step past that, and the accent on
   `--v2-border-border-focus`.
6. Save as `my-theme.json`, open **Settings > Themes**, hit `Reload`, click the
   swatch. Every surface repaints without a restart.

Editing while the app runs works: change the JSON, hit `Reload`, click the
swatch again. There is no cache to clear.

## Troubleshooting

| symptom | cause |
| --- | --- |
| file does not appear in the tab | not valid JSON, no `colors` object, or the name starts with a dot |
| swatch applies, nothing changes | every key in the file failed validation; check for `;` or `url(` |
| sidebar stays vendor grey | you only set `layer-03`; the sidebar reads `layer-01` |
| hover rows look like panels | layers are more than about 14 percent apart |
| scrollbars stay the wrong brightness | no `kind`, so `color-scheme` never flipped |
| text disappears on selected rows | `--v2-text-text-contrast` was left on the vendor value |
| palette undoes itself after a scheme flip | reload the app; the sheet is re-read on load, older builds painted inline |

## Rules the loader enforces

- File must be valid JSON and live in this folder, extension `.json`.
- `colors` must be a non-empty object; keys start with `--`.
- Values are capped at 64 characters and cannot contain `;`, `}`, `<`, `>` or a
  newline.
- Up to 64 theme files are read; the first 256 keys of each are used.
- `active.json` is written by the app and is not a theme - leave it alone.
- A file named `.something.json` is ignored, so a draft can be parked in place.

## Shipping a theme with the build

The 35 builtin palettes live in `zzzcode_app.py` as `_BUILTIN_THEMES`, one row
per theme:

```
(id, name, kind, bg, layer1, layer2, layer3, layer4,
 text, muted, faint, border, strong, accent_bg, accent_text, accent_hover)
```

`_theme_from_row()` expands a row into the full twenty-six-key colour map, which
is why a builtin sets the whole surface set and a user file can set as few keys
as it likes. Adding a row is the entire procedure for shipping a new palette;
the tab picks it up on the next launch, and no other file has to change.

User files win ties: a `user:*` theme and a builtin can share a display name
without stepping on each other, because the id is what gets written to
`active.json`.

Save the file, open **Settings > Themes**, hit `Reload`, click your swatch.
Nothing is installed and nothing is patched into the app: the renderer sets the
properties on `documentElement` for the length of the session.


---

## Where the builtins come from

`_BUILTIN_THEMES` in `zzzcode_app.py` holds 35 rows. Each row is expanded by
`_theme_from_row()` into the full token map that the renderer paints, which is
how a builtin covers every surface while a user file can cover two keys and
still work.

The palette table is data, not code: add a row and the Themes tab grows a
swatch on the next launch. `zzzcode_app.py` has no other theme list.
