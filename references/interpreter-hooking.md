# Interpreter/VM hooking (as an alternative to address-based memory scanning)

[ref:live-memory-patching] covers AOB scanning + pointer chains — finding a value's
*address* in a specific running process. This doc covers a different, more robust
class of technique: hooking the engine's own **interpreter or scripting VM** at a
stable function (string draw, expression eval, bytecode dispatch) instead of chasing
an address. An address shifts between game versions and ASLR runs; the interpreter's
own entry points for "evaluate this expression" or "draw this string" don't.

This pattern (and the engine-coverage map below) comes from studying the architecture
of **MTool**, a Chinese machine-translation injector for Japanese games — Michael's
own long-standing tool and the actual inspiration for this whole skill. MTool isn't
open source and we don't vendor its compiled hook DLLs here; what's genuinely reusable
is the *pattern* (inject early, hook the interpreter, not a raw address) and the
engine-detection knowledge, both derived from its config format and file layout
(`Tool/loaders/*Hook*.dll` naming, `Tool/gameLib/*.gljson` per-game profiles).

## The pattern

1. **Inject a DLL before the target's own entry point runs** ("inject at OEP" —
   original entry point). This is stronger than injecting after `main()` starts,
   because the hook is live before any of the game's own init code executes, so
   nothing can run un-observed.
2. **Hook a stable interpreter-level function**, not a value's address:
   - A string-rendering/draw call, to intercept every piece of text the game
     displays (MTool's actual use case: swap in a translation).
   - An expression-eval or variable-get/set call, to intercept every read/write of a
     named game variable — this is the part directly relevant to *our* use case
     (save-state editing), even though MTool itself only uses this for text.
3. **Bridge to an external process** over a local socket/IPC (MTool's own app talks to
   its injected hooks this way — same general shape as the DLL-injection-plus-IPC
   fallback already noted in [ref:live-memory-patching]).

## Engine detection table

Derived from which hook DLL MTool selects per engine (`Tool/loaders/`) and what
file/folder signature identifies each one — useful as a detection reference
independent of MTool itself:

| Engine | Detect by | Interpreter hooked | Notes |
|---|---|---|---|
| RPG Maker XP/VX/VX Ace | `RGSS1.dll`/`RGSS2.dll`/`RGSS3.dll` next to the exe, `Data/*.rxdata`/`*.rvdata2` | Ruby (RGSS) | Very common J-RPG engine, not yet covered elsewhere in this toolkit |
| RPG Maker MZ/MV | `package.json` + `www/` folder + `nw.exe` (or a renamed NW.js binary) | V8/Node — same shell MTool itself is built on | Since it's just Node/Chromium under the hood, the running JS context is reachable directly, no native hooking needed in principle |
| KiriKiri / KiriKiriZ | `.xp3` archive files, `TVP`/`krkr` strings in the exe | TJS (KiriKiri's own script language) | Very common Japanese VN engine, not covered elsewhere here |
| Wolf RPG Editor (ウディタ) | `Data.wolf`, `Game.exe` | Proprietary — closed-source engine, hook targets known function offsets per version | No public bytecode format the way GameMaker has one |
| SRPG Studio | distinctive project folder layout, `Game.exe` | Ruby-like embedded scripting | Tactics-RPG-focused engine |
| Python-based games (incl. Ren'Py) | `.py`/`.pyc` presence, `python3*.dll`, or (for Ren'Py specifically) the signatures in [ref:renpy-galleries] | CPython interpreter directly | For Ren'Py specifically, prefer the engine's own sanctioned API ([ref:renpy-galleries]) over interpreter hooking when the goal is a gallery/save unlock — hooking is the *text-translation* answer, not the save-editing one |
| Unity (Mono) | see [ref:unity-mono-saves] | Mono runtime | Cross-reference — MTool's "MonoJunkie" hook and Cheat Engine's Mono dissector solve the same discovery problem two different ways |
| RPG Maker Bakin | distinctive launcher/player exe pair | — | Newer 3D-capable successor to classic RPG Maker |
| Action Game Maker (AGTK) | distinctive project layout | — | Japanese action-game-maker tool |

## If we ever want to build our own hook instead of just detecting the engine

**Frida** (frida.re, open source, actively maintained) is the legitimate, buildable
equivalent of what MTool's compiled hook DLLs do: it injects into a running process
and lets you hook functions by name/pattern across multiple language runtimes,
including Python, V8/Node, and Mono/CLR — the same three interpreter families in the
table above that MTool covers with purpose-built DLLs. If a future case needs live
interpreter-level hooking (as opposed to a save file or [ref:live-memory-patching]'s
address-based approach), reach for a Frida script targeting the relevant runtime
rather than reverse-engineering MTool's own binaries — same capability, and it's ours
to actually read, modify, and redistribute.

## Where this fits relative to the rest of the toolkit

This is a **detection and technique-selection aid**, not a replacement for anything
existing. For any given game: still check for a plain/simple save first
([ref:workflow]), still prefer an engine's own sanctioned unlock API when one exists
([ref:renpy-galleries]), and reach for interpreter hooking specifically when the goal
requires observing/intercepting live behavior (text, or a value that's computed
on-the-fly and never touches disk) rather than editing state that's already sitting in
a save file.
