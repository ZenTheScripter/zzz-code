# ZzZ Code — open source

A console launcher for the OpenCode runtime. It stages a patched copy of
`opencode.exe`, paints a ZzZ Code wordmark on it, holds the desktop bundle's
wordmark for the length of a session and puts it back on exit, and adds three
things to the app shell through a small renderer payload:

- an **Abliterated** switch in the composer,
- a **ZzZ Code** tab and a **Themes** tab in Settings,
- an update pill with a chooser when more than one update is pending.

Nothing here needs a server, an account, an API key or a build service. Pure
Python standard library plus PyInstaller when you want a single `.exe`.

## What is in the box

```
zzzcode_app.py            console launcher, bridge, themes, updater, cold start
patch_desktop.py          app.asar wordmark: apply / restore lifecycle
patch_gui.py              renderer payload: composer switch, Settings tabs, update pill
patch_opencode.py         thin wrapper around the CLI wordmark patch
zzz_patch.py              length-preserving wordmark patch for opencode.exe
ZzZ Code.bat              double-click launcher (exe if present, script otherwise)
ZzZCode.spec              PyInstaller spec, paths relative to itself
build.py                  one-command build
THEMES.md                 how to write a theme
recovered_src/            WARP keeper, /64 lane proxy, guard, firewall, egress, helpers
```

`recovered_src/` holds the runtime modules the launcher imports:

```
ouc_common.py             paths, process helpers, WARP controls, IPv6 utilities
zen_lane.py               launches opencode through the pinned IPv6 proxy
zen_proxy.py              the CONNECT proxy that carries the lane
zen_guard.py              watches opencode.log and rotates on a limit hit
zen_hop.py                single /64 rotation step
warp_keeper.py            keeps the selected WARP mode up, repairs drops
proxy_chain.py            egress route config: warp / tor / custom / clean
tor_manager.py            managed portable Tor daemon
clean_endpoint.py         direct-egress mode
auto_resume.py            re-launches after a guard rotation
ouc_firewall.py           kill-switch rules
doctor.py                 health check used by `--doctor`
zenzenitozeno_ui.py       the optional Control Center window (WebView2)
ui/index.html             the Control Center markup
```

## Run from source

```
python zzzcode_app.py
```

Python 3.10+. No third-party packages are imported by the console launcher; the
Control Center is the only thing that wants `pywebview` and `psutil`, and it
soft-fails without them.

## Build a standalone exe

```
python -m pip install pyinstaller
python build.py
```

Output lands in `dist/ZzZCode.exe` next to the sources. The spec collects
`recovered_src` as importable modules, so the frozen build needs the folder at
build time only.

## How it stays vanilla

- The CLI is never modified in place: `opencode.exe` is copied to
  `%LOCALAPPDATA%\ZzZCode\bin`, the copy is patched, and that copy is what runs.
- The desktop bundle (`app.asar`) is repacked for the session and restored from
  `app.asar.zzz.bak` when the app exits, or on the next boot if the machine died
  mid-session. A `--desktop-restore <pid>` watcher does the same thing when the
  process disappears.
- `~/.config/opencode/opencode.json` gets an `instructions` entry for the
  session and is written back byte for byte when the session ends.

Running opencode without this launcher is stock opencode: nothing is patched
until a launch, and everything is unpatched after it.

## Themes

Themes are CSS custom-property overrides painted into a single stylesheet in
`<head>` by the renderer payload. They never touch the app's theme store, so
closing the session closes the theme with it.

35 palettes ship in `zzzcode_app.py` (`_BUILTIN_THEMES`). Your own live in
`~/.zzzcode/themes/*.json`:

```json
{
  "name": "Deep Water",
  "author": "me",
  "kind": "dark",
  "colors": {
    "--v2-background-bg-base": "#06121a",
    "--v2-text-text-base": "#d9ecf7",
    "--v2-background-bg-accent": "#1f6f8b"
  }
}
```

The full guide is written to `~/.zzzcode/themes/README.md` on first run and is
also in [THEMES.md](THEMES.md). Open **Settings > Themes**, hit `Reload`, click a
swatch.

## Egress routes

`Settings > Egress route` picks where traffic leaves:

| route | what it does |
| --- | --- |
| `warp` | Cloudflare tunnel, pinned IPv6 lane (default) |
| `tor` | managed portable Tor, SOCKS5 on 9050 |
| `custom` | a proxy list, rotated per connection |
| `clean` | direct egress, no tunnel |

The choice lands in `%LOCALAPPDATA%\opencode-unlimited\lane\egress_mode.json`
and the keeper re-reads it on its next tick, so a switch takes effect without
restarting the stack.

