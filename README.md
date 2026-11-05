# Omni Tool

A Claude Code skill for editing single-player game save/persistent data — unlocking
gallery/replay content, changing money or stats, or otherwise modifying local game
state without playing through it.

Built up one real, previously-solved game at a time rather than written from theory:
Ren'Py gallery unlocks, Unity (IL2CPP and Mono) save formats and live memory patching,
Godot's encrypted save format, Unreal Engine's GVAS saves, GameMaker bytecode
patching, RPG Maker MV/MZ and TyranoScript saves, SQLite saves, PyInstaller-packaged
Python games, and a generic engine-agnostic live
memory-patching fallback for everything else.

**Scope:** single-player/offline save editing on your own machine, in games you own.
Not cheats against other real players in live online multiplayer.

## Layout

- `SKILL.md` — the entry point: how to approach a new game, and an index into
  everything below.
- `references/` — one doc per engine/format, plus `workflow.md` for lessons that
  recurred across multiple unrelated games (backup discipline, why a game must be
  fully closed before you edit its save, how to spot a shadow-copy anti-tamper field,
  etc.).
- `scripts/` — real, runnable tooling: an engine detector (`detect_engine.py`), Ren'Py
  RPA archive extraction, GameMaker `data.win` bytecode disassembly/patching, Unity
  Easy Save 2 record patching, SQLite save inspection/patching, RPG Maker MV/MZ save
  inspection/patching, TyranoScript save editing. Every script prints usage with
  `--help`.

## Using this with Claude Code

Clone it and link it into your personal skills folder so edits to the repo go live:

```powershell
git clone https://github.com/MicrophoneBoy/omni-tool
New-Item -ItemType Junction -Path "$env:USERPROFILE\.claude\skills\omni-tool" -Target "$PWD\omni-tool"
```

(macOS/Linux: `ln -s "$PWD/omni-tool" ~/.claude/skills/omni-tool`.) A project-level
`.claude/skills/omni-tool/` works too. Claude Code then lists it as an invocable skill. See `SKILL.md` for the actual playbook.
