#!/usr/bin/env python3
"""Add the `Abliterated` switch and the `ZzZ Code` settings tab to OpenCode Desktop.

The renderer is a Vite bundle inside `app.asar`; the composer toolbar is built
from `[data-slot=composer-controls]` and the reasoning-level chip sits in the
inner flex row. The control this module adds is a DOM node, so the bundle has to
grow - unlike the wordmark work in `patch_desktop.py`, this is not a
length-preserving splice.

Nothing is rewritten in place. The asar header is re-serialised and the data
section is carried over verbatim:

    * two members are (re)written at the end of the data section
      (`out/renderer/index.html` gains a script tag, `out/renderer/assets/
      zzz-gui.js` is the payload)
    * every untouched member keeps its original offset, because offsets are
      relative to the start of the data section and that block never moves
    * the three header words are recomputed from the new JSON length

The toggle is a real `<label data-component=switch>`, so it inherits the app's
own switch styling - `--v2-background-bg-accent` when on, layer-04 when off,
`--v2-text-text-muted` for the label - and flips with the light/dark theme
without a second stylesheet. State lives in `localStorage["zzzcode.abliterated"]`
and mirrors onto `<html data-zzz-abliterated>`, so other hooks can read it.

Two vendor details shape the payload:

    * the bundled switch rules reach specificity `0,5,0` - the hover rule is
      `:hover:not([data-disabled],[data-readonly]) [data-slot=switch-thumb]` -
      so a scoped rule cannot keep the knob round. Geometry is declared
      `!important` and reinforced inline by `setThumb()`, which is the only
      declaration level those selectors cannot outrank.
    * the label type is *borrowed* from the composer's model chip at runtime
      through `getComputedStyle` longhands, not hardcoded, so it follows the
      app's own type token and cannot drift when the app restyles.

The settings tab is injected into the shell's real contract, read out of the
bundle: `aside.settings-sidebar > .settings-nav > .settings-nav-groups >
.settings-nav-group` holds one `[data-slot=tabs-v2-trigger-wrapper]` per tab,
selection paints through `:has([data-selected])`, and panels are
`.settings-content > .settings-panel` toggled by the `hidden` attribute. The tab
is appended to the last group and its panel rebuilt whenever the shell re-renders
while the tab is selected. It carries a single action, `Jailbreak All Opened
Folders`, which posts to the launcher's loopback bridge.

     python patch_gui.py --check
     python patch_gui.py

Undo is `python patch_desktop.py --restore`, which copies the pristine bundle
back over both patches.
"""

from __future__ import annotations

import json
import re
import struct
import sys
import zlib
from pathlib import Path

from patch_desktop import ASCENDER, ASAR, BACKUP, GLYPHS, asar_base

INDEX_MEMBER = "/out/renderer/index.html"
GUI_MEMBER = "/out/renderer/assets/zzz-gui.js"
SCRIPT_TAG = b'<script src="./assets/zzz-gui.js"></script>'
SHARE_MEMBER = "/out/renderer/assets/social-share-zzz.png"
ICON_SVG_MEMBER = "/out/renderer/assets/favicon-zzz.svg"
ICON_PNG_MEMBER = "/out/renderer/assets/favicon-zzz-96.png"

