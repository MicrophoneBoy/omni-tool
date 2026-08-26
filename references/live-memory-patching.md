# Live memory patching (when there's no save file worth editing)

Last resort in the [ref:workflow] ordering — reach for this only after confirming the
save is genuinely unrecoverable (real encryption with a key you can't derive) or the
value you want literally isn't persisted anywhere on disk. Our worked case for the
"mod-loader console" version of this is a Unity IL2CPP management sim
([ref:unity-il2cpp-saves]: BepInEx + UnityExplorer's C# console). This doc covers the
more general, engine-agnostic fallback for when no such mod-loader ecosystem exists for
the engine you're looking at.

## The general technique: AOB scan → pointer chain → patch or freeze

When there's no mod loader to hand you live object references via reflection (the way
UnityExplorer does for Unity), you find a value in another process's memory the manual
way:

1. **Array-of-bytes (AOB) / pattern scan.** Search the process's memory for a byte
   pattern with wildcards (e.g. the surrounding instruction bytes near where a value is
   read/written), rather than a fixed address — addresses shift between game versions
   and even between runs (ASLR), but the surrounding code pattern is usually stable.
2. **Resolve a pointer chain** (`module_base + static_offset -> ptr -> +offset -> ...`)
   from the scan hit back to the actual value, so the address stays valid across
   restarts instead of being a one-off hit you have to re-find every session.
3. **Patch (one-time write) or freeze (repeated write on a timer/thread)** depending on
   whether you want a permanent change or to hold a stat constant (e.g. infinite HP) —
   freezing is a distinct technique from a one-time edit, useful when something else
   keeps re-writing the value you want fixed.
4. Same float-vs-int gotcha as [ref:unity-il2cpp-saves]: confirm the value's actual
   type before scanning, since scanning for the wrong width/type silently finds
   nothing.

### Tools

- **[Cheat Engine](https://www.cheatengine.org/)** — the default GUI tool for all of
  the above; has a **Mono dissector** specifically for Mono-based Unity games (see
  [ref:unity-mono-saves]) that resolves managed objects the way UnityExplorer does for
  IL2CPP.
- **memory.dll** (github.com/erfg12/memory.dll) — C# library wrapping the same
  primitives (attach by process id/name, typed read/write, AOB scan with masking,
  pointer-chain resolution, freeze-via-thread, DLL injection with named-pipe IPC) for
  building a standalone trainer instead of using Cheat Engine interactively. Windows
  only, .NET build dependency — useful when you want a scriptable/repeatable trainer
  rather than manual GUI work.
- **Squalr** (github.com/Squalr/Squalr-Sharp) — open-source, actively maintained C#/
  .NET Cheat-Engine-class scanner (GPLv3). Notable: constraint-based scanning via
  `ManualScanner`/`ValueCollector` (multi-type comparative filtering across snapshots)
  and a **C# scripting API** (`CsScript`) for automating a scan/patch instead of manual
  GUI steps — the scriptable-alternative angle worth reaching for if UnityExplorer
  isn't available (non-Unity engine, or Mono without the dissector set up). Needs
  SSE/AVX CPU support for its SIMD scanner; build from source (VS2017+), no simple
  installer.
- **pyMeow** (github.com/qb-0/pyMeow) — Python library (compiled from Nim) for
  process memory read/write, Windows + Linux. Lower-level than the above: it gives you
  the read/write primitive but **no object-graph walker** — you still have to find the
  address yourself via pattern scan or pointer chain, it doesn't do IL2CPP/Mono-aware
  discovery the way UnityExplorer does. Useful once you already know the address (e.g.
  confirmed via Cheat Engine first, then automated in a Python script), not a
  replacement for the discovery step. Its own example gallery is ESP/aimbot-oriented —
  a signal it's commonly used for online-multiplayer cheat dev, which is out of scope
  for this toolkit; cite the primitive, not the use case.

## Engine-agnostic fallback: DLL injection + IPC

When there's no existing mod-loader ecosystem at all for an engine (no BepInEx
equivalent), the generic pattern is: inject a DLL into the running game process, and
control it from an external process via a named-pipe (or socket) IPC channel. This is
what BepInEx effectively automates for you on Unity — doing it by hand is the fallback
for engines nothing like BepInEx exists for. No specific worked case yet in this
toolkit; treat as a documented option, not a battle-tested recipe.

## Static analysis for anything too complex for a hand-rolled parser

Our GameMaker (`data.win`) and Ren'Py (RPA) parsers in `scripts/` are hand-rolled
because those formats are simple enough to reverse by inspection. For a compiled
native binary (a custom engine, or a format too complex to reverse by hand), reach for
a real disassembler — **Ghidra** (free, NSA-developed) or **IDA Pro** — instead of
trying to extend a hand-rolled parser past what it can reasonably handle.

## Practicing before touching a real game

**Pwn Adventure 3** is a game built specifically as a legal reverse-engineering
practice target (referenced from a curated online-game-hacking resource list) — a
lower-risk place to try a new scanning/patching technique for the first time than
experimenting directly on a real save you care about.