## The lane proxy port

The keeper prefers `41987`, but Windows reserves whole ranges for Hyper-V and
WSL, and a reserved port fails the bind with `WSAEACCES` rather than
`WSAEADDRINUSE`. `ouc_common.service_proxy_port()` probes the remembered
choice, then `41987`, then `51987`, `54987`, `43987`, then an OS-assigned port,
and records the winner in:

```
%LOCALAPPDATA%\opencode-unlimited\lane\proxy_port.txt
```

Everything that needs to reach the proxy reads that file - `stack_ensure`,
`worker_start`, the desktop `service.json` wiring, the Status page and Doctor.
Assuming the constant is what made a keeper serving fine on `51987` look dead on
`41987`, so the launch aborted with `keeper never bound 127.0.0.1:41987`.

## Updates

Updates are off until you flip **Enable Updates** in Settings > ZzZ Code. With it
on, the launcher reads `ZenTheScripter/zzz-code` through the public GitHub API:

- a release asset named `*.exe` is downloaded and swapped in for `ZzZCode.exe`
  (rename dance, the running image is not locked on Windows),
- with no asset, the `main` archive is downloaded and its sources are staged;
  from source they are copied over the checkout, and a frozen build reports the
  staging path so the next build picks them up,
- the vendor runtime is compared against the npm dist-tag (`opencode-ai`) and
  re-staged through the same path the launcher already uses, which also
  re-patches the wordmark.

`Auto update` applies whatever the check finds. `Status:` in the same tab shows
the current state, and `Check now` forces a refresh. Every detected update logs
`Patching Latest Update...` before it touches anything.

The pill in the top-right corner is ours, not the vendor's. One pending update
opens that lane; two pending updates fuse into a single pill that opens a chooser
(OpenCode / ZzZ Code / Both).

## WARP cold start

WARP's client service starts at logon and reconnects because the client reports
`Always On: true`. The launcher flips the service to demand start, keeps a
`~/.zzzcode/warp_cold` marker and parks the keeper while no session is open:

- `~/.zzzcode/warp_cold` — tunnel stays down at boot,
- `~/.zzzcode/session.active` — a launch is holding it open,
- `Settings > WARP cold start` toggles the policy and restores the service to
  automatic start when switched off.

A launch starts the service and connects; the restore watcher clears the session
marker and the tunnel parks again.

Boot only corrects the start type, never the tunnel. The Cloudflare client
rewrites its own service back to automatic on every connect, so a boot that
treated `start type != demand` as "park it" disconnected the user on every
launch; `warp_cold_apply(stop=False)` fixes the type and leaves a live tunnel
alone, and only `warp_park()` - the end of a session - disconnects. The policy needs admin once: the first switch
raises a single UAC prompt, records the result in `state.json`, and never asks
again.

## The bridge

The renderer has no filesystem access, so the launcher exposes a loopback-only
HTTP bridge on `127.0.0.1:47654` for the life of a desktop session:

| method | route | purpose |
| --- | --- | --- |
| GET | `/state` | persona feed on/off |
| GET | `/folders` | folders opencode has open |
| POST | `/state` | flip the persona feed |
| POST | `/jailbreak` | drop the instruction sheet into every open folder |
| GET | `/themes` | palettes + active id |
| POST | `/themes/apply` | apply a palette |
| POST | `/themes/reset` | back to the vendor theme |
| POST | `/themes/open` | open the themes folder |
| POST | `/themes/new` | write a template theme |
| GET | `/update/status` | update state |
| POST | `/update/check` | force a refresh |
| POST | `/update/enable` | updates on/off |
| POST | `/update/auto` | auto apply on/off |
| POST | `/update/apply` | apply `zzz`, `opencode` or `both` |

Every route is best-effort from the renderer's side: a dead bridge leaves the
switches usable and the launcher's own console menus authoritative.

## Prerequisites

First run installs what is missing through `winget`: Cloudflare WARP and the
WebView2 runtime. Both are checked before the menu paints and the check is
cached in `~/.zzzcode/prereq.json`.

## Layout the launcher expects

```
ZzZCode.exe | zzzcode_app.py
patch_desktop.py   patch_gui.py   zzz_patch.py
recovered_src/*.py
```

State lives under `%LOCALAPPDATA%\ZzZCode` (staged binaries) and `~/.zzzcode`
(markers, themes, update stamps).

## Notice

ZzZ Code is a modified build of OpenCode, for research use only. OpenCode is a
separate project by Anomaly Innovations, Inc.; this repository ships no vendor
code and claims no affiliation with it.