# ---------------------------------------------------------------- renderer payload
#
# Loaded as a classic script so it does not need module/CORS plumbing. It waits
# for the composer row, appends the switch, and re-appends it whenever Solid
# replaces the subtree; the switch is idempotent because it is keyed by
# `data-slot`. Comments stay out of the payload: it ships to the page verbatim.
GUI_JS = r"""(function () {
  "use strict";
  var KEY = "zzzcode.abliterated";
  var SLOT = "zzz-abliterated";
  var HOST = '[data-slot="composer-controls"] > div';
  var ROOT = document.documentElement;

  // The launcher owns the actual injection: it merges the instruction entries
  // into `~/.config/opencode/opencode.json` for the session. The renderer cannot
  // touch files, so the switch talks to the launcher's loopback bridge. Port is
  // fixed and the bridge is only up while a ZzZ desktop session runs; every call
  // is best-effort, so a dead bridge leaves the switch usable.
  var BRIDGE = "http://127.0.0.1:47654";
  var STATE = BRIDGE + "/state";
  var JAILBREAK = BRIDGE + "/jailbreak";
  var UPD_STATUS = BRIDGE + "/update/status";
  var THEMES = BRIDGE + "/themes";
  var THEMES_APPLY = THEMES + "/apply";
  var THEMES_RESET = THEMES + "/reset";
  var THEMES_OPEN = THEMES + "/open";
  var THEMES_NEW = THEMES + "/new";
  var UPD_ENABLE = BRIDGE + "/update/enable";
  var UPD_AUTO = BRIDGE + "/update/auto";
  var UPD_CHECK = BRIDGE + "/update/check";
  var UPD_APPLY = BRIDGE + "/update/apply";
  var DIAG = BRIDGE + "/diagnostics";
  var CRASH_OPEN = BRIDGE + "/crash/open";
  var CRASH_CLEAR = BRIDGE + "/crash/clear";
  var STACK_VERIFY = BRIDGE + "/stack/verify";
  var WORKERS_RESTART = BRIDGE + "/workers/restart";
  var TEMPLATES = BRIDGE + "/templates/list";
  var TEMPLATE_SAVE = BRIDGE + "/templates/save";
  var THEME_KEY = "zzz.theme.id";

  // Small shared surfaces. A toast is one reused node so spamming an action never
  // stacks pills up the screen; the clipboard helper falls back to a hidden
  // textarea because `navigator.clipboard` is undefined on a non-secure origin.
  function toast(text) {
    var node = document.querySelector("[data-zzz-toast]");
    if (!node) {
      node = document.createElement("div");
      node.setAttribute("data-zzz-toast", "");
      (document.body || ROOT).appendChild(node);
    }
    node.textContent = String(text || "");
    node.setAttribute("data-show", "");
    window.clearTimeout(node.__zzzTimer);
    node.__zzzTimer = window.setTimeout(function () {
      node.removeAttribute("data-show");
    }, 1800);
  }

  function copyText(text) {
    var done = function (ok) {
      return ok;
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      return navigator.clipboard.writeText(text).then(function () {
        return done(true);
      }, function () {
        return done(fallbackCopy(text));
      });
    }
    return Promise.resolve(done(fallbackCopy(text)));
  }

  function fallbackCopy(text) {
    try {
      var area = document.createElement("textarea");
      area.value = text;
      area.style.position = "fixed";
      area.style.opacity = "0";
      area.style.pointerEvents = "none";
      (document.body || ROOT).appendChild(area);
      area.select();
      var ok = document.execCommand("copy");
      area.remove();
      return !!ok;
    } catch (err) {
      return false;
    }
  }

  // The vendor switch is `[data-component=switch]` with a 24x16 track and a
  // 12px square thumb (border-radius:2px, 3px on hover, translate(8px) when
  // checked). Those selectors reach 0,5,0 - `:hover:not([data-disabled],
  // [data-readonly]) [data-slot=switch-thumb]` - so a plain scoped rule cannot
  // beat them and the knob visibly squares off on click. The geometry below is
  // declared `!important` and the thumb also carries inline `!important`
  // geometry (see setThumb), which outranks every stylesheet.
  //
  // Geometry: 36x20 track, 1px border + 2px padding either side leaves a 30px
  // inner lane, so a 14px knob travels 16px between the two rests.
  var STYLE = [
    'html [data-slot="' + SLOT + '"]{gap:7px;padding:0 2px;margin-inline-start:4px}',
    'html [data-slot="' + SLOT + '"] [data-slot=switch-label]{white-space:nowrap;opacity:1}',
    'html [data-slot="' + SLOT + '"] [data-slot=switch-control]{box-sizing:border-box!important;width:36px!important;height:20px!important;padding:2px!important;border:1px solid var(--v2-border-border-base)!important;border-radius:999px!important;background:var(--v2-background-bg-base)!important;box-shadow:inset 0 1px 2px rgba(0,0,0,.07)!important;transition:background 140ms ease,border-color 140ms ease}',
    'html [data-slot="' + SLOT + '"] [data-slot=switch-thumb]{box-sizing:border-box!important;width:14px!important;height:14px!important;min-width:14px!important;max-width:14px!important;min-height:14px!important;max-height:14px!important;aspect-ratio:1/1!important;flex:0 0 auto!important;border:0!important;border-radius:50%!important;background:var(--v2-text-text-base)!important;box-shadow:0 1px 2px rgba(0,0,0,.3)!important;transform:translateX(0)!important;transition:transform 140ms ease,background 140ms ease!important}',
    'html [data-slot="' + SLOT + '"]:hover [data-slot=switch-thumb]{width:14px!important;height:14px!important;border-radius:50%!important;transform:translateX(0)!important}',
    'html [data-slot="' + SLOT + '"][data-checked] [data-slot=switch-control]{border-color:var(--v2-border-border-strong)!important;background:var(--v2-background-bg-base)!important}',
    'html [data-slot="' + SLOT + '"][data-checked] [data-slot=switch-thumb]{background:var(--v2-background-bg-accent)!important;transform:translateX(16px)!important}',
    'html [data-slot="' + SLOT + '"][data-checked]:hover [data-slot=switch-thumb]{transform:translateX(16px)!important}',
    'html [data-slot="' + SLOT + '"]:dir(rtl)[data-checked] [data-slot=switch-thumb]{transform:translateX(-16px)!important}',
    'html [data-zzz-tab] [data-slot=tabs-v2-trigger]{display:flex;align-items:center;gap:6px;width:100%;height:100%;padding:0 6px;border:0;background:none;color:inherit;font:inherit;text-align:start;cursor:inherit}',
    'html [data-zzz-nav]{display:flex;flex-direction:column;gap:1px;margin-top:6px;padding-top:8px;border-top:1px solid var(--v2-border-border-base)}',
    'html [data-zzz-nav-label]{padding:2px 8px 4px;font-size:10px;line-height:14px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--v2-text-text-faint)}',
    'html [data-zzz-nav] [data-slot=tabs-v2-trigger-wrapper]{border-radius:6px}',
    'html [data-zzz-nav] [data-slot=tabs-v2-trigger-wrapper]:has([data-selected]){background:var(--v2-background-bg-layer-03);color:var(--v2-text-text-base)}',
    'html [data-zzz-nav] [data-slot=tabs-v2-trigger-wrapper]:not(:has([data-selected])):hover{background:var(--v2-overlay-simple-overlay-hover)}',
    'html[data-zzz-sheet-open] .settings-nav-groups [data-slot=tabs-v2-trigger-wrapper]:has([data-selected]){background:transparent!important;color:var(--v2-text-text-muted)!important}',
    'html [data-zzz-sheet]{box-sizing:border-box;position:fixed;z-index:40;display:none;flex-direction:column;overflow-y:auto;padding:6px 8px 18px;background:var(--v2-background-bg-base);scrollbar-width:none}',
    'html [data-zzz-sheet][data-open]{display:flex}',
    'html [data-zzz-sheet]::-webkit-scrollbar{display:none}',
    'html [data-zzz-sheet]>.settings-panel{height:auto;min-height:0;flex:0 0 auto;overflow:visible;padding-inline:0}',
    'html [data-zzz-search]{height:30px;padding:0 10px;border:1px solid var(--v2-border-border-base);border-radius:6px;background:var(--v2-background-bg-layer-01);color:var(--v2-text-text-base);font:inherit;font-size:12px;width:100%}',
    'html [data-zzz-search]:focus{outline:none;border-color:var(--v2-border-border-focus)}',
    'html [data-zzz-banner]{display:flex;align-items:center;gap:9px;padding:9px 11px;border:1px solid var(--v2-border-border-base);border-radius:8px;background:var(--v2-background-bg-layer-01);text-decoration:none;color:var(--v2-text-text-base)}',
    'html [data-zzz-banner]:hover{background:var(--v2-background-bg-layer-02);border-color:var(--v2-border-border-strong)}',
    'html [data-zzz-banner] b{font-size:12px;font-weight:600}',
    'html [data-zzz-banner] span{font-size:11px;line-height:15px;color:var(--v2-text-text-faint)}',
    'html [data-zzz-banner-mark]{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;border-radius:7px;background:var(--v2-background-bg-accent);color:var(--v2-text-text-contrast);font-size:12px;font-weight:700;flex:0 0 auto}',
    'html [data-zzz-template]{display:flex;flex-direction:column;gap:4px;padding:8px 0;border-bottom:1px solid var(--v2-border-border-base)}',
    'html [data-zzz-template]:last-child{border-bottom:0}',
    'html [data-zzz-template-head]{display:flex;align-items:center;justify-content:space-between;gap:10px}',
    'html [data-zzz-template-name]{font-size:12px;font-weight:550;color:var(--v2-text-text-base)}',
    'html [data-zzz-template-note]{font-size:11px;line-height:15px;color:var(--v2-text-text-faint)}',
    'html [data-zzz-kbd]{display:inline-block;padding:1px 5px;border:1px solid var(--v2-border-border-base);border-radius:4px;font-family:ui-monospace,monospace;font-size:10px;color:var(--v2-text-text-muted)}',
    'html [data-zzz-toast]{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);z-index:2147483002;padding:8px 14px;border:1px solid var(--v2-border-border-strong);border-radius:999px;background:var(--v2-background-bg-layer-02);color:var(--v2-text-text-base);font-size:12px;box-shadow:0 10px 30px rgba(0,0,0,.32);opacity:0;transition:opacity 140ms ease}',
    'html [data-zzz-toast][data-show]{opacity:1}',
    'html [data-zzz-tab] [data-slot=tabs-v2-trigger] svg{flex:0 0 auto}',
    'html [data-zzz-panel]{display:flex!important;flex-direction:column;gap:14px;min-height:0;overflow-y:auto}',
    'html [data-zzz-panel][hidden]{display:none!important}',
    'html [data-zzz-action]{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:30px;padding:0 12px;border:1px solid var(--v2-border-border-base);border-radius:6px;background:var(--v2-background-bg-layer-02);color:var(--v2-text-text-base);font:inherit;font-weight:500;cursor:pointer;transition:background 120ms ease,border-color 120ms ease,opacity 120ms ease}',
    'html [data-zzz-action]:hover:not([disabled]){background:var(--v2-background-bg-layer-03);border-color:var(--v2-border-border-strong)}',
    'html [data-zzz-action][disabled]{opacity:.55;cursor:default}',
    'html [data-zzz-status]{font-size:12px;line-height:16px;color:var(--v2-text-text-muted);min-height:16px}',
    'html [data-zzz-switch]{display:flex;align-items:center;gap:8px;flex:0 0 auto;cursor:pointer;font:inherit;color:var(--v2-text-text-base)}',
    'html [data-zzz-switch] [data-slot=switch-label]{white-space:nowrap;opacity:1}',
    'html [data-zzz-switch] [data-slot=switch-control]{box-sizing:border-box!important;width:36px!important;height:20px!important;padding:2px!important;border:1px solid var(--v2-border-border-base)!important;border-radius:999px!important;background:var(--v2-background-bg-base)!important;transition:background 140ms ease,border-color 140ms ease}',
    'html [data-zzz-switch] [data-slot=switch-thumb]{box-sizing:border-box!important;width:14px!important;height:14px!important;min-width:14px!important;max-width:14px!important;min-height:14px!important;aspect-ratio:1/1!important;flex:0 0 auto!important;border:0!important;border-radius:50%!important;background:var(--v2-text-text-muted)!important;transition:transform 140ms ease,background 140ms ease!important}',
    'html [data-zzz-switch][data-checked] [data-slot=switch-thumb]{background:var(--v2-background-bg-accent)!important}',
    'html [data-zzz-switch][data-checked] [data-slot=switch-control]{border-color:var(--v2-border-border-strong)!important}',
    'html [data-zzz-row]{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:7px 0}',
    'html [data-zzz-row] [data-zzz-copy]{display:flex;flex-direction:column;gap:2px;min-width:0}',
    'html [data-zzz-row] [data-zzz-title]{font-size:13px;line-height:18px;font-weight:500;color:var(--v2-text-text-base)}',
    'html [data-zzz-hint]{font-size:11px;line-height:15px;color:var(--v2-text-text-faint)}',
    'html [data-zzz-section]{display:flex;flex-direction:column;gap:8px;padding:10px 0 14px;border-bottom:1px solid var(--v2-border-border-base)}',
    'html [data-zzz-section]:last-child{border-bottom:0}',
    'html [data-zzz-grid]{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:8px;padding-top:4px}',
    'html [data-zzz-swatch]{display:flex;flex-direction:column;gap:6px;padding:7px;border:1px solid var(--v2-border-border-base);border-radius:8px;background:var(--v2-background-bg-layer-01);cursor:pointer;text-align:start;font:inherit;color:inherit;transition:border-color 120ms ease,transform 120ms ease}',
    'html [data-zzz-swatch]:hover{border-color:var(--v2-border-border-strong);transform:translateY(-1px)}',
    'html [data-zzz-swatch][data-active]{border-color:var(--v2-border-border-focus);box-shadow:0 0 0 1px var(--v2-border-border-focus) inset}',
    'html [data-zzz-swatch-preview]{display:flex;flex-direction:column;gap:3px;height:40px;padding:5px;border-radius:5px;overflow:hidden}',
    'html [data-zzz-swatch-preview] span{display:block;height:4px;border-radius:2px}',
    'html [data-zzz-swatch-name]{font-size:11px;line-height:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
    'html [data-zzz-pill]{position:relative;flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;height:20px;padding:0 8px;margin-inline-end:8px;border:1px solid var(--v2-border-border-strong);border-radius:999px;background:var(--v2-background-bg-deep);color:var(--v2-icon-icon-accent);font:inherit;font-size:11px;font-weight:530;line-height:16px;white-space:nowrap;cursor:pointer;-webkit-app-region:no-drag;app-region:no-drag;transition:background 120ms ease}',
    'html [data-zzz-pill]:hover{background:var(--v2-background-bg-layer-03)}',
    'html [data-zzz-pill][data-fixed]{position:fixed;top:8px;right:150px;z-index:2147483000;box-shadow:0 6px 18px rgba(0,0,0,.22)}',
    'html [data-zzz-pill] i{display:block;width:7px;height:7px;border-radius:50%;background:currentColor;flex:0 0 auto}',
    'html [data-zzz-overlay]{position:fixed;inset:0;z-index:2147483001;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.42);backdrop-filter:blur(2px)}',
    'html [data-zzz-dialog]{width:340px;max-width:calc(100vw - 32px);display:flex;flex-direction:column;gap:12px;padding:16px;border:1px solid var(--v2-border-border-strong);border-radius:12px;background:var(--v2-background-bg-layer-01);color:var(--v2-text-text-base);box-shadow:0 24px 64px rgba(0,0,0,.45)}',
    'html [data-zzz-dialog] h3{margin:0;font-size:14px;font-weight:600}',
    'html [data-zzz-dialog] p{margin:0;font-size:11px;line-height:15px;color:var(--v2-text-text-muted)}',
    'html [data-zzz-choice]{display:flex;align-items:center;gap:9px;padding:8px 10px;border:1px solid var(--v2-border-border-base);border-radius:8px;background:var(--v2-background-bg-layer-02);cursor:pointer;font-size:12px}',
    'html [data-zzz-choice][data-selected]{border-color:var(--v2-border-border-focus);background:var(--v2-background-bg-layer-03)}',
    'html [data-zzz-choice] input{margin:0}',
    'html [data-zzz-actions]{display:flex;justify-content:flex-end;gap:8px}'
  ].join("");

  // Longhands only: Chromium does not round-trip the `font` shorthand through
  // getComputedStyle, so the chip's type is copied property by property.
  var TYPE_PROPS = [
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "font-stretch",
    "font-variation-settings",
    "font-feature-settings",
    "letter-spacing",
    "line-height",
    "text-transform",
    "color"
  ];

  var enabled = false;
  try {
    enabled = window.localStorage.getItem(KEY) === "1";
  } catch (err) {
    enabled = false;
  }

  function injectStyle() {
    if (document.getElementById("zzz-abliterated-style")) return;
    var tag = document.createElement("style");
    tag.id = "zzz-abliterated-style";
    tag.textContent = STYLE;
    (document.head || ROOT).appendChild(tag);
  }

  function reflect() {
    ROOT.setAttribute("data-zzz-abliterated", enabled ? "1" : "0");
    var nodes = document.querySelectorAll('[data-slot="' + SLOT + '"]');
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      var box = node.querySelector('[data-slot="switch-input"]');
      if (box) box.checked = enabled;
      if (enabled) node.setAttribute("data-checked", "");
      else node.removeAttribute("data-checked");
      var thumb = node.querySelector('[data-slot="switch-thumb"]');
      if (thumb) setThumb(thumb, enabled);
    }
  }

  // Inline `!important` geometry is the only thing the vendor's hover and
  // checked rules cannot outrank, so the knob stays a circle on every state.
  function setThumb(thumb, on) {
    thumb.style.setProperty("box-sizing", "border-box", "important");
    thumb.style.setProperty("width", "14px", "important");
    thumb.style.setProperty("height", "14px", "important");
    thumb.style.setProperty("min-width", "14px", "important");
    thumb.style.setProperty("min-height", "14px", "important");
    thumb.style.setProperty("aspect-ratio", "1 / 1", "important");
    thumb.style.setProperty("flex", "0 0 auto", "important");
    thumb.style.setProperty("border", "0", "important");
    thumb.style.setProperty("border-radius", "50%", "important");
    thumb.style.setProperty(
      "transform",
      on ? "translateX(16px)" : "translateX(0px)",
      "important"
    );
    thumb.style.setProperty("transition", "transform 140ms ease,background 140ms ease", "important");
  }

  // Typography is borrowed from the composer's model chip rather than hardcoded:
  // the chip carries the app's own type token, so the label matches it exactly in
  // every theme without this payload knowing the token's name.
  function chipCandidate() {
    var row = document.querySelector(HOST);
    if (!row) return null;
    var nodes = row.querySelectorAll('button, [data-component="button-v2"], [role="button"]');
    var best = null;
    var bestScore = 0;
    for (var i = 0; i < nodes.length; i += 1) {
      var node = nodes[i];
      if (node.closest('[data-slot="' + SLOT + '"]')) continue;
      var text = (node.textContent || "").trim();
      if (!text || text.length > 40) continue;
      var score = 1;
      if (/free|flash|pro|mini|max|opus|sonnet|haiku|gpt|claude|gemini|deepseek|kimi|grok|llama|qwen|mistral/i.test(text)) {
        score += 4;
      }
      if (text.length >= 6) score += 1;
      if (node.getBoundingClientRect().width > 0) score += 1;
      if (score > bestScore) {
        bestScore = score;
        best = node;
      }
    }
    return best;
  }

  function adoptChipType() {
    var chip = chipCandidate();
    if (!chip) return;
    var computed = window.getComputedStyle(chip);
    var stamp = computed.fontSize + "|" + computed.fontWeight + "|" + computed.fontFamily;
    var labels = document.querySelectorAll('[data-slot="' + SLOT + '"] [data-slot=switch-label]');
    for (var i = 0; i < labels.length; i += 1) {
      var label = labels[i];
      if (label.getAttribute("data-zzz-type") === stamp) continue;
      for (var j = 0; j < TYPE_PROPS.length; j += 1) {
        var value = computed.getPropertyValue(TYPE_PROPS[j]);
        if (value) label.style.setProperty(TYPE_PROPS[j], value);
      }
      label.style.setProperty("opacity", "1");
      label.setAttribute("data-zzz-type", stamp);
    }
  }

  function persist() {
    try {
      window.localStorage.setItem(KEY, enabled ? "1" : "0");
    } catch (err) {
      return;
    }
  }

  // Push the switch state at the launcher; it applies or drops the instruction
  // entries. A rejected promise is the normal case when the CLI console is gone.
  function tellLauncher() {
    try {
      window
        .fetch(STATE, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ enabled: enabled }),
          cache: "no-store"
        })
        .catch(function () {});
    } catch (err) {
      return;
    }
  }

  // The launcher is the source of truth at load: a session started with the feed
  // on shows the switch on, even in a fresh renderer with empty localStorage.
  function askLauncher() {
    try {
      window
        .fetch(STATE, { cache: "no-store" })
        .then(function (res) {
          return res.ok ? res.json() : null;
        })
        .then(function (data) {
          if (!data || typeof data.enabled !== "boolean") return;
          if (data.enabled === enabled) return;
          enabled = data.enabled;
          persist();
          reflect();
        })
        .catch(function () {});
    } catch (err) {
      return;
    }
  }

  function build() {
    var root = document.createElement("label");
    root.setAttribute("data-component", "switch");
    root.setAttribute("data-slot", SLOT);
    root.setAttribute("title", "Abliterated");
    root.style.flex = "0 0 auto";

    var box = document.createElement("input");
    box.setAttribute("data-slot", "switch-input");
    box.setAttribute("role", "switch");
    box.setAttribute("aria-label", "Abliterated");
    box.type = "checkbox";
    box.checked = enabled;

    var text = document.createElement("span");
    text.setAttribute("data-slot", "switch-label");
    text.textContent = "Abliterated";

    var control = document.createElement("span");
    control.setAttribute("data-slot", "switch-control");
    var thumb = document.createElement("span");
    thumb.setAttribute("data-slot", "switch-thumb");
    setThumb(thumb, enabled);
    control.appendChild(thumb);

    box.addEventListener("change", function () {
      enabled = box.checked === true;
      persist();
      tellLauncher();
      reflect();
      try {
        window.dispatchEvent(
          new CustomEvent("zzz:abliterated", { detail: { enabled: enabled } })
        );
      } catch (err) {
        return;
      }
    });
    box.addEventListener("click", function (event) {
      event.stopPropagation();
    });

    root.appendChild(box);
    root.appendChild(text);
    root.appendChild(control);
    return root;
  }

  // ------------------------------------------------------------ settings tab
  //
  // The settings shell is a `tabs-v2` list: `aside.settings-sidebar >
  // .settings-nav > .settings-nav-groups > .settings-nav-group`, one
  // `[data-slot=tabs-v2-trigger-wrapper]` per tab, and the selected tab paints
  // through `.settings-nav-groups [data-slot=tabs-v2-trigger-wrapper]:has(
  // [data-selected])`.
  //
  // `.settings-nav-groups` is a Solid `For` list: every selection change re-runs
  // it, and a node appended inside it is destroyed on the next run. Destroying
  // the node between mousedown and mouseup kills the click, which is exactly why
  // the old in-group entries looked dead. So the entries live in our own
  // `[data-zzz-nav]` block under `.settings-nav` (outside the reconciled list,
  // static child of the sidebar), and the panels live in a `[data-zzz-sheet]`
  // overlay we own, sized to `.settings-content`. Vendor panels are never hidden
  // or mutated: closing the sheet simply reveals whatever the shell had.

  function settingsHost() {
    var content = document.querySelector(".settings-content");
    var nav = document.querySelector(".settings-nav");
    var groups = document.querySelector(".settings-nav-groups");
    if (!content) return null;
    if (!nav) {
      if (!groups) return null;
      nav = groups.parentElement;
    }
    if (!nav) return null;
    return { nav: nav, groups: groups, content: content };
  }

  function navBlock(host) {
    var block = host.nav.querySelector("[data-zzz-nav]");
    if (block) return block;
    block = document.createElement("div");
    block.setAttribute("data-zzz-nav", "");
    var caption = document.createElement("div");
    caption.setAttribute("data-zzz-nav-label", "");
    caption.textContent = "ZzZ Code";
    block.appendChild(caption);
    // Appended after the vendor groups, never inside them: `.settings-nav` has a
    // static child list, so nothing re-runs a `For` over our row.
    host.nav.appendChild(block);
    return block;
  }

  function iconFor(kind) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("width", "16");
    svg.setAttribute("height", "16");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.6");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("stroke-linecap", "round");
    var path = document.createElementNS(ns, "path");
    path.setAttribute(
      "d",
      kind === "themes"
        ? "M12 3.6a8.4 8.4 0 1 0 0 16.8h1.1a1.9 1.9 0 0 0 0-3.8h-.8a1.7 1.7 0 0 1 0-3.4H17a3.4 3.4 0 0 0 3.4-3.4A6.2 6.2 0 0 0 12 3.6z"
        : "M6 4h12l-8.5 7.5H18L6 20l3.8-6.5H6.5z"
    );
    svg.appendChild(path);
    return svg;
  }

  var TABS = [
    { id: "zzz", label: "ZzZ Code", kind: "zzz", build: buildZzzPanel },
    { id: "themes", label: "Themes", kind: "themes", build: buildThemesPanel }
  ];

  function buildTab(tab) {
    // Vendor contract, copied from the shell's `tabs-v2` trigger: wrapper div
    // with `data-value`, a `role=tab` button carrying `data-key` and
    // `data-selected`, and one `[data-slot=tabs-v2-trigger-content]` span that
    // owns the flex layout. Anything less and the row does not inherit the
    // group's 28px metrics.
    var wrap = document.createElement("div");
    wrap.setAttribute("data-slot", "tabs-v2-trigger-wrapper");
    wrap.setAttribute("data-value", tab.id);
    wrap.setAttribute("data-zzz-tab", tab.id);

    var button = document.createElement("button");
    button.type = "button";
    button.setAttribute("data-slot", "tabs-v2-trigger");
    button.setAttribute("data-key", tab.id);
    button.setAttribute("data-orientation", "vertical");
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", "false");
    button.setAttribute("tabindex", "-1");

    var content = document.createElement("span");
    content.setAttribute("data-slot", "tabs-v2-trigger-content");
    content.className = "inline-flex items-center gap-2";
    content.appendChild(iconFor(tab.kind));

    var label = document.createElement("span");
    label.textContent = tab.label;
    content.appendChild(label);

    button.appendChild(content);
    // Activation rides `pointerdown`, not `click`: a click needs the node to
    // survive mousedown -> mouseup, and a shell re-render in that window is the
    // one thing that used to eat the press. `click` stays wired for keyboard
    // activation, and `activateTab` no-ops on the id that is already open.
    wrap.addEventListener("pointerdown", function (event) {
      if (event.button !== 0) return;
      event.preventDefault();
      event.stopPropagation();
      activateTab(tab.id);
    });
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      activateTab(tab.id);
    });

    wrap.appendChild(button);
    return wrap;
  }

  function panelFrame(title, sub) {
    var panel = document.createElement("div");
    panel.className = "settings-panel";
    panel.setAttribute("data-zzz-panel", "");
    panel.setAttribute("hidden", "");

    var header = document.createElement("div");
    header.className = "settings-tab-header";
    var headerRow = document.createElement("div");
    headerRow.className = "settings-tab-header-row";
    var copy = document.createElement("div");
    copy.className = "flex flex-col gap-1";
    var head = document.createElement("h2");
    head.className = "settings-tab-title";
    head.textContent = title;
    var line = document.createElement("span");
    line.className = "text-11-regular text-v2-text-text-muted";
    line.textContent = sub;
    copy.appendChild(head);
    copy.appendChild(line);
    headerRow.appendChild(copy);
    header.appendChild(headerRow);
    panel.appendChild(header);

    var body = document.createElement("div");
    body.className = "settings-tab-body";
    panel.appendChild(body);
    return { panel: panel, body: body };
  }

  function makeSection(title) {
    var section = document.createElement("section");
    section.className = "settings-section";
    section.setAttribute("data-zzz-section", "");
    if (title) {
      var head = document.createElement("div");
      head.setAttribute("data-zzz-title", "");
      head.textContent = title;
      section.appendChild(head);
    }
    return section;
  }

  function makeRow(title, hint, control) {
    var row = document.createElement("div");
    row.setAttribute("data-zzz-row", "");
    var copy = document.createElement("div");
    copy.setAttribute("data-zzz-copy", "");
    var label = document.createElement("span");
    label.setAttribute("data-zzz-title", "");
    label.textContent = title;
    copy.appendChild(label);
    if (hint) {
      var note = document.createElement("span");
      note.setAttribute("data-zzz-hint", "");
      note.textContent = hint;
      copy.appendChild(note);
    }
    row.appendChild(copy);
    if (control) row.appendChild(control);
    return row;
  }

  function makeButton(text) {
    var button = document.createElement("button");
    button.type = "button";
    button.setAttribute("data-zzz-action", "1");
    button.textContent = text;
    return button;
  }

  // Same vendor switch contract as the composer knob: a real
  // `[data-component=switch]` label so the app's own focus and hover states
  // apply, with the track geometry declared in STYLE and the thumb geometry set
  // inline `!important` (see setThumb) so it stays a circle on every state.
  function makeSwitch(checked, onChange) {
    var root = document.createElement("label");
    root.setAttribute("data-component", "switch");
    root.setAttribute("data-zzz-switch", "1");
    root.style.flex = "0 0 auto";

    var box = document.createElement("input");
    box.setAttribute("data-slot", "switch-input");
    box.setAttribute("role", "switch");
    box.type = "checkbox";
    box.checked = checked === true;

    var caption = document.createElement("span");
    caption.setAttribute("data-slot", "switch-label");
    caption.style.position = "absolute";
    caption.style.width = "1px";
    caption.style.height = "1px";
    caption.style.overflow = "hidden";
    caption.style.clip = "rect(0 0 0 0)";
    caption.textContent = "toggle";

    var control = document.createElement("span");
    control.setAttribute("data-slot", "switch-control");
    var thumb = document.createElement("span");
    thumb.setAttribute("data-slot", "switch-thumb");
    setThumb(thumb, box.checked);
    control.appendChild(thumb);

    function sync() {
      setThumb(thumb, box.checked);
      if (box.checked) root.setAttribute("data-checked", "");
      else root.removeAttribute("data-checked");
    }

    box.addEventListener("change", function () {
      sync();
      onChange(box.checked === true);
    });
    box.addEventListener("click", function (event) {
      event.stopPropagation();
    });

    root.appendChild(box);
    root.appendChild(caption);
    root.appendChild(control);
    sync();

    return {
      root: root,
      set: function (value) {
        box.checked = value === true;
        sync();
      }
    };
  }

  function postJSON(url, body) {
    try {
      return window
        .fetch(url, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(body || {}),
          cache: "no-store"
        })
        .then(function (res) {
          return res
            .json()
            .catch(function () {
              return null;
            })
            .then(function (data) {
              return { ok: res.ok, data: data };
            });
        })
        .catch(function () {
          return { ok: false, data: null };
        });
    } catch (err) {
      return Promise.resolve({ ok: false, data: null });
    }
  }

  function buildZzzPanel() {
    var frame = panelFrame("ZzZ Code", "Local launcher controls for this machine");
    var body = frame.body;

    var jail = makeSection("Abliterated");
    var action = makeButton("Jailbreak All Opened Folders");
    var status = document.createElement("div");
    status.setAttribute("data-zzz-status", "");
    action.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      runJailbreak(action, status);
    });
    jail.appendChild(action);
    jail.appendChild(status);
    body.appendChild(jail);

    var ups = makeSection("Updates");
    var enableSwitch = makeSwitch(false, function (on) {
      statusLine.textContent = "Status: reading\u2026";
      postJSON(UPD_ENABLE, { enabled: on }).then(function (result) {
        applyUpdateStatus(result.data, true);
      });
    });
    var autoSwitch = makeSwitch(true, function (on) {
      postJSON(UPD_AUTO, { auto: on }).then(function (result) {
        applyUpdateStatus(result.data, true);
      });
    });

    ups.appendChild(
      makeRow(
        "Enable Updates",
        "Off by default \u00b7 pulls releases and commits from GitHub",
        enableSwitch.root
      )
    );

    var statusLine = document.createElement("div");
    statusLine.setAttribute("data-zzz-status", "");
    statusLine.setAttribute("data-zzz-update-status", "");
    statusLine.textContent = "Status: reading\u2026";
    ups.appendChild(statusLine);

    ups.appendChild(
      makeRow("Auto update", "Applies what it finds without asking", autoSwitch.root)
    );

    var check = makeButton("Check now");
    check.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      statusLine.textContent = "Status: checking\u2026";
      postJSON(UPD_CHECK, {}).then(function (result) {
        applyUpdateStatus(result.data, true);
      });
    });

    var version = document.createElement("div");
    version.setAttribute("data-zzz-hint", "");
    version.textContent = "ZzZ Code " + VERSION + " \u00b7 OpenCode managed by the launcher";

    var foot = document.createElement("div");
    foot.setAttribute("data-zzz-row", "");
    foot.appendChild(version);
    foot.appendChild(check);
    ups.appendChild(foot);

    body.appendChild(ups);

    // -------------------------------------------------------- diagnostics
    var diag = makeSection("Diagnostics");
    var diagStatus = document.createElement("div");
    diagStatus.setAttribute("data-zzz-status", "");
    var diagRow = document.createElement("div");
    diagRow.setAttribute("data-zzz-row", "");
    var openCrash = makeButton("Crash log");
    var clearCrash = makeButton("Clear log");
    var copyDiag = makeButton("Copy report");
    diagRow.appendChild(openCrash);
    diagRow.appendChild(clearCrash);
    diagRow.appendChild(copyDiag);
    diag.appendChild(diagRow);
    diag.appendChild(diagStatus);

    function readDiag() {
      return fetch(DIAG, { cache: "no-store" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          return data || null;
        })
        .catch(function () {
          return null;
        });
    }

    // Flat `key: value` lines, because the reader is a bug report, not a parser.
    function formatDiag(data) {
      var lines = ["ZzZ Code diagnostics", ""];
      if (!data) {
        lines.push("bridge: offline");
        return lines.join("\n");
      }
      var keys = [
        ["version", "version"],
        ["bundle", "bundle"],
        ["python", "python"],
        ["port", "bridge port"],
        ["opencode", "opencode"],
        ["desktop", "desktop"],
        ["themes", "themes"],
        ["workers", "workers"],
        ["cli_store", "cli store"],
        ["agents", "AGENTS.md"],
        ["crash_log", "crash log"]
      ];
      for (var i = 0; i < keys.length; i += 1) {
        var value = data[keys[i][0]];
        lines.push(keys[i][1] + ": " + (value === undefined || value === null || value === "" ? "n/a" : value));
      }
      if (data.last_crash) lines.push("last crash: " + data.last_crash);
      return lines.join("\n");
    }

    function showDiag() {
      return readDiag().then(function (data) {
        if (!data) {
          diagStatus.textContent = "launcher bridge offline";
          return null;
        }
        diagStatus.textContent =
          "v" + (data.version || "?") + " \u00b7 python " + (data.python || "?") +
          " \u00b7 " + (data.themes || 0) + " themes" +
          (data.crash_log ? " \u00b7 crash log present" : " \u00b7 no crash log");
        return data;
      });
    }

    openCrash.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      postJSON(CRASH_OPEN, {}).then(function (result) {
        diagStatus.textContent = result.ok
          ? (result.data && result.data.detail) || "log opened"
          : (result.data && result.data.detail) || "no crash log to open";
      });
    });
    clearCrash.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      postJSON(CRASH_CLEAR, {}).then(function (result) {
        diagStatus.textContent = result.ok
          ? (result.data && result.data.detail) || "log cleared"
          : "could not clear the log";
      });
    });
    copyDiag.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      showDiag().then(function (data) {
        copyText(formatDiag(data)).then(function (ok) {
          diagStatus.textContent = ok ? "report copied" : "clipboard refused";
          if (ok) toast("diagnostics copied");
        });
      });
    });

    body.appendChild(diag);

    // ------------------------------------------------------------- runtime
    var runtime = makeSection("Runtime");
    var runStatus = document.createElement("div");
    runStatus.setAttribute("data-zzz-status", "");
    var runRow = document.createElement("div");
    runRow.setAttribute("data-zzz-row", "");
    var verify = makeButton("Verify stack");
    var restartWorkers = makeButton("Restart keeper");
    runRow.appendChild(verify);
    runRow.appendChild(restartWorkers);

    verify.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      verify.disabled = true;
      runStatus.textContent = "reading the stack\u2026";
      postJSON(STACK_VERIFY, {}).then(function (result) {
        verify.disabled = false;
        var data = result.data || {};
        if (!result.ok) {
          runStatus.textContent = "verify failed \u00b7 " + (data.detail || "bridge offline");
          return;
        }
        runStatus.textContent =
          (data.ok ? "stack ok" : "stack incomplete") +
          " \u00b7 " + (data.opencode || "opencode ?") +
          " \u00b7 " + (data.desktop || "desktop ?");
        toast(data.ok ? "stack verified" : "stack incomplete");
      });
    });

    restartWorkers.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      restartWorkers.disabled = true;
      runStatus.textContent = "restarting the keepers\u2026";
      postJSON(WORKERS_RESTART, {}).then(function (result) {
        restartWorkers.disabled = false;
        var data = result.data || {};
        runStatus.textContent = result.ok
          ? (data.detail || "workers restarted")
          : "restart failed \u00b7 " + (data.detail || "bridge offline");
      });
    });

    runtime.appendChild(runRow);
    runtime.appendChild(runStatus);
    body.appendChild(runtime);

    // ----------------------------------------------------------- templates
    var tpl = makeSection("Templates");
    var tplStatus = document.createElement("div");
    tplStatus.setAttribute("data-zzz-status", "");
    var tplList = document.createElement("div");
    tpl.appendChild(tplList);
    tpl.appendChild(tplStatus);

    function paintTemplates(items) {
      tplList.textContent = "";
      if (!items || !items.length) {
        tplStatus.textContent = "no templates on disk";
        return;
      }
      for (var i = 0; i < items.length; i += 1) {
        (function (item) {
          var row = document.createElement("div");
          row.setAttribute("data-zzz-template", "");
          var head = document.createElement("div");
          head.setAttribute("data-zzz-template-head", "");
          var name = document.createElement("span");
          name.setAttribute("data-zzz-template-name", "");
          name.textContent = item.name || item.id;
          var add = makeButton("Add to AGENTS.md");
          head.appendChild(name);
          head.appendChild(add);
          var note = document.createElement("div");
          note.setAttribute("data-zzz-template-note", "");
          note.textContent = item.note || "";
          row.appendChild(head);
          row.appendChild(note);

          row.addEventListener("click", function (event) {
            if (event.target === add) return;
            event.preventDefault();
            event.stopPropagation();
            copyText(item.body || "").then(function (ok) {
              tplStatus.textContent = ok
                ? (item.name || item.id) + " copied"
                : "clipboard refused";
            });
          });
          add.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopPropagation();
            add.disabled = true;
            postJSON(TEMPLATE_SAVE, { id: item.id }).then(function (result) {
              add.disabled = false;
              tplStatus.textContent = result.ok
                ? (result.data && result.data.detail) || "appended"
                : "failed \u00b7 " + ((result.data && result.data.detail) || "bridge offline");
            });
          });
          tplList.appendChild(row);
        })(items[i]);
      }
      tplStatus.textContent = items.length + " templates \u00b7 click one to copy";
    }

    function loadTemplates() {
      tplStatus.textContent = "reading templates\u2026";
      fetch(TEMPLATES, { cache: "no-store" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          paintTemplates((data && data.templates) || []);
        })
        .catch(function () {
          tplStatus.textContent = "launcher bridge offline";
        });
    }

    body.appendChild(tpl);

    // ------------------------------------------------------------- footer
    var banner = document.createElement("a");
    banner.setAttribute("data-zzz-banner", "");
    banner.setAttribute("href", "https://discord.gg/pQBDchXTdp");
    banner.setAttribute("target", "_blank");
    banner.setAttribute("rel", "noreferrer noopener");
    var mark = document.createElement("span");
    mark.setAttribute("data-zzz-banner-mark", "");
    mark.textContent = "z";
    var bannerCopy = document.createElement("span");
    var bannerName = document.createElement("b");
    bannerName.textContent = "ZzZ Code community";
    var bannerNote = document.createElement("span");
    bannerNote.textContent = "Builds, patches, questions \u00b7 opens in your browser";
    bannerCopy.appendChild(bannerName);
    bannerCopy.appendChild(document.createElement("br"));
    bannerCopy.appendChild(bannerNote);
    banner.appendChild(mark);
    banner.appendChild(bannerCopy);
    body.appendChild(banner);

    var about = makeSection("About");
    var aboutText = document.createElement("div");
    aboutText.setAttribute("data-zzz-hint", "");
    aboutText.textContent =
      "ZzZ Code " + VERSION + " \u00b7 built and kept by ZenZenitoZeno. A patched " +
      "build of the OpenCode desktop app, published for research and study: a " +
      "readable fork used to test local tooling, theme plumbing and launcher " +
      "behaviour. Not affiliated with Anomaly Innovations. Source and notes at " +
      "github.com/ZenTheScripter/zzz-code.";
    about.appendChild(aboutText);
    body.appendChild(about);

    frame.panel.addEventListener("zzz:refresh", function () {
      showDiag();
      loadTemplates();
    });
    showDiag();
    loadTemplates();

    function applyUpdateStatus(data, sync) {
      if (!data || typeof data.enabled !== "boolean") {
        statusLine.textContent = "Status: launcher bridge offline";
        return;
      }
      if (sync) {
        enableSwitch.set(data.enabled);
        autoSwitch.set(data.auto === true);
      }
      statusLine.textContent = "Status: " + (data.status || "unknown");
      renderPill(data);
    }

    refreshUpdates(enableSwitch, autoSwitch, statusLine);
    frame.panel.addEventListener("zzz:refresh", function () {
      refreshUpdates(enableSwitch, autoSwitch, statusLine);
    });
    return frame.panel;
  }

  function refreshUpdates(enableSwitch, autoSwitch, statusLine) {
    try {
      fetch(UPD_STATUS, { cache: "no-store" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (!data || typeof data.enabled !== "boolean") {
            statusLine.textContent = "Status: launcher bridge offline";
            return;
          }
          enableSwitch.set(data.enabled);
          autoSwitch.set(data.auto === true);
          statusLine.textContent = "Status: " + (data.status || "unknown");
          renderPill(data);
        })
        .catch(function () {
          statusLine.textContent = "Status: launcher bridge offline";
        });
    } catch (err) {
      return;
    }
  }

  // ---------------------------------------------------------------- themes

  var themed = [];
  var THEME_STYLE_ID = "zzz-theme-overrides";

  // The shell writes `--v2-*` on `<html data-color-scheme>` from a stylesheet
  // rule, and it rewrites that attribute on every scheme change. Inline
  // properties on the same element would lose to a later rule pass, so the
  // overrides go into one `!important` sheet in `<head>`: it outlives every
  // Solid re-render and every scheme flip, and clearing it restores the vendor
  // palette exactly.
  function themeStyleNode() {
    var node = document.getElementById(THEME_STYLE_ID);
    if (!node) {
      node = document.createElement("style");
      node.id = THEME_STYLE_ID;
      node.setAttribute("data-zzz-theme", "");
      (document.head || ROOT).appendChild(node);
    }
    return node;
  }

  function paintTheme(colors, kind, wall) {
    var node = themeStyleNode();
    themed = [];
    if (!colors && !wall) {
      node.textContent = "";
      ROOT.removeAttribute("data-zzz-theme-painted");
      return;
    }
    var css = ":root,[data-color-scheme],[data-theme]{";
    var count = 0;
    for (var key in colors) {
      if (!Object.prototype.hasOwnProperty.call(colors, key)) continue;
      if (key.indexOf("--") !== 0) continue;
      var value = String(colors[key]).replace(/[;{}<>\n\r]/g, "").trim();
      if (!value) continue;
      css += key + ":" + value + " !important;";
      themed.push(key);
      count += 1;
    }
    if (kind === "light" || kind === "dark") css += "color-scheme:" + kind + " !important;";
    css += "}";
    // A wallpaper is a gradient string, never an image file: the vendor CSP and
    // the theme loader both stay happy, and there is nothing to fetch. It goes on
    // a fixed layer above the shell so it reads on every panel, under the dialogs
    // (`2147483000`) and toasts, and never eats a click.
    var wash = "";
    if (wall) {
      var clean = String(wall).replace(/[;{}<>\n\r"]/g, "").trim();
      if (clean && /^(linear|radial|conic)-gradient\(/i.test(clean)) {
        wash =
          'body::after{content:"";position:fixed;inset:0;pointer-events:none;' +
          "z-index:2147482000;opacity:.22;mix-blend-mode:soft-light;" +
          "background-image:" + clean + " !important;}";
        count += 1;
      }
    }
    node.textContent = count ? css + wash : "";
    if (count) ROOT.setAttribute("data-zzz-theme-painted", String(count));
    else ROOT.removeAttribute("data-zzz-theme-painted");
  }

  // Reload restore. The bridge keeps the applied id, so the first paint after a
  // window reload re-applies it before the settings page is ever opened; the
  // saved localStorage id is only a hint for the panel's own ordering.
  function restoreTheme() {
    try {
      fetch(THEMES, { cache: "no-store" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (!data || !data.active || !data.themes) return;
          for (var i = 0; i < data.themes.length; i += 1) {
            if (data.themes[i].id !== data.active) continue;
            var theme = data.themes[i];
            paintTheme(theme.colors, theme.kind, theme.wall);
            return;
          }
        })
        .catch(function () {
          return;
        });
    } catch (err) {
      return;
    }
  }

  function swatch(theme, onPick) {
    var button = document.createElement("button");
    button.type = "button";
    button.setAttribute("data-zzz-swatch", "");
    button.setAttribute("title", theme.name + " \u00b7 " + (theme.author || "zzz"));
    button.__zzzTheme = theme;
    if (theme.active) button.setAttribute("data-active", "");

    var colors = theme.colors || {};
    var bg = colors["--v2-background-bg-base"] || "var(--v2-background-bg-base)";
    var l3 = colors["--v2-background-bg-layer-03"] || "var(--v2-background-bg-layer-03)";
    var text = colors["--v2-text-text-base"] || "var(--v2-text-text-base)";
    var accent = colors["--v2-text-text-accent"] || "var(--v2-background-bg-accent)";

    var preview = document.createElement("span");
    preview.setAttribute("data-zzz-swatch-preview", "");
    preview.style.background = bg;
    if (theme.wall) {
      preview.style.backgroundImage = String(theme.wall);
      preview.setAttribute("data-wall", "");
    }
    var bars = [
      { width: "46%", color: text },
      { width: "70%", color: l3 },
      { width: "38%", color: accent }
    ];
    for (var i = 0; i < bars.length; i += 1) {
      var bar = document.createElement("span");
      bar.style.width = bars[i].width;
      bar.style.background = bars[i].color;
      preview.appendChild(bar);
    }

    var name = document.createElement("span");
    name.setAttribute("data-zzz-swatch-name", "");
    name.textContent = theme.name;

    button.appendChild(preview);
    button.appendChild(name);
    button.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      onPick(theme);
    });
    return button;
  }

  function buildThemesPanel() {
    var frame = panelFrame(
      "Themes",
      "Palettes painted over the shell \u00b7 your own live in ~/.zzzcode/themes"
    );
    var body = frame.body;

    var bar = document.createElement("div");
    bar.setAttribute("data-zzz-row", "");
    var tools = document.createElement("div");
    tools.setAttribute("data-zzz-copy", "");
    tools.style.flexDirection = "row";
    tools.style.gap = "8px";
    tools.style.flexWrap = "wrap";

    var reload = makeButton("Reload");
    var folder = makeButton("Theme folder");
    var fresh = makeButton("New theme");
    var surprise = makeButton("Surprise me");
    var exportPalette = makeButton("Copy palette");
    var clear = makeButton("Default");
    tools.appendChild(reload);
    tools.appendChild(folder);
    tools.appendChild(fresh);
    tools.appendChild(surprise);
    tools.appendChild(exportPalette);
    tools.appendChild(clear);
    bar.appendChild(tools);

    // Search is a plain substring match over name and author, and it re-renders
    // from the cached list, so typing never re-hits the bridge.
    var search = document.createElement("input");
    search.type = "search";
    search.setAttribute("data-zzz-search", "");
    search.setAttribute("placeholder", "Filter themes \u00b7 name or author");
    search.setAttribute("spellcheck", "false");
    bar.appendChild(search);

    var grid = document.createElement("div");
    grid.setAttribute("data-zzz-grid", "");

    var status = document.createElement("div");
    status.setAttribute("data-zzz-status", "");

    body.appendChild(bar);
    body.appendChild(grid);
    body.appendChild(status);

    var all = [];
    var activeTheme = null;
    var query = "";

    var all = [];
    var activeTheme = null;
    var query = "";
    var dir = "";

    function mark(id) {
      var cards = grid.querySelectorAll("[data-zzz-swatch]");
      for (var i = 0; i < cards.length; i += 1) {
        var theme = cards[i].__zzzTheme;
        if (theme && theme.id === id) cards[i].setAttribute("data-active", "");
        else cards[i].removeAttribute("data-active");
      }
    }

    function applyTheme(picked) {
      status.textContent = "Applying " + picked.name + "\u2026";
      postJSON(THEMES_APPLY, { id: picked.id }).then(function (result) {
        if (!result.ok || !result.data || !result.data.colors) {
          var why = (result.data && result.data.detail) || "bridge refused the id";
          status.textContent = "apply failed \u00b7 " + why;
          return;
        }
        paintTheme(result.data.colors, picked.kind, result.data.wall || picked.wall);
        activeTheme = picked;
        mark(picked.id);
        status.textContent = picked.name + " applied";
        toast(picked.name + " applied");
        try {
          window.localStorage.setItem(THEME_KEY, picked.id);
        } catch (err) {
          return;
        }
      });
    }

    function render() {
      grid.textContent = "";
      var needle = String(query || "").trim().toLowerCase();
      var shown = 0;
      for (var i = 0; i < all.length; i += 1) {
        var theme = all[i];
        var hay = String(theme.name || "") + " " + String(theme.author || "");
        if (needle && hay.toLowerCase().indexOf(needle) < 0) continue;
        theme.active = !!(activeTheme && theme.id === activeTheme.id);
        grid.appendChild(swatch(theme, applyTheme));
        shown += 1;
      }
      if (!shown) {
        var empty = document.createElement("div");
        empty.setAttribute("data-zzz-status", "");
        empty.textContent = "nothing matches \u201c" + String(query).trim() + "\u201d";
        grid.appendChild(empty);
      }
      status.textContent =
        shown + " of " + all.length + " themes" + (dir ? " \u00b7 " + dir : "");
    }

    function load() {
      status.textContent = "Reading themes\u2026";
      fetch(THEMES, { cache: "no-store" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          if (!data || !data.themes) {
            status.textContent = "launcher bridge offline";
            return;
          }
          all = data.themes;
          dir = data.dir || "";
          activeTheme = null;
          for (var i = 0; i < all.length; i += 1) {
            if (all[i].id === data.active) activeTheme = all[i];
          }
          render();
          if (activeTheme) paintTheme(activeTheme.colors, activeTheme.kind, activeTheme.wall);
        })
        .catch(function () {
          status.textContent = "launcher bridge offline";
        });
    }

    search.addEventListener("input", function () {
      query = search.value || "";
      render();
    });

    surprise.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      if (!all.length) return;
      var pool = all;
      var pick = pool[Math.floor(Math.random() * pool.length)];
      applyTheme(pick);
    });

    exportPalette.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      if (!activeTheme) {
        status.textContent = "nothing applied yet";
        return;
      }
      var payload = JSON.stringify(
        { id: activeTheme.id, name: activeTheme.name, kind: activeTheme.kind, wall: activeTheme.wall || "", colors: activeTheme.colors || {} },
        null,
        2
      );
      copyText(payload).then(function (ok) {
        status.textContent = ok ? "palette copied \u00b7 paste into a theme file" : "clipboard refused";
      });
    });

    reload.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      load();
    });
    folder.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      postJSON(THEMES_OPEN, {}).then(function (result) {
        status.textContent = result.ok
          ? "folder open"
          : "could not open the folder";
      });
    });
    fresh.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      postJSON(THEMES_NEW, {}).then(function (result) {
        status.textContent =
          (result.data && result.data.detail) || "template written";
        load();
      });
    });
    clear.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
      postJSON(THEMES_RESET, {}).then(function () {
        paintTheme(null);
        status.textContent = "vendor theme restored";
      });
    });

    load();
    frame.panel.addEventListener("zzz:refresh", load);
    return frame.panel;
  }

  function runJailbreak(button, status) {
    button.disabled = true;
    status.textContent = "Fetching the abliterated prompt...";
    postJSON(JAILBREAK, {}).then(function (result) {
      var detail = (result.data && result.data.detail) || "";
      if (result.ok) {
        status.textContent = detail || "done";
      } else {
        status.textContent = "failed \u00b7 " + (detail || "launcher bridge offline");
      }
      button.disabled = false;
    });
  }

  function ourTabs() {
    return document.querySelectorAll("[data-zzz-tab]");
  }

  function markNav(id) {
    var tabs = ourTabs();
    for (var i = 0; i < tabs.length; i += 1) {
      var trigger = tabs[i].querySelector('[data-slot="tabs-v2-trigger"]');
      if (!trigger) continue;
      if (tabs[i].getAttribute("data-zzz-tab") === id) {
        trigger.setAttribute("data-selected", "");
        trigger.setAttribute("aria-selected", "true");
        trigger.setAttribute("tabindex", "0");
      } else {
        trigger.removeAttribute("data-selected");
        trigger.setAttribute("aria-selected", "false");
        trigger.setAttribute("tabindex", "-1");
      }
    }
  }

  // The vendor row paints through `:has([data-selected])`. Our sheet paints its
  // own row, and leaving two lit rows reads as "two tabs at once", so the live
  // vendor selection is parked in `data-zzz-vendor-selected` and put back when
  // the sheet closes. Nothing else about the vendor DOM is touched.

  function clearVendorSelection(host) {
    if (!host || !host.groups) return;
    var wraps = host.groups.querySelectorAll("[data-slot=tabs-v2-trigger-wrapper]");
    for (var i = 0; i < wraps.length; i += 1) {
      var trigger = wraps[i].querySelector('[data-slot="tabs-v2-trigger"]');
      if (!trigger || !trigger.hasAttribute("data-selected")) continue;
      wraps[i].setAttribute("data-zzz-vendor-selected", "1");
      trigger.removeAttribute("data-selected");
      trigger.setAttribute("aria-selected", "false");
    }
  }

  function restoreVendorSelection(host) {
    if (!host || !host.groups) return;
    var marked = host.groups.querySelectorAll("[data-zzz-vendor-selected]");
    if (!marked.length) return;
    // If the shell has already painted a choice of its own, the parked marker is
    // stale: drop it and leave the fresh paint alone.
    var painted = host.groups.querySelector('[data-slot="tabs-v2-trigger"][data-selected]');
    for (var i = 0; i < marked.length; i += 1) {
      marked[i].removeAttribute("data-zzz-vendor-selected");
      if (painted) continue;
      var trigger = marked[i].querySelector('[data-slot="tabs-v2-trigger"]');
      if (!trigger) continue;
      trigger.setAttribute("data-selected", "");
      trigger.setAttribute("aria-selected", "true");
      trigger.setAttribute("tabindex", "0");
    }
  }

  var sheetState = { id: "" };

  function sheetNode() {
    // `div[data-zzz-sheet]`, never the bare attribute: `<html>` carries the
    // `data-zzz-sheet-open` flag while a sheet is up, and a bare selector would
    // grab the document element and style the page instead of the overlay.
    var sheet = document.querySelector("div[data-zzz-sheet]");
    if (sheet) return sheet;
    sheet = document.createElement("div");
    sheet.setAttribute("data-zzz-sheet", "");
    (document.body || ROOT).appendChild(sheet);
    return sheet;
  }

  // The sheet is a sibling overlay pinned to the measured content box. Measuring
  // beats `position:absolute` here because the shell centres a max-width column
  // and the sidebar can collapse; the rect is the only honest answer.
  function placeSheet() {
    var host = settingsHost();
    if (!host) return null;
    var rect = host.content.getBoundingClientRect();
    if (!rect.width || !rect.height) return null;
    var sheet = sheetNode();
    sheet.style.left = Math.round(rect.left) + "px";
    sheet.style.top = Math.round(rect.top) + "px";
    sheet.style.width = Math.round(rect.width) + "px";
    sheet.style.height = Math.round(rect.height) + "px";
    return sheet;
  }

  function sheetPanel(sheet, id) {
    var spec = null;
    for (var i = 0; i < TABS.length; i += 1) {
      if (TABS[i].id === id) spec = TABS[i];
    }
    if (!spec) return null;
    var panel = sheet.querySelector('[data-zzz-owner="' + id + '"]');
    if (!panel) {
      panel = spec.build();
      panel.setAttribute("data-zzz-owner", id);
      sheet.appendChild(panel);
    }
    var panels = sheet.querySelectorAll("[data-zzz-owner]");
    for (var j = 0; j < panels.length; j += 1) {
      if (panels[j] === panel) panels[j].removeAttribute("hidden");
      else panels[j].setAttribute("hidden", "");
    }
    return panel;
  }

  function activateTab(id) {
    if (sheetState.id === id) return;
    var host = settingsHost();
    if (!host) return;
    var sheet = placeSheet();
    if (!sheet) return;
    var panel = sheetPanel(sheet, id);
    if (!panel) return;
    sheetState.id = id;
    sheet.setAttribute("data-open", id);
    document.documentElement.setAttribute("data-zzz-sheet-open", id);
    clearVendorSelection(host);
    markNav(id);
    try {
      panel.dispatchEvent(new CustomEvent("zzz:refresh"));
    } catch (err) {
      return;
    }
  }

  function closeSheet() {
    if (!sheetState.id) return;
    sheetState.id = "";
    document.documentElement.removeAttribute("data-zzz-sheet-open");
    var sheet = document.querySelector("div[data-zzz-sheet]");
    if (sheet) sheet.removeAttribute("data-open");
    markNav("");
    restoreVendorSelection(settingsHost());
  }

  function bindNav(host) {
    if (host.nav.getAttribute("data-zzz-bound") === "1") return;
    host.nav.setAttribute("data-zzz-bound", "1");
    // Capture phase: the shell's own row is about to paint a vendor panel under
    // the sheet, so the sheet steps aside first and the parked selection comes
    // back if nothing new was chosen.
    host.nav.addEventListener(
      "pointerdown",
      function (event) {
        var target = event.target;
        if (!(target instanceof Element)) return;
        if (target.closest("[data-zzz-nav]")) return;
        closeSheet();
      },
      true
    );
  }

  function mountTab() {
    var host = settingsHost();
    if (!host) {
      closeSheet();
      return;
    }
    bindNav(host);
    var block = navBlock(host);
    for (var i = 0; i < TABS.length; i += 1) {
      if (!block.querySelector('[data-zzz-tab="' + TABS[i].id + '"]')) {
        block.appendChild(buildTab(TABS[i]));
      }
    }
    if (!sheetState.id) return;
    // A re-render can drop the sheet panel while the id stays selected; rebuild
    // in place and re-measure so the overlay keeps covering the content column.
    var sheet = placeSheet();
    if (!sheet || !sheet.querySelector('[data-zzz-owner="' + sheetState.id + '"]')) {
      var keep = sheetState.id;
      sheetState.id = "";
      activateTab(keep);
      return;
    }
    clearVendorSelection(host);
    markNav(sheetState.id);
  }

  // ------------------------------------------------------------ update pill
  //
  // Our own surface, deliberately separate from the vendor's update button: the
  // pill only exists while the launcher reports an update and updates are on.
  // With two updates pending it fuses into one pill and opens a chooser.

  var VERSION = "1.1.0";

  // Stock OpenCode parks its update button in the titlebar's right slot:
  // `header[data-slot=titlebar-v2]` holds a flex row, and the right-most child is
  // `div.relative.z-20...justify-end` containing `[data-slot=titlebar-update]`.
  // Our pill joins that same row, so it lands where the stock control lives and
  // never drifts over the window buttons.
  function titlebarHost() {
    var update = document.querySelector('[data-slot="titlebar-update"]');
    if (update && update.parentElement) return update.parentElement;
    var header = document.querySelector('header[data-slot="titlebar-v2"]');
    if (!header) return null;
    var kids = header.querySelectorAll(":scope > div");
    for (var i = 0; i < kids.length; i += 1) {
      if (kids[i].querySelector(":scope > .justify-end")) return kids[i].querySelector(":scope > .justify-end");
      if (kids[i].className && String(kids[i].className).indexOf("justify-end") >= 0) return kids[i];
    }
    return header;
  }

  function keepPillHome(node) {
    var host = titlebarHost();
    if (!host) {
      // Titlebar not mounted yet (or a themed shell without one): float it at the
      // stock offset rather than dropping it, and retry on the next pass.
      if (!node.hasAttribute("data-fixed")) {
        node.setAttribute("data-fixed", "");
        (document.body || ROOT).appendChild(node);
      }
      return;
    }
    if (node.hasAttribute("data-fixed")) node.removeAttribute("data-fixed");

    // The row is `[ ... ][titlebar-update][window controls]` and it is laid out
    // left to right, so "in the row" is not enough: appending puts the pill to
    // the right of the minimise/close buttons. The pill is spliced in directly
    // after the stock update slot, or, when the vendor has no update control, in
    // front of the window buttons. Both put it where the stock control lives.
    var slot = host.querySelector('[data-slot="titlebar-update"]');
    var anchor = null;
    if (slot && slot.parentElement === host) {
      anchor = slot.nextElementSibling;
    } else {
      var kids = host.children;
      for (var i = 0; i < kids.length; i += 1) {
        var name = String(kids[i].className || "");
        if (name.indexOf("winctl") >= 0 || name.indexOf("window-control") >= 0) {
          anchor = kids[i];
          break;
        }
      }
    }
    if (anchor) {
      if (node.nextElementSibling !== anchor) host.insertBefore(node, anchor);
      return;
    }
    if (node.parentElement !== host) host.appendChild(node);
  }

  function renderPill(status) {
    var zzzUp = !!(status && status.zzz && status.zzz.available);
    var ocUp = !!(status && status.opencode && status.opencode.available);
    var node = document.querySelector("[data-zzz-pill]");
    if (!status || !status.enabled || (!zzzUp && !ocUp)) {
      if (node) node.remove();
      return;
    }
    if (!node) {
      node = document.createElement("button");
      node.type = "button";
      node.setAttribute("data-zzz-pill", "");
      node.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
        openUpdateDialog();
      });
      keepPillHome(node);
    } else {
      keepPillHome(node);
    }
    node.textContent = "";
    var dot = document.createElement("i");
    node.appendChild(dot);
    var text = zzzUp && ocUp ? "2 updates" : zzzUp ? "ZzZ Code update" : "OpenCode update";
    node.appendChild(document.createTextNode(text));
  }

  function closeUpdateDialog() {
    var old = document.querySelector("[data-zzz-overlay]");
    if (old) old.remove();
  }

  function openUpdateDialog() {
    closeUpdateDialog();
    fetch(UPD_STATUS, { cache: "no-store" })
      .then(function (res) {
        return res.json();
      })
      .then(function (data) {
        if (!data || !data.enabled) return;
        buildDialog(data);
      })
      .catch(function () {
        return;
      });
  }

  function buildDialog(status) {
    var options = [];
    if (status.zzz && status.zzz.available) {
      options.push({ id: "zzz", label: "ZzZ Code " + status.zzz.available });
    }
    if (status.opencode && status.opencode.available) {
      options.push({ id: "opencode", label: "OpenCode " + status.opencode.available });
    }
    if (!options.length) return;
    if (options.length > 1) options.push({ id: "both", label: "Both" });

    var picked = options.length > 1 ? "both" : options[0].id;

    var overlay = document.createElement("div");
    overlay.setAttribute("data-zzz-overlay", "");
    var dialog = document.createElement("div");
    dialog.setAttribute("data-zzz-dialog", "");

    var head = document.createElement("h3");
    head.textContent = options.length > 1 ? "Two updates available" : "Update available";
    dialog.appendChild(head);

    var note = document.createElement("p");
    note.textContent = "Pick what to install. ZzZ Code applies a launcher build, OpenCode re-stages the runtime.";
    dialog.appendChild(note);

    var choices = document.createElement("div");
    choices.style.display = "flex";
    choices.style.flexDirection = "column";
    choices.style.gap = "6px";
    for (var i = 0; i < options.length; i += 1) {
      var row = document.createElement("label");
      row.setAttribute("data-zzz-choice", "");
      if (options[i].id === picked) row.setAttribute("data-selected", "");
      var radio = document.createElement("input");
      radio.type = "radio";
      radio.name = "zzz-update-target";
      radio.value = options[i].id;
      radio.checked = options[i].id === picked;
      radio.addEventListener("change", function () {
        picked = this.value;
        var all = choices.querySelectorAll("[data-zzz-choice]");
        for (var k = 0; k < all.length; k += 1) {
          all[k].removeAttribute("data-selected");
          if (all[k].querySelector("input").value === picked) {
            all[k].setAttribute("data-selected", "");
          }
        }
      });
      var caption = document.createElement("span");
      caption.textContent = options[i].label;
      row.appendChild(radio);
      row.appendChild(caption);
      choices.appendChild(row);
    }
    dialog.appendChild(choices);

    var line = document.createElement("p");
    line.setAttribute("data-zzz-hint", "");
    dialog.appendChild(line);

    var actions = document.createElement("div");
    actions.setAttribute("data-zzz-actions", "");
    var cancel = makeButton("Cancel");
    var go = makeButton("Update");
    actions.appendChild(cancel);
    actions.appendChild(go);
    dialog.appendChild(actions);

    cancel.addEventListener("click", function (event) {
      event.preventDefault();
      closeUpdateDialog();
    });
    go.addEventListener("click", function (event) {
      event.preventDefault();
      go.disabled = true;
      cancel.disabled = true;
      line.textContent = "Applying\u2026";
      postJSON(UPD_APPLY, { target: picked }).then(function (result) {
        var detail = (result.data && result.data.detail) || "done";
        line.textContent = (result.ok ? "" : "failed \u00b7 ") + detail;
        go.disabled = false;
        cancel.disabled = false;
        setTimeout(function () {
          closeUpdateDialog();
          fetch(UPD_STATUS, { cache: "no-store" })
            .then(function (res) {
              return res.json();
            })
            .then(function (data) {
              renderPill(data);
            })
            .catch(function () {
              return;
            });
        }, 1600);
      });
    });

    overlay.appendChild(dialog);
    overlay.addEventListener("click", function (event) {
      if (event.target === overlay) closeUpdateDialog();
    });
    (document.body || ROOT).appendChild(overlay);
  }

  function pollUpdates() {
    try {
      fetch(UPD_STATUS, { cache: "no-store" })
        .then(function (res) {
          return res.json();
        })
        .then(function (data) {
          renderPill(data);
        })
        .catch(function () {
          return;
        });
    } catch (err) {
      return;
    }
  }

  function mount() {
    var hosts = document.querySelectorAll(HOST);
    for (var i = 0; i < hosts.length; i += 1) {
      if (hosts[i].querySelector('[data-slot="' + SLOT + '"]')) continue;
      hosts[i].appendChild(build());
    }
    reflect();
    adoptChipType();
    mountTab();
  }

  var queued = false;
  function mountSoon() {
    queued = false;
    mount();
  }
  function schedule() {
    if (queued) return;
    queued = true;
    // rAF is the cheap path, but a backgrounded window does not paint frames and
    // the shell's DOM keeps changing there (settings panels mount lazily). The
    // timer is the floor: whichever fires first clears `queued`.
    window.requestAnimationFrame(mountSoon);
    window.setTimeout(mountSoon, 120);
  }

  // The chip and the settings shell both arrive after first paint (lazy panels,
  // model list fetch), so the type adoption and the tab are re-attempted on a
  // short ladder instead of relying on the observer's first pass alone.
  function reattempt() {
    var delays = [0, 120, 400, 1200, 2600];
    for (var i = 0; i < delays.length; i += 1) {
      window.setTimeout(function () {
        adoptChipType();
        mountTab();
      }, delays[i]);
    }
  }

  function start() {
    injectStyle();
    mount();
    askLauncher();
    reattempt();
    restoreTheme();
    pollUpdates();
    window.setInterval(pollUpdates, 90000);
    window.addEventListener("resize", function () {
      if (sheetState.id) placeSheet();
    });
    window.addEventListener(
      "keydown",
      function (event) {
        if (event.key === "Escape") {
          if (document.querySelector("[data-zzz-overlay]")) {
            closeUpdateDialog();
            return;
          }
          if (sheetState.id) {
            event.preventDefault();
            closeSheet();
          }
          return;
        }
        // Ctrl/Cmd+Shift+Z opens the ZzZ Code sheet from anywhere in the window,
        // and again closes it, which is quicker than walking the sidebar.
        if ((event.ctrlKey || event.metaKey) && event.shiftKey && !event.altKey) {
          var key = String(event.key || "").toLowerCase();
          if (key !== "z") return;
          event.preventDefault();
          if (sheetState.id) closeSheet();
          else activateTab("zzz");
        }
      },
      true
    );
    new MutationObserver(schedule).observe(document.body, {
      childList: true,
      subtree: true
    });
    window.addEventListener("storage", function (event) {
      if (event.key !== KEY) return;
      enabled = event.newValue === "1";
      reflect();
    });
  }

  window.zzzAbliterated = {
    get: function () {
      return enabled;
    },
    set: function (value) {
      enabled = value === true;
      persist();
      tellLauncher();
      reflect();
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
""".encode("utf-8")


