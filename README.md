# Opencode-Unlimited-Limit-Bypass-

What it actually does - OpenCode's free limit tracks your IPv6 /64 block and which Cloudflare edge you hit. Opencode Unlimited puts traffic through WARP IPv6, picks random Cloudflare edges, watches `opencode.log` in the background, and automatically grabs a fresh WARP /64 in ~12 seconds when a limit hits. If WARP drops, it fails closed so your real IP doesn't leak.

---

## Requirements

### For Windows App (`ZzZCode.exe`)
- **OS:** Windows 10 or Windows 11 (64-bit)
- **OpenCode:** Official OpenCode Desktop app or OpenCode CLI
- **Cloudflare WARP:** [Cloudflare WARP (1.1.1.1)](https://one.one.one.one/) installed and registered
- **WebView2:** [Microsoft Edge WebView2 Runtime](https://go.microsoft.com/fwlink/p/?LinkId=2124703) (preinstalled on standard Windows 10/11; required for debloated/lite Windows editions)
- *Note:* Python is **NOT required** if you are running the prebuilt `ZzZCode.exe`.

### For Running / Building From Source (Python)
- **Python:** 3.8 to 3.12 (64-bit)
- Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- Build the standalone executable anytime:
  ```powershell
  powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
  ```

### For Linux / WSL2 Users
- Linux x86_64 (native or WSL2)
- systemd & python3
- `sudo` privileges for initial systemd unit registration

---

## How to set it up

### 1. Make sure you have OpenCode & Cloudflare WARP
If you already have OpenCode and Cloudflare WARP (1.1.1.1) installed, you're good. If not:
- Download OpenCode: [opencode.ai](https://opencode.ai)
- Download Cloudflare WARP: [1.1.1.1](https://one.one.one.one/)

### 2. Open the app
1. Run `ZzZCode.exe`.
2. Click **Install / Repair System** at the bottom left.
3. Give it a few seconds. It sets up the background tasks (WARP Keeper + Zen Guard), connects WARP in TUN mode, wires the OpenCode Desktop daemon, and sets up `opencode` in your system `PATH`.
4. *(Optional - not needed if everything works)* If you want the Windows Firewall rule that forces `opencode-cli.exe` to never touch your direct internet, toggle **Firewall Kill-Switch** on and accept the Windows UAC prompt.

### 3. Check that everything is green
- Top right badge should say `PROTECTED • WARP IPv6`.
- Public WARP /64 card should show `CF Verified`.
- **WARP Keeper**, **Zen Guard**, and **Desktop App Proxy** switches should all be **ON**.

---

## Daily use (how to actually run OpenCode)

- **Using the Desktop app:** Click **Launch OpenCode Desktop** in the app (your old chats and projects stay right where they are).
- **Using CLI:** Click **Launch OpenCode CLI**, or open any new terminal and type `opencode`.

### If you hit "Free usage limit reached":
1. Don't close anything. *(If it doesn't work while OpenCode is opened, close OpenCode and then try it).*
2. Wait ~10-15 seconds. Zen Guard catches the error in `opencode.log` and rotates WARP automatically - you'll see the top badge switch to `ROTATING /64...`.
3. Re-send your message.

### Want a new IP/edge manually anytime?
Hit **Rotate /64 Now (Hop)** or **Re-roll** on the Pinned Edge card.

---

## Troubleshooting

- **App opens to a blank / black screen:**
  Your Windows installation is missing the Microsoft Edge WebView2 Evergreen Runtime (common on stripped/custom Windows like AtlasOS, ReviOS, or LTSC).
  Download and install the official runtime: [Microsoft Edge WebView2 Installer](https://go.microsoft.com/fwlink/p/?LinkId=2124703), then re-open the app.
- **Can't connect to internet without the VPN:**
  If you turned on **Firewall Kill-Switch**, Windows blocks `opencode-cli.exe` unless it's routing through the local proxy. You can toggle the Firewall Kill-Switch **OFF** in the app, or use `btnWarpToggle` / disconnect in the UI.
- **Verify health from terminal:**
  You can run a diagnostic health check anytime:
  ```powershell
  .\ZzZCode.exe --doctor
  ```

---

## ZzZ Code (console rebrand)

`ZzZCode.exe` / `ZzZ Code.bat` is a console-only front end that runs the same
WARP + /64 rotation stack and launches a copy of the OpenCode runtime whose
pixel wordmark reads **ZZZCODE**.

**Vanilla guarantee.** Nothing the vendor installed is ever left modified.
Launching `OpenCode.exe` directly, or typing `opencode` in any terminal, gives
the stock app with the stock wordmark. The rebrand only exists while a ZzZ Code
session is running.

- **Where the runtime lives:** `%LOCALAPPDATA%\ZzZCode\bin\zzzcode.exe`. On first
  boot the launcher copies the installed `opencode.exe` into that folder as
  `opencode.exe`, patches the copy, then renames it to `zzzcode.exe`. A crash
  mid-patch therefore never leaves a broken binary under the name the launcher
  runs. The vendor binary is never written to.
- **Boot sequence:** `zzz_intro.py` paints the console in three stages -
  `matrix_rain()` fills the screen with green code rain for 1.9 s, the rain fades,
  then `sweep("MADE BY ZZZ")` draws the block wordmark dark and runs a bright band
  across it left to right before settling on the tinted art. The first menu paint
  then assembles line by line and every later page lands in one write, so
  navigating never replays the animation. `ZZZ_NO_ANIM=1` or a redirected stdout
  (a pipe, a service, CI) skips both animations and prints the same wordmark
  once, plain, with no cursor maths and no sleeps. Each animation also has a hard
  frame cap derived from its duration, so a slow terminal cannot stretch boot into
  a hang, and any exception falls back to the static banner.
- **The console code page is pinned to 65001 before anything is written:**
  `_pin_utf8()` calls `SetConsoleOutputCP` / `SetConsoleCP` first and only then
  reconfigures the streams. Reconciling only `sys.stdout` was not enough - a
  console opened on cp437/cp850/cp1252 still decodes the bytes it receives with
  that page, so every block glyph, bullet and accent arrived as `????`. Colour is
  emitted only when VT is on **and** stdout is a terminal; a redirect gets clean
  text.
- **Menu:** `[1] Launch ZzZ Code` (Desktop or CLI), `[2] Settings` (WARP Keeper,
  Zen Guard, Desktop App Proxy, firewall kill-switch, strict mode, autostart,
  abliterated feed, `[v] Verify stack`), `[3] Status`, `[4] Repair patch`,
  `[5] Doctor`, `[6] Restore vanilla`. Keys are read as single presses through
  `msvcrt.getwch()` on a real console - no Enter - while an unknown key is
  ignored with a short beep instead of repainting the page; piped input falls
  back to line reads so scripts still drive it. Every selection clears the
  console, repaints the cached wordmark, then renders the page beneath it. `c`
  repaints any page.
- **Update detection:** the launcher stores a sha256 of the vendor runtime in
  `~/.zzzcode/state.json`. When the vendor binary changes, the next boot logs
  `Patching Latest Update...` and re-stages from scratch instead of trusting the
  old copy.
- **Desktop wordmark:** applied to the installed `app.asar` at launch and
  restored the moment the app exits (a detached watcher waits on the process
  id). A hard kill leaves it patched; the next boot notices and puts the vendor
  art back. `[6] Restore vanilla`, or `python patch_desktop.py --restore`, does
  the same by hand.
- **Abliterated toggle:** `python patch_gui.py` adds a switch to the right of the
  reasoning-level chip in the chat composer. It is a real
  `<label data-component=switch>` rendered into
  `[data-slot=composer-controls]` as a wide pill: a 36x20 track (1 px
  `--v2-border-border-base` rim, `--v2-background-bg-base` fill, fully rounded)
  with a 14 px round knob that rests 3 px from the left edge when off and travels
  16 px to the right when on, where it takes `--v2-background-bg-accent`. Two
  things are deliberate. **The knob stays a circle:** the vendor's own switch
  rules reach specificity `0,5,0` (`:hover:not([data-disabled],[data-readonly])
  [data-slot=switch-thumb]` squares it to `border-radius:3px;width:13px`, and
  `[data-checked]` pins `border-radius:2px`), so the geometry is declared
  `!important` and reinforced with inline `!important` properties applied by
  `setThumb()` on every state change - the only level those selectors cannot
  outrank. **The label type is borrowed, not guessed:** it is copied property by
  property (`font-family`, `font-size`, `font-weight`, `letter-spacing`,
  `line-height`, `color`, ...) from the composer's model chip via
  `getComputedStyle` longhands, so it matches the app's own type token in every
  theme and cannot drift when the app restyles. State lives in
  `localStorage["zzzcode.abliterated"]`, mirrors onto
  `<html data-zzz-abliterated>`, and is exposed as `window.zzzAbliterated` plus a
  `zzz:abliterated` CustomEvent. Unlike the wordmark this cannot be a
  length-preserving splice, so `patch_gui.py` repacks: changed members are
  appended to the tail of the data blob and their header entries repointed, which
  leaves the other 11 801 members byte-identical and never rewrites the 240 MB
  bundle. `patch_desktop.py --restore` undoes both passes from the pristine
  `.bak`.
- **ZzZ Code settings tabs:** the same payload appends **two** tabs to the
  settings sidebar, using the shell's real contract read out of the bundle -
  `aside.settings-sidebar > .settings-nav > .settings-nav-groups >
  .settings-nav-group` holds one `[data-slot=tabs-v2-trigger-wrapper]` per tab,
  selection paints through `.settings-nav-groups
  [data-slot=tabs-v2-trigger-wrapper]:has([data-selected])`, and panels are
  `.settings-content > .settings-panel` toggled by the `hidden` attribute. Both
  tabs are appended to the last group, and whichever one is selected is rebuilt
  when the shell re-renders. **ZzZ Code** carries **Jailbreak All Opened
  Folders** (posts `{}` to `http://127.0.0.1:47654/jailbreak`, prints the folder
  count under it) plus the whole updates section, below. **Themes** carries the
  palette grid, below.
- **Themes (35 built in, yours allowed):** a theme is a set of CSS custom
  properties painted through one `!important` stylesheet in `<head>` by the
  renderer, not a change to the app's theme store - it outlives every Solid
  re-render and every `<html data-color-scheme>` flip, and the whole thing
  disappears when the session's renderer closes. 35 palettes ship as 16-field
  rows in `_BUILTIN_THEMES`
  (`noir`, `paper`, `solarized-dark`, `solarized-light`, `nord`, `dracula`,
  `gruvbox`, `tokyo-night`, `catppuccin`, `one-dark`, `monokai`, `rose-pine`,
  `everforest`, `kanagawa`, `cyberpunk`, `matrix`, `blood-moon`, `vaporwave`,
  `mint`, `coffee`, `iceberg`, `github-light`, `catppuccin-latte`, `flexoki`,
  `sakura`, `sepia`, `ayu-dark`, `ayu-mirage`, `night-owl`, `material-ocean`,
  `synthwave-84`, `forest`, `midnight-blue`, `amber-crt`, `graphite`), each
  expanded by `_theme_from_row()` into 25 `--v2-*` tokens covering background
  layers, text ramp, borders, icons and the `--v2-blue-*` accent ladder. Your
  own live in `~/.zzzcode/themes/*.json`:
  `{"name": ..., "author": ..., "kind": "dark", "colors": {"--v2-background-bg-base": "#0b0b10"}}`.
  The loader validates every key (`^--[a-zA-Z0-9-]{1,64}$`) and value
  (`^[#a-zA-Z0-9(),.% +-]{1,64}$`), caps 64 files and 256 keys per file, so a
  theme cannot break out of its declaration or smuggle a `url()` into the page.
  A 10 KB guide is written to `~/.zzzcode/themes/README.md` on first run: token
  reference, the layer-stepping method, a dark and a light worked example, a
  troubleshooting table and the loader limits. The tab has
  `Reload`, `Open theme folder`, `New theme file` (writes a full 25-key template)
  and `Default` (drops every override). `POST /themes/apply` persists the choice
  in `~/.zzzcode/themes/active.json`, so the next session repaints itself.
- **Updates are off by default:** `~/.zzzcode/updates.json` holds
  `enabled=false` until **Enable Updates** is flipped in Settings > ZzZ Code.
  With it on, the launcher reads `ZenTheScripter/zzz-code` through the public
  GitHub API and compares the release tag (plus the `main` head commit) and the
  npm `opencode-ai` dist-tag against what it last ran. The `Status:` line in that
  tab says `updates disabled`, `enabled · up to date`, or names what is pending;
  `Check now` forces a refresh (`POST /update/check`), while ordinary reads are
  cached for ten minutes so a renderer poll cannot hammer the API. An empty
  `zzz_commit`/`zzz_tag` is treated as a first run and stamps the baseline
  silently instead of advertising an update on install day. **Auto update**
  applies what it finds at boot. The ZzZ lane prefers a `*.exe` release asset
  (downloaded, then swapped in with a rename dance, since Windows will not let a
  running image be overwritten but will let it be renamed) and falls back to the
  `main` archive staged under `~/.zzzcode/updates/` - copied over the checkout
  when running from source, reported as a path when frozen. The OpenCode lane
  re-stages the vendor runtime through `prepare_runtime(force=True)`, which also
  re-patches the wordmark.
- **One pill, two lanes:** the top-right update pill is ours, not the vendor's,
  and a vendor update button now sits beside a visually distinct ZzZ one. When
  both channels have something pending the pill fuses into a single control -
  `2 updates` - which opens a small dialog with a chooser: **OpenCode**,
  **ZzZ Code**, or **Both**. It polls `GET /update/status` every 90 s and
  targets `POST /update/apply` with `{"target": "zzz" | "opencode" | "both"}`.
- **WARP does not light up at boot any more:** the client service used to start
  at logon and bring the tunnel with it (`Always On: true`). The launcher parks
  it: `sc config CloudflareWARP start= demand`, tunnel disconnected, and a
  `~/.zzzcode/warp_cold` marker that makes `warp_keeper.ensure_connected()` and
  the 45 s probe loop no-ops. `~/.zzzcode/session.active` is written for the
  length of a launch, which reopens the service, the tunnel and the probe; the
  restore watcher clears it and everything parks again. Cold start is the
  default on a fresh install (`cold_seed()`), `Settings [w]` toggles it, and
  switching it off restores `start= auto` and dials the tunnel. The policy needs
  admin once - the first switch raises a single UAC prompt, records the result
  in `state.json`, and never asks again.
- **The park runs after every session, not just at first switch:** the Cloudflare
  client rewrites its own service back to `start= auto` each time it connects, so
  a launch that opens the tunnel leaves the start type warm behind it. `warp_park()`
  (in the CLI lane's `finally`, in `desktop_restore_now()`, and on an aborted
  launch) re-applies the whole cold policy - `sc config ... demand`, tunnel down -
  and `warp_bringup()` is the only thing that opens it. That is what keeps WARP
  dark at the next logon instead of merely dark until the first launch.
  A session that cannot elevate reports `tunnel still up · ...` in one line
  instead of pretending the park landed.
- **Cold start and unelevated launches only coexist because of one service
  grant:** parking the service on demand start makes `sc start CloudflareWARP`
  access-denied (rc 5) for a standard account, so a launcher that had parked the
  tunnel could never reopen it - the launch failed with the tunnel down no matter
  which button was pressed. `warp_grant_user_start()` reads the service DACL with
  `sc sdshow`, appends `(A;;RPWP;;;IU)` to the end of the DACL when it is missing,
  and writes it back with `sc sdset`, scoped to `CloudflareWARP` alone. It needs
  admin once and runs from the elevated lanes (`--warp-cold apply`, `--warp-start`),
  both of which only ever execute from a UAC prompt. After that a cold start is an
  ordinary user operation. `warp_service_start()` now reports
  `sc start access denied (no user grant)` on rc 5 instead of the old
  `WARP service start sent`, and `warp_bringup()` uses `--warp-start` as its UAC
  fallback when the grant is somehow absent.
- **Four egress routes, one config file:** `Settings [e]` picks `warp` (default),
  `tor` (managed portable daemon, SOCKS5 on 9050), `custom` (a proxy list rotated
  per connection, `host:port` or `scheme://host:port`, credentials refused) or
  `clean` (direct). The choice lands in
  `%LOCALAPPDATA%\opencode-unlimited\lane\egress_mode.json` and the keeper
  re-reads it on its next 45 s tick, so a switch needs no restart.
- **`open-source/` is the publishable tree:** the launcher, the three patch
  modules, `recovered_src/` (13 modules), the PyInstaller spec, `build.py`,
  `THEMES.md` and a README that documents the bridge routes, the theme format,
  the egress table and the update lanes. `_sync_opensource.py` rebuilds it and
  fails the sync on a credential-shaped token, a personal path, a foreign credit
  or a renamed-artifact leftover. `python build.py` produces the same
  single-file `dist/ZzZCode.exe`.

- **Toggle drives the feed, not just the pixels:** the payload posts
  `{"enabled": bool}` to `http://127.0.0.1:47654/state`, a loopback bridge the
  launcher binds for the life of a desktop session, and reads the same URL on
  load so a fresh renderer adopts the launcher's truth instead of stale
  `localStorage`. Flipping it off removes the persona entry from the config
  document immediately - no restart, nothing left behind if the app is killed.
  If the console is gone the port is dead and the switch keeps working locally.
- **Abliterated feed** (`Settings [7]`): while the toggle is on, the `AGENTS.md`
  nearest the launch directory is merged into the config document's
  `instructions` array for the duration of the session, so the model has it
  before the first message and it never shows up as a chat part. The previous
  bytes of `~/.config/opencode/opencode.json` are copied aside and restored on
  exit, including when the session is interrupted. No project file is touched.
  Only the entries the launcher added are ever stripped, so a path you listed
  yourself survives the revert. **Toggle off means off:** nothing from the
  persona document is referenced anywhere in the config.
- **The sheet is fetched, never bundled:** the abliterated document is pulled
  from `raw.githubusercontent.com/ZenTheScripter/zzz-code/main/jailbreaks/
  AGENTS.md` (jsDelivr, then `github.com/.../raw`, as fallbacks) the first time it
  is needed, through a proxy-less opener so the fetch cannot loop back into the
  tunnel the launcher is configuring. It is cached at
  `~/.zzzcode/instructions/AGENTS.md` with a 12 h TTL, held as bytes end to end,
  and written into project folders byte-identically. Flipping the composer toggle
  on drops the sheet into the working directory plus the three most recent
  projects, and only where no `AGENTS.md` exists. **Jailbreak All Opened
  Folders** does all of them and overwrites. A folder that already had its own
  `AGENTS.md` keeps the original as `AGENTS.md.zzz.bak` before the first
  overwrite; read-only trees (Steam, Program Files) fail the write and are
  reported, never retried in a loop. Nothing is announced: no chat part, no
  dialog, no file the app opens.
- **"Opened folders" means the databases, not the UI:** `opened_folders()` reads
  `~/.local/share/opencode/opencode.db` and `opencode-local.db` read-only,
  unioning `project.worktree`, `worktree.directory`, `session_v2.directory`,
  `session.directory` and `project_directory.directory` - each table optional,
  because the two files carry different schemas and either can be mid-migration.
  Results are resolved, deduped, capped at 64, and anything under `%TEMP%`/`%TMP%`
  is dropped as probe leftovers. `GET /folders` on the bridge returns the list.
- **First run installs what a fresh machine is missing:** before the menu paints,
  `ensure_prerequisites()` checks `warp-cli.exe` and the Evergreen WebView2
  registration (`EdgeUpdate\Clients\{F3017226-...}`, both hives, plus the
  `EdgeWebView\Application` directories) and installs only what is absent through
  `winget -e --id Cloudflare.Warp` / `Microsoft.EdgeWebView2Runtime --silent
  --disable-interactivity`. The outcome lands in `~/.zzzcode/prereqs.json`; a
  machine that already has both touches nothing, and a failed install is retried
  at most every six hours instead of on every launch. That is what makes the
  build usable on someone else's box rather than only this one.
- **MCP self-setup** (always on, independent of the toggle): every session also
  carries `~/.zzzcode/instructions/mcp-self-setup.md`, which authorises the model
  to install and wire MCP servers on its own. Asked for "roblox studio mcp" (or
  any other server) it resolves the package, searches the web when its own
  knowledge runs out, checks `node`/`npx`/`uv`, merges an entry under the `mcp`
  key of `~/.config/opencode/opencode.json` without touching keys it did not add,
  runs the command once to verify, and reports the exact line plus the single
  step left to you. No clarifying question, no permission prompt. That path is
  also how a Roblox Studio MCP lands in a ZzZ session: an entry under `mcp`
  pointing at whichever Studio MCP proxy is installed on the box, which the app
  picks up on the next restart.
- **The proxy path is verified, not assumed:** `Launch -> Desktop` runs
  `stack_ensure()` before it touches `app.asar` or spawns anything. It brings
  WARP up, starts the keeper and guard, waits for `127.0.0.1:41987`, then runs a
  real end-to-end probe through the proxy: TCP to the listener, `CONNECT`
  `opencode.ai:443`, a TLS handshake with certificate validation, and one HTTP
  request. A bound port is not a working proxy - the old code only checked the
  socket - so a dead edge or a downed tunnel used to launch anyway and quietly
  fall back to direct egress. Now three repair rounds run before giving up:
  re-roll the Cloudflare edge, then `warp-cli connect`, then a full `/64`
  rotation, each followed by the same probe. If it still fails the launch is
  aborted rather than started unproxied. `Settings [v] Verify stack` runs the
  same routine on demand, and `Doctor` prints the probe result instead of
  "listening".
- **Edge failover:** a pinned Cloudflare address that refuses a connect is
  retired into a bad set and the next candidate is tried, up to five, before the
  request fails closed. When every spare is burnt the set is recycled and the
  AAAA pool re-fetched in the background. A fresh registration also drops the
  old edge instead of keeping one pinned across a `/64` change.
- **The rotation only counts when the proxy works:** `hop_once()` now probes the
  lane proxy after each registration and returns a failure if TLS does not
  complete, so the guard no longer logs `rotated ... -> <new /64>` for a hop that
  left the client unable to reach opencode.ai. The guard's before/after readings
  use `get_egress_v6(direct=True)`, which measures the raw WARP egress instead of
  asking the proxy it may be repairing. DoH pool lookups also bypass
  `HTTP(S)_PROXY` now - previously the lookup was routed through our own
  listener and collapsed to the five hardcoded fallbacks whenever the proxy was
  the broken part.
- **Keeper self-heal:** every tick (45 s) the keeper probes the lane proxy. One
  failure re-probes after two seconds; a second failure reconnects WARP. That
  keeps a stale edge or a half-open tunnel from sitting dead until the next
  quota wall.
- **Stale service recycle:** the desktop reuses an already-running
  `opencode-cli serve --service`, which snapshots its environment at spawn time.
  `Launch -> Desktop` stops that process after writing `service.json`, so the
  restarted service actually inherits `HTTPS_PROXY` instead of dialling providers
  directly with the env it was born with.

---

## License
GPL-3.0-or-later, matching the upstream `LICENSE` shipped in this repository.
The launcher, lane proxy, patchers and themes are modifications of the Opencode Unlimited
stack; see `CREDITS.md` for the upstream attribution the GPL requires.
