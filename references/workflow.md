# Cross-game workflow

Lessons that showed up independently across at least two unrelated games. If you're
about to do something and it feels like you've done it before, check here first.

## Look for a plain save before reaching for anything harder

Order of increasing effort, and what to check for each before moving to the next:

1. **Plain JSON / INI / XML save file.** `grep` the save directory for `.json`,
   `.ini`, `.sav`, `.dat` and just open one in a text editor. a pygame sim game's entire
   save was `json.dumps(indent=4)` — money key `gold`, done in one edit.
2. **Trivially-decoded binary** (XOR, gzip, base64, a known third-party plugin format
   like Easy Save 2 or GVAS). Check the first few bytes against known magic numbers
   (`1F 8B` gzip, `GVAS`, `7E` ES2 record marker) — if the raw bytes don't match but
   XORing with a small constant does, it's obfuscation, not encryption.
3. **Engine-native encrypted/signed data** (Ren'Py persistent + ECDSA tokens, Godot
   `GDEC`). Usually has a documented or derivable key/password baked into the game's
   own code — check before assuming it's unrecoverable.
4. **Compiled bytecode holds the value, not the save** (Downwell's starting HP is a
   literal in `data.win`, never touches the save file at all). Only reach for a
   disassembler once you've confirmed the save genuinely doesn't contain what you want.
5. **Genuinely unrecoverable encryption with a key you can't derive** (a Unity IL2CPP management sim: AES-CBC via a key baked into a Unity asset bundle, impractical to pull out).
   Last resort: patch the *running game* instead of the save, via a mod loader
   (BepInEx) and a live inspector (UnityExplorer's C# console). See
   [ref:unity-il2cpp-saves].

Don't skip to step 4 or 5 without ruling out 1-3 first — every case where step 4/5 was
actually necessary, steps 1-3 were checked first and genuinely came up empty.

## Verify the thing you're about to patch actually exists

Before writing a fix, confirm the lock/gate you're about to bypass is real. Grep the
game's own script/config files for the condition first (`seen_label`, a persistent
flag, an `if unlocked` check). One gallery screen (a second Ren'Py visual novel) turned out
to have **no lock logic at all** — every scene was reachable from a fresh save via an
unconditional `Jump()`. The correct output there was "nothing to patch, here's the
evidence," not a fix for a lock that didn't exist.

## The game must be fully closed before you edit its save on disk

Games that flush save state periodically or on exit will silently overwrite your edit
if the process is still running when you write the file. Symptom: you patch the file,
launch the game, and it's back to the old value — the game read your edit, then wrote
the *old in-RAM* value back over it seconds later.

- Don't trust a process-name check to confirm the game is closed (`Get-Process -Name
  Foo*` can come back empty while the game is demonstrably still running under a
  different process/window name). Compare the save file's `LastWriteTime` before and
  after asking the user to close it, or just ask the user to confirm it's closed and
  watch the mtime yourself after your write.
- After the user relaunches, re-check the file's content (not just mtime) to confirm
  the game didn't revert it on load.

## "Secure*" / shadow-copy fields are a duplicate value, not real crypto

A field named `SecureCashSave`, `requisitionPointsOdometer`, or similar is usually a
plain second copy of the real value (often keyed by the value itself, e.g. a
`Map<int,Object>` whose single key IS the cash amount), used as a tamper check against
live memory editors. Patch it in lockstep with the real field or the game will notice
the mismatch. It is not a hash, checksum, or encrypted value — verify by just reading
it: if it decodes to a plausible plain int equal to (or trivially derived from) the
field you're already changing, that's what it is.

Distinguish this from an actual **content checksum** that must be recomputed — check
whether the field's value actually correlates with content before assuming either way.
One case (`SavedBytes` in a GVAS save) looked like a checksum but turned out to be
constant garbage across files with completely different content — not required at all,
and the game regenerated it fine when absent.

## Backup discipline

- Always write a backup before the first edit to a given file, this session.
- Never overwrite an existing backup — if one's already there, append a counter
  (`file.bak`, `file.bak2`, `file.bak3`, ...). See the pattern in
  `scripts/unity_es2/es2_set.py`. This preserves every prior known-good state, which
  matters if an earlier edit turns out to have been wrong.

## Verify by re-reading from disk, not from your in-memory buffer

After writing, open the file again (fresh read, not the `bytearray` you just wrote from)
and decode the field you changed. This catches encoding mistakes, wrong offsets, and
silent truncation that a "the write call didn't throw" check would miss. For
fixed-width in-place edits, also assert the file size didn't change — a good free
sanity check that you didn't accidentally shift anything.

## For compiled bytecode: find write sites by name, check for a later override

Never hardcode a byte offset for a value you want to patch — engines version their
bytecode/asset layout across builds, and a hardcoded offset silently patches the wrong
thing (or crashes) on the next patch/build. Instead:

- Resolve the *name* of the variable/field you want (via the format's own name table —
  GameMaker's `VARI`/`FUNC` chunks, Unreal's serialized property names, etc.) and
  search for references to that name.
- Once you find a candidate write site, check whether something else writes to the same
  target *afterward* in the normal execution order. Downwell assigns starting HP in two
  places — a base initializer, then a per-playstyle switch that runs after it and wins.
  Patching only the first one produces a fix that "does nothing" in game, which is a
  very confusing failure mode if you don't know to look for the second writer.

## When there's no save file worth editing

If you've ruled out steps 1-3 above and the value genuinely only exists in compiled
bytecode or live memory, see [ref:gamemaker-datawin] for the bytecode-patching
approach or [ref:live-memory-patching] for the engine-agnostic live-memory fallback
(AOB scanning, pointer chains, DLL injection + IPC, and when to reach for Ghidra/IDA
instead of extending a hand-rolled parser). If you want to dry-run a new technique
before touching a real save you care about, Pwn Adventure 3 is a game built
specifically as a legal RE practice target — see [ref:live-memory-patching].

## Confirm with a real launch, not just static analysis

Decoding the format correctly and writing a plausible-looking value isn't the same as
the game actually reading it that way. Where possible, launch the actual game after
patching (or have the user do it) and check the in-game state, not just that the file
round-trips through your parser.
