# PyInstaller-packaged Python games

Worked case: **a pygame sim game** (Python 3.11 + pygame, PyInstaller-packaged).

## Check the save first — it's very likely plain

Games built this way often just use `json.dump`/`json.dumps` for saves, with zero
encryption. The game's saves were plain JSON at
`%APPDATA%\<Game>\save\save{N}.json`, formatted with `indent=4` — editing top-level
keys directly (money key was `gold`) and round-tripping with
`json.dump(..., ensure_ascii=False)` (to preserve non-ASCII text) was the entire fix.
This is almost always faster than touching the packaged exe — check it before doing
anything below.

## If the value genuinely isn't in the save: patching the packaged exe

Sometimes a value is loaded from a *default* embedded in the game's own code and never
actually restored from the save on load (a real bug in some games, not a save format
issue) — confirmed by editing the save key, relaunching, and observing the game
silently reset it. In that situation the fix has to live in the packaged code, not the
save. This is high-effort and not guaranteed to work — treat it as a last resort.

- PyInstaller bundles game code as a `PYZ` archive (zipped, marshaled `.pyc` code
  objects) inside the exe, alongside a `CArchive` directory structure.
- **Python 3.12 can `marshal.loads()` a 3.11 code object, but must never
  `marshal.dumps()` it back** — re-serializing and re-embedding a 3.11 code object
  loaded under 3.12 produces a exe that crashes on import
  (`ValueError: too many values to unpack`). **Patch the raw marshaled bytes in place
  instead of round-tripping through `marshal.loads`/`dumps`.**
- Two marshal type tags are both fixed 5 bytes (`type_byte + int32`), which makes
  in-place patching tractable: `TYPE_INT` (`'i'`) and `TYPE_REF` (`'r'`, used when
  `FLAG_REF` is set for objects marshal may need to reference again). **Preserve the
  `FLAG_REF` bit** when identifying which tag byte you're looking at — flipping it
  changes the type tag's meaning, not just the value.
- The PYZ table-of-contents (TOC) format isn't guaranteed to be a `dict` — one build
  used a **list** instead. Preserve whatever type it already is when rebuilding; don't
  assume dict.

Locate the target constant by searching decompiled/disassembled bytecode (or just the
raw bytes, since small ints often appear as a literal in the constants table) for the
function that sets the default, then patch every constant occurrence — there can be
more than one copy of the same literal in different functions, and patching only one
may have no visible effect if another function's copy is what actually executes at the
point you care about (same "check for a later/different writer" lesson as
[ref:gamemaker-datawin]).

## When to stop

Not every value is reachable this way. The game's max-action-points cap resisted
every angle tried (save edit: written but ignored on load; default-data JSON edit: key
not even read by the loader; a related "increase max" skill: dead code, never
implemented by the stat-recalculation function; byte-patching the obvious constant and
rebuilding: applied cleanly but the value still reset after the in-game day-rollover
event, implying a *second*, unpatched copy of the constant elsewhere). After
exhausting the visible constant sites, further attempts need actual tracing of the
runtime call that performs the reset (e.g. disassembling the specific handler function
implicated by the symptom) rather than more guessing at "the" constant. If a user
explicitly calls off further attempts at a specific value, don't reopen it without a
new lead — repeating the same exhausted angles wastes time.
