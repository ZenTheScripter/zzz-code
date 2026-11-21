# Building the standalone ZzZ Code launcher

```
python -m pip install pyinstaller
python build.py
```

`build.py` runs PyInstaller against `ZzZCode.spec`, which resolves every path
relative to itself, so the tree can be cloned anywhere.

Output: `dist/ZzZCode.exe`, ~11 MB, console subsystem, no external runtime.

## Flags

```
python build.py --clean      remove build/ and dist/ first
python build.py --onedir     folder build instead of a single file
```

## What the spec collects

- `zzzcode_app.py` as the entry script,
- `pathex` = this folder (every module sits next to the launcher),
- `hiddenimports` for every module the launcher imports lazily
  (`warp_keeper`, `zen_guard`, `zen_lane`, `zen_proxy`, `ouc_common`,
  `ouc_firewall`, `zen_hop`, `doctor`, `zzz_patch`, `patch_desktop`,
  `patch_gui`).

Nothing is downloaded at build time and no code signing step is included.