# -------------------------------------------------------------------- rebrand
#
# Three surfaces, one brand: the renderer copy, the pre-load page, and the art
# the app ships as files. The copy pass rewrites values a person reads and
# leaves every identifier alone: vendor service names (`OpenCode Go`,
# `OpenCode Console`, `OpenCode Free`, `OpenCode Beta`, `OpenCode Stable`), the
# capability header, and links into the vendor docs still name things that are
# genuinely the vendor's, so they stay exactly as shipped.

BRAND = b"ZzZ Code"
VENDOR_NAME = b"OpenCode"
# Newer vendor builds title themselves "Opencode Unlimited". Both spellings are
# the app's own name, so the copy pass sweeps the longer one first.
VENDOR_NAMES = (b"Opencode Unlimited", b"OpenCode Unlimited", b"OpenCode")

# Whole-value rewrites that carry the disclaimer. Each pair is (shipped, ours);
# a missing first literal just means the vendor moved on, so the pair is skipped
# rather than raising.
#
# These are `str`, not `bytes`: Python bytes literals cannot hold non-ASCII, and
# every colophon literal carries a typographic character (’ · ©). Written as
# bytes they would be a literal backslash sequence that never matches the asar,
# which is exactly the silent no-op these pairs used to be. `rebrand_values`
# encodes both sides on the way in.
COPY_PAIRS = (
    (
        "`OpenCode, the open source coding agent`",
        "`ZzZ Code - a modified OpenCode build. Research use only.`",
    ),
    (
        "`OpenCode is a registered trademark of Anomaly Innovations, Inc.`",
        "`ZenZenitoZeno - research use only.`",
    ),
    (
        "`OpenCode includes the following open source software.`",
        "`ZzZ Code includes the following open source software.`",
    ),
    # The colophon. The first five are English-locale only, so the swap lands on
    # the string a reader actually sees and the other 60-odd locales keep their
    # own translation untouched. The website and the copyright line are shared by
    # every locale, so those two do move everywhere - which is intended: the
    # bundle is ours, and a vendor address in a fork is a dead link.
    (
        "`AI can\u2019t build great software, without you`",
        "`ZzZ Code \u00b7 a research build maintained by ZenZenitoZeno`",
    ),
    (
        "`Written by {{names}}`",
        "`Built and kept by ZenZenitoZeno`",
    ),
    (
        "`Illustrated by {{names}}`",
        "`Distributed for research and study only`",
    ),
    (
        "`First published in Missouri, USA`",
        "`Forked from the OpenCode open source project`",
    ),
    (
        "`First illustrated in London, England`",
        "`Independent \u00b7 not affiliated with Anomaly Innovations`",
    ),
    (
        "`Typeset in Inter and IBM Plex Mono`",
        "`Built for learning, auditing and experimentation`",
    ),
    (
        "`www.opencode.ai`",
        "`github.com/ZenTheScripter/zzz-code`",
    ),
    (
        "`\u00a9 Anomaly Innovations, Inc.`",
        "`\u00a9 ZenZenitoZeno \u00b7 research use only`",
    ),
)

