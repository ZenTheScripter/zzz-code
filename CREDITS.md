# Credits and upstream attribution

ZzZ Code is a modified distribution of the **Opencode Unlimited** control stack
(`ZenTheScripters`), which orchestrates Cloudflare WARP, IPv6 identity rotation and the
local OpenCode Desktop/CLI daemon on Windows.

- Upstream project: Opencode Unlimited v3.0, by ZenTheScripter (ZenZenitoZeno)
- Upstream license: GNU General Public License v3.0 - the `LICENSE` file in this
  repository is the upstream copy and is not modified
- This repository: GPL-3.0-or-later, as required by the upstream license
- OpenCode itself is a separate project by Anomaly Innovations, Inc. Its name and
  trademark belong to them; this fork is not affiliated with them and speaks for nobody
  upstream.

## What this distribution changes

- Launcher (`zzzcode_app.py`) rewritten around a staged-copy model: `ZzZCode.exe` runs a
  private copy of the runtime and never touches the vendor install. The desktop app's
  renderer is repainted for the duration of a session only, and restored on exit.
- Lane proxy port is discovered instead of hard-coded (probe, remembered value, then
  OS-assigned fallback), because `41987` collides with a Hyper-V excluded range on some
  machines.
- WARP cold start no longer kills a live tunnel; parking is explicit.
- Theme engine rewritten around `--v2-*` token sets: **52 built-in palettes**, optional
  gradient washes, user theme files, live filtering and palette export.
- Settings surface: a `ZzZ Code` tab and a `Themes` tab inside the app's own settings
  window, driven by a loopback bridge rather than a custom window.
- Diagnostics: stack verification, worker restart, crash log handling and a copyable
  report, all from the settings panel.
- `AGENTS.md` template pack: 12 snippets, appended idempotently from the panel.
- Opt-in updater pointed at this repository, with a single update control.
- Console intro, Matrix rain, ASCII wordmark and animated menu.

No upstream notice, copyright line or license text was removed.
