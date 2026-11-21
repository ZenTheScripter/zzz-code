# Credits and upstream attribution

ZzZ Code is a modified distribution of the **Opencode Unlimited** control stack
(`ShadowySphinX`), which orchestrates Cloudflare WARP, IPv6 identity rotation and the
local OpenCode Desktop/CLI daemon on Windows.

- Upstream project: Opencode Unlimited v3.0, by ShadowySphinX (ZenZenitoZeno)
- Upstream license: GNU General Public License v3.0 — the `LICENSE` file in this
  repository is the upstream copy and is not modified
- This repository: GPL-3.0-or-later, as required by the upstream license

## What this distribution changes

- Launcher (`zzzcode_app.py`) rewritten around a staged-copy model: `ZzZCode.exe`
  patches a copy, never the vendor install, and the Desktop `app.asar` is patched for
  the duration of a session only, then restored.
- Lane proxy port is discovered instead of hard-coded (probe, remembered value, then
  OS-assigned fallback), because `41987` collides with a Hyper-V excluded range on
  some machines.
- WARP cold start no longer kills a live tunnel; parking is explicit.
- Theme pack (35 themes) and the Settings guide.
- Opt-in updater pointed at this repository, with a fused update button.
- Console intro, Matrix rain, ASCII wordmark and animated menu.

Modified files remain under GPL-3.0. No upstream notice, copyright line or license
text was removed.