# A hit is kept when one of these sits next to it. Every entry names the vendor,
# a vendor service, or a protocol field rather than this app.
COPY_KEEP = (
    b"X-OpenCode-",
    b"OpenCode:()=>",
    b"OpenCode Go",
    b"OpenCode Console",
    b"OpenCode Free",
    b"OpenCode Beta",
    b"OpenCode Stable",
    b"OpenCode V2",
    b"OpenCode {{version}}",
    b"OpenCode team",
    b"OpenCode Documentation",
    b"OpenCode is a registered trademark",
    b"https://opencode",
    b"onboarding.",
    b"error.installOpencode",
    # Our own disclaimer text names the vendor on purpose. Without these the
    # second pass eats its own tail: "a modified build of OpenCode" would come
    # back as "a modified build of ZzZ Code" the next time the bundle is written.
    b"modified OpenCode build",
    b"modified build of OpenCode",
)

COPY_WINDOW = 28


def rebrand_copy(body: bytes) -> bytes:
    """Swap the display name in place, leaving vendor names untouched."""
    out = bytearray(body)
    for name in VENDOR_NAMES:
        width = len(name)
        idx = 0
        while True:
            at = out.find(name, idx)
            if at < 0:
                break
            window = bytes(out[max(0, at - COPY_WINDOW): at + width + COPY_WINDOW])
            if any(keep in window for keep in COPY_KEEP):
                idx = at + width
                continue
            out[at:at + width] = BRAND
            idx = at + width
    return bytes(out)


