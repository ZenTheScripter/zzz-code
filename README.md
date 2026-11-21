# ZzZ Code

This my modded, open source, OpenCode Client ! It has a abliterated button (to
jailbreak the ai), custom themes, many other quality updates.

ZzZ CODE -> BEST MODDED OPENCODE CLIENT it contains, jailbreak, custom themes and
a ton of stuff..

---

## what it is

`ZzZCode.exe` sits in front of OpenCode and does the annoying parts for you. It
keeps Cloudflare WARP up, pins your exit so the CLI stops hitting the provider
directly, patches the Desktop app while a session runs and puts it back the moment
you close it. Everything is local, nothing phones home, no account, no login.

The console thing is mine too, that's the matrix rain and the big ASCII wordmark
before the menu.

## the abliterated button

That's the whole point of this fork. In the menu, `7` fetches the instruction sheet
from this very repo (`jailbreaks/AGENTS.md`), and `j` drops it as `AGENTS.md` into
every folder OpenCode has open, silently. Next session your AI is off the leash,
no copy pasting, no "please act as".

Your own folders, your own client, your own rules.

## themes

35 themes, Settings > Themes. They repaint the whole client, not just the accent
color, and the list is written down in `THEMES.md` with what each one is aiming
for. Pick one, restart, done.

## updates

Settings > ZzZ Code. The updater reads releases from this repo
(`ZenTheScripter/zzz-code`), so whatever is pushed here is what you get. The
`Enable Updates` switch is off until you turn it on, because the client you
downloaded works and I'm not going to replace it behind your back.

`Patching Latest Update...` in the log means it found something and is applying it.

## how to run it

1. Grab `ZzZCode.exe` and run it. Windows, nothing to install first, WARP and the
   WebView2 runtime get pulled in through winget if the machine never had them.
2. Click **Install / Repair System** bottom left. That sets up the background
   workers, wires the Desktop app, puts `opencode` in your PATH.
3. Menu. `1` opens OpenCode, `7` jailbreaks, `s` settings, `q` quits.

Keep the folder intact if you want the source next to the exe. The exe alone works
too, the modules are frozen inside it.

## building it yourself

```
python -m pip install -r requirements.txt
python build.py
```

or by hand:

```
python -m PyInstaller --noconfirm build_tmp\ZzZCode.spec
```

The tree is flat on purpose: every module sits next to the launcher, `ui/` has the
Control Center page, `assets/` has the icon, `jailbreaks/` has the sheet. Nothing
nested, nothing hidden, you can read the whole thing.

## license / credits

GPL-3.0, same as the upstream this was recovered from. `LICENSE` is the original
file, `CREDITS.md` says who made the stack I started from and what I changed. The
credit stays in the repo, that's how the license works.

Everything else in here is mine.
