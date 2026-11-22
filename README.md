# ZzZ Code

A modified OpenCode desktop client for Windows, kept by **ZenZenitoZeno**.

> **Educational and research use only.**
>
> ZzZ Code is a fork published so that the behaviour of an AI coding client can be
> read, studied, audited and experimented with. It is a learning artefact, not a
> product, not a support contract, and not endorsed by or affiliated with Anomaly
> Innovations, the authors of OpenCode.
>
> Read the full notice at the bottom of this file before you run it. It is short and
> it is not decorative.

---

## What it is

`ZzZCode.exe` is a console launcher that stages and runs a private copy of the
OpenCode runtime, keeps a Cloudflare WARP tunnel pinned so the client stops reaching
the provider over your home address, and repaints the desktop app's interface for the
duration of a session — restoring everything it touched the moment you close it.

The vendor install is never the thing that gets modified. The launcher copies the
runtime into its own working directory, works on that copy, and leaves the original
`opencode` binary and the installed desktop app exactly as it found them.

Everything is local. No account, no login, no telemetry, no outbound call to any
server that is not the upstream release feed you explicitly enable.

**Version 1.1.0** · Windows 10/11 · console launcher, single exe · GPL-3.0.

## What is actually in here

| | |
|---|---|
| Themes | **52** built-in palettes, 5 of them with a gradient wash |
| Templates | **12** `AGENTS.md` snippets, appended from the settings panel |
| Launcher version | `1.1.0` |
| Settings surface | a `ZzZ Code` tab and a `Themes` tab inside the app's own Settings |
| Local bridge | `127.0.0.1:47654`, loopback only, alive only while a session runs |
| State directory | `%USERPROFILE%\.zzzcode` |

## Install

1. Download `ZzZCode.exe` and run it. Nothing to install first — WARP and the WebView2
   runtime are pulled in through `winget` if the machine has never had them.
2. Choose **`4` Repair patch** once, or let the first launch do it: that stages the
   runtime, sets up the two background workers, wires the desktop app, and puts
   `opencode` on your `PATH`.
3. Back at the menu, **`1` Launch ZzZ Code** → desktop or CLI.

Keep the folder together if you want the sources beside the exe. The exe alone works
too — the Python modules are frozen inside it.

## The console menu

```
1  Launch ZzZ Code        desktop or CLI
2  Settings               keeper · guard · proxy
3  Status                 tunnel · processes · art
4  Repair patch           restage the runtime
5  Doctor                 diagnostics
6  Restore vanilla        undo every desktop edit
0  Exit                   vendor install untouched
```

### Settings

```
1  WARP Keeper                     keep the tunnel alive
2  Zen Guard                       watch the keeper
3  Desktop App Proxy               route the desktop app through the local listener
4  Firewall kill-switch            block egress when the tunnel drops
5  Strict mode                     refuse to fall back to a direct route
6  Autostart at logon              scheduled tasks for both workers
7  Abliterated (AGENTS.md feed)    opt-in instruction sheet feed
j  Jailbreak all opened folders    fetch the sheet and drop it silently
e  Egress route                    WARP · Tor · custom proxy
w  WARP cold start                 no tunnel at boot
u  Updates                         opt-in, reads this repository's releases
8  Rotate /64 now                  manual hop
9  Re-roll Cloudflare edge         pick a fresh edge
v  Verify stack                    probe and auto-repair
```

`e` opens the egress page: four modes, `t` starts the portable Tor daemon, `p` sets a
`host:port` or `socks5://host:port` proxy, `r` advances the proxy list.

Toggles marked in the settings page apply on the next launch; the workers are live
immediately.

## The two settings tabs

Both tabs live inside the app's own Settings window, next to the vendor tabs. They are
rendered by the launcher's bridge, so they work with the app's existing styling and
disappear cleanly when the session ends.

**ZzZ Code**

- Abliterated — fetches the instruction sheet from this repository and drops it into
  every folder OpenCode has open. Off by default; nothing is injected until you ask.