def rebrand_values(body: bytes) -> bytes:
    for old, new in COPY_PAIRS:
        needle = old.encode("utf-8")
        if body.count(needle) == 1:
            body = body.replace(needle, new.encode("utf-8"), 1)
    return body


TITLE_TAG = b"<title data-sm>ZzZ Code</title>"


def rewrite_page(page: bytes) -> bytes:
    """Pre-load page: title, icons, share image, disclaimer, payload tag."""
    # The vendor renames itself between builds ("OpenCode", "Opencode Unlimited"),
    # so the title is matched by shape: any single <title> tag becomes ours.
    page = re.sub(
        rb"<title[^>]*>[^<]*</title>", TITLE_TAG, page, count=1
    )
    for old, new in (
        (b'href="./favicon-96x96-v3.png" sizes="96x96"', b'href="./assets/favicon-zzz-96.png" sizes="96x96"'),
        (b'href="./favicon-v3.svg"', b'href="./assets/favicon-zzz.svg"'),
        (b'href="./favicon-v3.ico"', b'href="./assets/favicon-zzz.svg" type="image/svg+xml"'),
        (b'content="./social-share.png"', b'content="./assets/social-share-zzz.png"'),
    ):
        if old in page:
            page = page.replace(old, new)
    notice = (
        b'<meta name="description" content="ZzZ Code - a modified OpenCode build. '
        b'Research use only." />'
    )
    if b'name="description"' not in page:
        page = page.replace(b"<head>", b"<head>\n    " + notice, 1)
    if SCRIPT_TAG not in page:
        page = page.replace(b"</body>", SCRIPT_TAG + b"\r\n  </body>", 1)
    return page


