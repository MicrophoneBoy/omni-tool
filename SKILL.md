---
name: omni-tool
description: "Toolkit and playbook for editing single-player game save/persistent data — unlocking gallery/replay content, changing money or stats, or otherwise modifying local game state without playing through it. Covers Ren'Py (seen-label galleries, RPA archives), Unity (IL2CPP saves, Easy Save 2 binary records, live BepInEx/UnityExplorer patching), Godot (GDEC encrypted saves, PCK archives), Unreal Engine (GVAS saves), and GameMaker (data.win bytecode patching). Use when asked to unlock content, edit a save file, or modify a game's persistent state."
license: MIT
user-invocable: true
tags: [game-modding, save-editing, reverse-engineering]
---

# omni-tool

A playbook and script collection for editing single-player game state: save files,
persistent data, and (when there's no save-file shortcut) compiled bytecode. Built up
one game at a time — each `references/` doc is a real, previously-solved case.

## How to approach a new game

Work in this order. Most of the cost in past sessions came from skipping straight to
step 4 when steps 1-3 would have solved it in minutes.

1. **Find the save/persistent data first.** Check the obvious locations before touching
   anything else — see [ref:workflow] "where saves live". A large fraction of games
   (a pygame sim game, Iron Nest, One-armed robber, Orbt XL) store everything in a plain or
   trivially-decodable file. Don't reach for a bytecode patcher or a memory scanner
   until you've confirmed the save format actually resists editing.
2. **Identify the engine**, since it tells you the save format family:
   - Ren'Py (`.rpy`/`.rpyc` in `game/`, `renpy/` SDK folder) → [ref:renpy-galleries],
     [ref:rpa-archives]
   - Unity (`UnityPlayer.dll`, `*_Data/` folder) → check for IL2CPP vs Mono first
     (`GameAssembly.dll` present = IL2CPP; a `Managed/` folder of plain .NET
     assemblies with no `GameAssembly.dll` = Mono, see [ref:unity-mono-saves] for a
     completely different toolchain), then [ref:unity-il2cpp-saves] or
     [ref:unity-es2-saves]
   - Godot (`.pck`, `project.godot` strings in the exe) → [ref:godot-saves]
   - Unreal Engine (`.pak`, `-WindowsNoEditor.pak`, `GVAS` magic in save files) →
     [ref:unreal-gvas-saves]
   - GameMaker (`data.win`, `options.ini`) → [ref:gamemaker-datawin]
   - PyInstaller-packaged Python (`_internal/` folder, `.pyz`/`base_library.zip`) →
     [ref:pyinstaller-python-saves]
3. **Check whether the engine has its own sanctioned mechanism** for what you're trying
   to do before hand-editing binary state. Example: Ren'Py galleries are gated by
   `renpy.seen_label()`, and Ren'Py ships `renpy.mark_label_seen()` /
   `renpy.save_persistent()` specifically to unlock them — using it means the game
   signs its own persistent file correctly, instead of you needing to forge an ECDSA
   signature. See [ref:renpy-galleries].
4. **Verify the lock actually exists before patching it.** Not every gallery/replay
   screen is gated — one build had zero unlock logic (every chapter reachable from a
   fresh save), and the "fix" was reporting that back, not writing a patch. Grep the
   engine's script files for the lock condition (`seen_label`, `unlocked`, a persistent
   flag) before assuming one exists.
5. **Back up, edit, verify by re-reading from disk, then have the user confirm in a live
   launch.** See [ref:workflow] for the recurring gotchas (game must be fully closed,
   shadow-copy/"Secure*" fields, in-place vs resizing edits).

## Reference index

- [ref:workflow] — cross-game lessons: where to look first, backup discipline, the
  "secure/shadow copy" pattern, why a process check isn't enough to confirm a game is
  closed, verifying patches by re-reading from disk.
- [ref:renpy-galleries] — `renpy.seen_label()` / `persistent._seen_ever`, the
  `mark_label_seen()` + `save_persistent()` fix, ECDSA-signed persistent files, and how
  to confirm a gallery has no lock at all before patching one.
- [ref:rpa-archives] — RPA-3.0 archive format (header, XOR-keyed pickle index),
  extracting specific files without unpacking everything.