- Updates — the feed is this repository. The switch is off until you turn it on.
- Diagnostics — version, bundle, Python, bridge port, runtime version, desktop state,
  theme count, worker state, `AGENTS.md` location. `Copy report` puts the whole thing
  on the clipboard as flat `key: value` lines, ready for a bug report. `Crash log`
  opens it, `Clear log` empties it.
- Runtime — `Verify stack` reads WARP, the keeper port and the guard without repairing
  anything; `Restart keeper` stops and starts both workers in order.
- Templates — twelve snippets you can append to a project's `AGENTS.md`, or copy to the
  clipboard. The append is idempotent per heading, so clicking twice does not duplicate.
- A small community link at the bottom. It is a link, it opens in your browser, and it
  does not reappear anywhere else in the window.

**Themes**

- All 52 palettes as swatches, with the wallpaper ones marked.
- A filter box (name or author) and **Surprise me**.
- **Copy palette** dumps the active theme as JSON, ready to paste into a theme file.
- Applying a theme repaints the window immediately and persists across reloads.
- `Esc` closes the tab; `Ctrl/Cmd+Shift+Z` opens or closes the ZzZ Code tab from
  anywhere in the window.

## Themes

Themes are `--v2-*` token sets, not accent swaps: background layers, borders, text,
icons and accent all move together, so a light theme actually reads as light.