# ---------------------------------------------------------------- brand art
#
# Pure-python PNG so the build has no image dependency. Cells come from the same
# 4x5 bitmaps the wordmark patch uses, so the files and the in-app art match.

INK = (0x0B, 0x0B, 0x0F, 255)
ACCENT = (0x35, 0xE0, 0xB0, 255)
DIM = (0x1C, 0x1F, 0x2B, 255)


def _png(width: int, height: int, shade) -> bytes:
    """Encode RGB pixels. `shade(x, y)` returns an (r, g, b, a) tuple."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter: none
        for x in range(width):
            raw.extend(shade(x, y))

    def chunk(tag: bytes, body: bytes) -> bytes:
        return (
            struct.pack(">I", len(body))
            + tag
            + body
            + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF)
        )

    head = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", head)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


def _stamp(word: str, scale: int, gap: int, origin_x: int, origin_y: int):
    """Filled cells for `word` as (x, y) top-left pixels, plus the art bounds."""
    cells = set()
    cursor = origin_x
    for letter in word:
        bitmap = GLYPHS[letter]
        for r, line in enumerate(bitmap):
            for c, ch in enumerate(line):
                if ch != "#":
                    continue
                for dy in range(scale):
                    for dx in range(scale):
                        cells.add((cursor + c * scale + dx, origin_y + r * scale + dy))
        if letter in ASCENDER:
            row_from, row_to, col = ASCENDER[letter]
            for row in range(row_from, row_to + 1):
                for dy in range(scale):
                    for dx in range(scale):
                        cells.add(
                            (
                                cursor + col * scale + dx,
                                origin_y + row * scale + dy,
                            )
                        )
        cursor += (len(bitmap[0]) + gap) * scale
    return cells, cursor


def build_share_png(width: int = 1200, height: int = 630) -> bytes:
    scale, gap = 26, 1
    word = "ZZZCODE"
    span = (len(GLYPHS["Z"][0]) + gap) * scale * len(word) - gap * scale
    top = (height - 6 * scale) // 2 + scale
    cells, _ = _stamp(word, scale, gap, (width - span) // 2, top)
    bar_top = top + 5 * scale + 26

    def shade(x, y):
        if (x, y) in cells:
            return ACCENT
        if bar_top <= y < bar_top + 6 and width // 4 <= x < width - width // 4:
            return DIM
        return INK

    return _png(width, height, shade)


def build_icon_png(size: int = 96) -> bytes:
    scale = 14
    pad = (size - 4 * scale) // 2
    word = "ZZZCODE"
    _, span = _stamp(word, scale, 1, 0, 0)
    cells, _ = _stamp(word, scale, 1, (size - span) // 2, pad)

    def shade(x, y):
        if (x, y) in cells:
            return ACCENT
        edge = x in (0, size - 1) or y in (0, size - 1)
        return DIM if edge else INK

    return _png(size, size, shade)


ICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32">'
    '<rect width="32" height="32" rx="7" fill="#0b0b0f"/>'
    '<text x="6" y="23" fill="#35e0b0" font-size="26" font-family="sans-serif">zzz code</text>'
    "</svg>\n"
).encode("utf-8")


# ------------------------------------------------------------------- asar writer


class Archive:
    """An asar image held as `index` + `blob`, rebuilt on demand.

    Existing members are never moved and never rewritten; a member that changes
    is appended to the tail of the blob and its header entry repointed, which
    keeps this cheap on a 240 MB bundle and keeps untouched bytes byte-identical.
    """

    def __init__(self, data: bytes):
        json_len = struct.unpack("<I", data[12:16])[0]
        self.index = json.loads(data[16:16 + json_len].decode("utf-8"))
        self.blob = bytearray(data[asar_base(data):])

    def _files(self, member: str) -> dict:
        node = self.index
        for part in [p for p in member.split("/") if p][:-1]:
            node = node["files"][part]
        return node["files"]

    def has(self, member: str) -> bool:
        try:
            self._files(member)[member.rsplit("/", 1)[-1]]
        except KeyError:
            return False
        return True

    def body(self, member: str) -> bytes:
        entry = self._files(member)[member.rsplit("/", 1)[-1]]
        start = int(entry["offset"])
        return bytes(self.blob[start:start + int(entry["size"])])

    def write(self, member: str, payload: bytes) -> None:
        files = self._files(member)
        name = member.rsplit("/", 1)[-1]
        while len(self.blob) % 4:
            self.blob.append(0)
        entry = files.setdefault(name, {})
        entry["offset"] = str(len(self.blob))
        entry["size"] = len(payload)
        # The vendor block hashes describe the shipped bytes; a rewritten or
        # added member has no valid hash, so the field is dropped rather than
        # left stale.
        entry.pop("integrity", None)
        self.blob.extend(payload)

    def build(self) -> bytes:
        raw = json.dumps(self.index, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        pad = (4 - len(raw) % 4) % 4
        header = 4 + len(raw) + pad
        return b"".join(
            (
                struct.pack("<I", 4),
                struct.pack("<I", header + 4),
                struct.pack("<I", header),
                struct.pack("<I", len(raw)),
                raw,
                b"\0" * pad,
                bytes(self.blob),
            )
        )


# ------------------------------------------------------------------- lifecycle


def gui_state() -> dict:
    state = {
        "available": ASAR.is_file(),
        "patched": False,
        "script": False,
        "member": False,
        "branded": False,
        "art": False,
        "error": "",
    }
    if not state["available"]:
        return state
    try:
        archive = Archive(ASAR.read_bytes())
        page = archive.body(INDEX_MEMBER)
        state["script"] = SCRIPT_TAG in page
        state["member"] = archive.has(GUI_MEMBER) and archive.body(GUI_MEMBER) == GUI_JS
        state["branded"] = b"<title data-sm>ZzZ Code</title>" in page
        state["art"] = archive.has(SHARE_MEMBER) and archive.has(ICON_SVG_MEMBER)
        state["patched"] = (
            state["script"] and state["member"] and state["branded"] and state["art"]
        )
    except (KeyError, OSError, RuntimeError, ValueError, UnicodeDecodeError) as exc:
        state["error"] = str(exc)[:160]
    return state


def renderer_member(archive: "Archive") -> str:
    """The hashed bundle name is derived from the shipped page, never assumed."""
    page = archive.body(INDEX_MEMBER).decode("utf-8", "replace")
    at = page.find('src="./assets/')
    if at < 0:
        raise RuntimeError("renderer script tag not found")
    start = at + len('src="./assets/')
    end = page.find('"', start)
    return "/out/renderer/assets/" + page[start:end]


def apply() -> tuple[bool, str]:
    """Write the payload, the rebrand and the art into the installed bundle."""
    if not ASAR.is_file():
        return False, "desktop bundle not installed"
    if not BACKUP.is_file():
        # The backup is the only undo. Without it a repacked bundle could not be
        # rolled back, so the wordmark pass has to run first.
        return False, "no pristine backup - apply the wordmark patch first"
    try:
        archive = Archive(ASAR.read_bytes())
        changed = 0

        page = archive.body(INDEX_MEMBER)
        fresh = rewrite_page(page)
        if fresh != page:
            if b"</body>" not in fresh:
                return False, "renderer index has no </body> anchor"
            archive.write(INDEX_MEMBER, fresh)
            changed += 1

        if not archive.has(GUI_MEMBER) or archive.body(GUI_MEMBER) != GUI_JS:
            archive.write(GUI_MEMBER, GUI_JS)
            changed += 1

        bundle = renderer_member(archive)
        body = archive.body(bundle)
        # Pairs run first: each one matches the vendor's exact shipped literal,
        # and the copy pass behind them would have already renamed the subject.
        branded = rebrand_copy(rebrand_values(body))
        if branded != body:
            archive.write(bundle, branded)
            changed += 1

        for member, payload in (
            (SHARE_MEMBER, build_share_png()),
            (ICON_SVG_MEMBER, ICON_SVG),
            (ICON_PNG_MEMBER, build_icon_png()),
        ):
            if not archive.has(member) or archive.body(member) != payload:
                archive.write(member, payload)
                changed += 1

        if changed == 0:
            return True, "composer toggle and rebrand already applied"
        ASAR.write_bytes(archive.build())
    except (KeyError, OSError, RuntimeError, ValueError, UnicodeDecodeError) as exc:
        return False, str(exc)[:160]
    return True, "composer toggle and rebrand applied (%d member(s))" % changed


def main(argv) -> int:
    if "--check" in argv:
        state = gui_state()
        for key in ("available", "script", "member", "patched", "error"):
            print("%-10s: %s" % (key, state[key]))
        return 0 if not state["error"] else 1
    ok, message = apply()
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