- [ref:unity-il2cpp-saves] — gzip+XOR custom save formats, anti-tamper "odometer"
  shadow fields that live in memory only, BepInEx + UnityExplorer live C# patching for
  saves that are genuinely encrypted with an unrecoverable key.
- [ref:unity-es2-saves] — Easy Save 2 (asset-store plugin) binary record format:
  `7E <len> <name> <mid> FF <type> <value> 7B`, fixed-width in-place patching.
  (scripts/unity_es2)
- [ref:godot-saves] — Godot 4.x `GDEC` encrypted-file format (AES-256-**CFB128**, not
  CBC), embedded PCK v3 archives, and `GDSC` compiled-script token buffers for finding
  the password/keys without a decompiler.
- [ref:unreal-gvas-saves] — GVAS save format, `Secure*` shadow-copy map properties,
  Steam Cloud duplicate saves, why edits made while the game is running get silently
  reverted.
- [ref:gamemaker-datawin] — `data.win` IFF chunk format, bytecode-17 disassembly,
  finding literal-assignment write sites by name instead of hardcoded offsets, checking
  for a later writer that overrides your patch. (scripts/gamemaker)
- [ref:pyinstaller-python-saves] — PyInstaller-packaged Python games: check for plain
  JSON saves first, and (last resort) in-place marshal-bytecode patching without
  re-serializing a code object built by a different Python version.
- [ref:unity-mono-saves] — Mono vs IL2CPP Unity builds need entirely different
  tooling: ILSpy/dnSpyEx to decompile and patch the managed assembly directly, Cheat
  Engine's Mono dissector instead of UnityExplorer.
- [ref:live-memory-patching] — engine-agnostic live memory editing when there's no
  save file worth editing and no mod-loader console available: AOB scanning, pointer
  chains, freeze-vs-patch, DLL injection + IPC, and when to reach for Ghidra/IDA
  instead of a hand-rolled parser.

## Further reading

- [dsasmblr/game-hacking](https://github.com/dsasmblr/game-hacking) — broad curated
  index of game-hacking tools/tutorials/communities; useful as a jumping-off point
  when a new game needs an approach not yet covered above. Its companion repo,
  `dsasmblr/hacking-online-games`, is deliberately **not** linked here — it's scoped to
  live online-multiplayer exploitation, out of scope for this single-player-only
  toolkit (see Ground rules below).

## Scripts

- `scripts/renpy/rpa_list.py`, `rpa_extract.py` — list/extract files from an RPA-3.0
  archive. `python rpa_list.py game/scripts.rpa`,
  `python rpa_extract.py game/scripts.rpa out_dir/ gallery/`
- `scripts/gamemaker/` — `dw_chunks.py` (dump IFF chunks), `dw.py` (load
  strings/code-entries), `dw_names.py` (VARI/FUNC lookup by pattern), `dw_dis.py`
  (disassembler), `dw_refs.py` (all reads/writes of a variable name, with owning
  script), `dw_hp.py` (worked example: find and patch every literal-assignment site for
  a given global). All are GameMaker bytecode-17 tools written against Downwell but
  generic to any data.win of that bytecode version — override the target path with the
  `DW_DATA_WIN` env var.
- `scripts/unity_es2/` — `es2_read.py` (dump every record), `es2_set.py` (patch one
  field by tag name). Written against Orbt XL but generic to any Easy Save 2 binary
  save — override the target path with the `ES2_SAVE` env var.

## Ground rules (apply to every game)

- **Single-player/offline-save editing only.** This toolkit edits state on your own
  machine in games you own — it does not build or use cheats against other real
  players in live online matches (aimbots, ESP, anti-cheat evasion, server-side
  exploits). When reviewing outside source material, exclude anything scoped to live
  online multiplayer even if the underlying technique (memory scanning, DLL
  injection) overlaps with what we do — the target and intent are what matter, not
  just the mechanism.
- Never edit a save while the game is running — see [ref:workflow].
- Always back up before the first write, and never overwrite an existing backup (append
  a counter instead) — see the pattern in `es2_set.py`.
- After writing, re-read the file from disk and print the new value back. Don't trust
  the in-memory buffer you just wrote.
- If a value is a shadow-copied/"Secure*" field, patch every copy, not just the
  human-readable one.
- Ask the user to confirm the result in an actual live launch before considering the
  task done — static analysis of the format is not the same as verifying the game
  reads it the way you think it does.