A theme file is JSON in `%USERPROFILE%\.zzzcode\themes\`:

```json
{
  "name": "My Theme",
  "author": "you",
  "kind": "dark",
  "wall": "radial-gradient(120% 90% at 15% 0%, #24103f 0%, #0f1117 62%)",
  "colors": {
    "--v2-background-bg-base": "#0f1117",
    "--v2-text-text-base": "#e8e8f0",
    "--v2-background-bg-accent": "#6b46ff"
  }
}
```

- Any `--v2-*` token the bundle declares can be overridden.
- Values are validated against a conservative character set; anything else is dropped.
- `wall` is optional and must be a single `linear-`, `radial-` or `conic-gradient(...)`.
  It is painted as a soft wash above the interface and never eats a click. Anything that
  is not a gradient is ignored, so a typo costs the wash and nothing else.
- The active choice lives in `themes/active.json` and survives a restart.

`THEMES.md` lists every palette with the intent behind it.

## Templates

Twelve `AGENTS.md` snippets, appended straight from the settings panel: focused edits,
verify-before-claiming-done, no new dependencies, small diffs, plan first, no
placeholders, French replies with English code, conventional commits, a security pass, a
performance budget, docs that follow behaviour, and PowerShell 5.1 shell safety.

`python zzzcode_app.py --templates` lists them from the console.

## Command line

```
zzzcode_app.py --version             print the launcher version
zzzcode_app.py --help                list every flag
zzzcode_app.py --doctor              run the diagnostics and exit
zzzcode_app.py --themes              list all theme ids, mark the active one
zzzcode_app.py --theme ember         apply a theme without opening the window
zzzcode_app.py --templates           list the AGENTS.md snippets
zzzcode_app.py --worker keeper|guard run a worker in the foreground
zzzcode_app.py --firewall install|remove
zzzcode_app.py --warp-start          elevate, grant, start the tunnel
zzzcode_app.py --warp-cold apply|auto
zzzcode_app.py --desktop-restore <pid>
```

`--themes` prints one line per theme with a `+wall` marker, so scripting a theme picker
against it is a two-liner.

## Building it yourself

```
python -m pip install -r requirements.txt
python build.py
```

or by hand:

```
python -m PyInstaller --noconfirm build_tmp\ZzZCode.spec
```

Output: `dist/ZzZCode.exe`, console subsystem, no external runtime. See `BUILD.md` for
the flags and what the spec collects.

The tree is flat on purpose: every module sits next to the launcher, `ui/` holds the
Control Center page, `assets/` holds the icon, `jailbreaks/` holds the instruction
sheet. Nothing nested, nothing hidden — you can read the whole thing.

## Layout

```
zzzcode_app.py     the launcher, the bridge, the menus, the themes
zzz_intro.py       console intro, wordmark, menu chrome
zzz_ui.py          Control Center page
zen_guard.py       worker: watches the keeper
zen_lane.py        lane selection
zen_proxy.py       the local listener
warp_keeper.py     WARP supervision
proxy_chain.py     egress chain bookkeeping
tor_manager.py     portable Tor daemon
ouc_common.py      shared helpers
doctor.py          diagnostics
ui/                Control Center HTML
assets/            icon
jailbreaks/        the instruction sheet, fetched at runtime
THEMES.md          every palette and what it is aiming for
CREDITS.md         upstream attribution and what this fork changes
```

## Requirements

```
pywebview >= 5.0.0
pythonnet >= 3.0.0
clr_loader >= 0.2.6
psutil >= 5.9.0
pyinstaller >= 6.0.0     (build only)
```

Windows 10 or 11, x64. Cloudflare WARP is required for the tunnel modes; the launcher
installs it through `winget` if it is missing.

## Known limits

- The local bridge is HTTP on loopback, no auth. Any local process can talk to it while
  a session runs. It is a desktop convenience, not a service.
- Reverse proxies and corporate TLS interception can break the pinned lane. `v` in the
  settings page reports which stage is down.
- Only one desktop session at a time: two instances fight over Electron's cache
  directory.
- `Restore vanilla` is the undo. Use it before uninstalling if you want the desktop app
  byte-identical to what you started with.

---

# Educational and research notice

This repository is published for **study, teaching, auditing and experimentation**.
Please read this before you use it.

**1. It is a research artefact.** ZzZ Code exists so that a real, working AI coding
client can be taken apart and examined: how a desktop client manages state across a
reload, how a settings shell reconciles its DOM, how a theme layer interacts with a
component tree it does not own, how a loopback bridge can mediate between a sandboxed
renderer and a filesystem, how a proxy stack behaves when an edge changes under it.
That is the subject matter. Treat it as a specimen.

**2. It is not a product.** No warranty, no support, no stability promise, no
compatibility guarantee across upstream releases. The app it wraps changes; this fork
follows when someone has time. `GPL-3.0` is the whole of the agreement.

**3. It is not affiliated with anyone upstream.** ZzZ Code is an independent fork.
OpenCode is a project of Anomaly Innovations, Inc. The name, the trademark and the
licence belong to them. Nothing here is endorsed by them, and nothing here speaks for
them. The upstream `LICENSE` is preserved unmodified; the attribution is in
`CREDITS.md` and it stays there.

**4. You are responsible for where you point it.** The launcher provides networking
controls — tunnels, egress routes, a kill-switch, portable Tor. Those are ordinary
systems administration tools, and they are provided so their behaviour can be studied.
What you route through them, on which network, under which terms of service, is your
decision and your liability, not the author's. Do not use this to evade a network policy
you are bound by.

**5. The instruction-sheet feature is an opt-in.** Nothing is injected into your
projects until you explicitly ask for it, with the switch or with `j`. If you enable it,
read what it writes before you work next to it — the point of publishing the sheet in
this repository is that you can read it first.

**6. Privacy.** The launcher writes nothing that leaves the machine. The one outbound
call is the release check, and only after you enable updates. No analytics, no crash
reporting service, no identifier. The crash log is a local file you can open and delete
from the settings panel.

**7. If you are learning, learn here.** The most useful thing in this repository is not
the exe. It is that the whole tree is flat, commented, and readable: a launcher, a
worker pair, a proxy chain, a bridge, a theme engine and a DOM integration layer, each
in one file you can read in a sitting. Break it, rebuild it, prove it wrong. That is
what it is for.

**8. Acceptable use.** Use it on machines you control, on networks you are permitted to
use, and on content you are entitled to work with. Do not redistribute it as if it were
the official client, do not strip the attribution, and do not represent this fork as the
upstream project.

## License and credits

GPL-3.0, same as the upstream this was derived from. `LICENSE` is the original file,
byte for byte, with the upstream notice untouched. `CREDITS.md` names who built the
stack this fork started from and lists every change made on top of it. The credit stays
in the repository — that is how the licence works.

Everything else in here is mine.

— **ZenZenitoZeno**
