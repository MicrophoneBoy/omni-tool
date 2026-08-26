# GameMaker: `data.win` bytecode patching

Worked case: **Downwell** (bytecode version 17, GameMaker Studio).

Use this only after confirming the value you want isn't in the save file at all —
GameMaker `.ini`-style saves are usually plain and worth checking first (see
[ref:workflow]). Downwell's `save.ini` held only meta stats; starting HP was a literal
baked into compiled bytecode, never touching the save.

## Container format (IFF)

```
'FORM' | total_size:u32 | chunks...
each chunk: name:4-char-ascii | size:u32 | payload
```

Relevant chunks: `STRG` (string table), `CODE` (per-script/event bytecode), `VARI`/
`FUNC` (name tables the bytecode references by index/offset-chain), `GEN8` (general
game info, e.g. bytecode version, internal name).

- **`STRG` pointer trap:** each entry's pointer targets a `length:u32` field, and the
  actual characters start **4 bytes past that**, not at the pointer itself. Reading the
  chars starting at the raw pointer value gives garbage.
- **`CODE` entry layout:** `name_ptr:u32, length:u32, locals:u16, args:u16,
  rel_offset:i32` where `rel_offset` is **relative to the position of that field
  itself**, not to the entry start — the actual bytecode lives in a shared blob at
  `field_position + rel_offset`. Multiple names can alias the same bytecode (e.g.
  `gml_Script_foo` and `gml_GlobalScript_foo`).

## Two traps that produce plausible-but-wrong output

1. **Opcode table version.** Bytecode 15+ uses one numbering
   (`add=0x0C, sub=0x0D, and=0x0E, or=0x0F, xor=0x10, ...`); older bytecode versions
   shift the arithmetic ops down by 4 (`conv=0x03` instead of `0x07`, etc.). Mixing
   tables still decodes branches/calls/strings correctly (so it *looks* plausible)
   while silently mislabeling every arithmetic op — the tell is a suspicious run of
   `mod.i.v` sitting between pushes and a call where an `add` would make more sense.
   Confirm your table against the game's actual bytecode version (`GEN8` chunk) before
   trusting a disassembly.
2. **Name resolution via occurrence chains, not the packed reference index.** `VARI`/
   `FUNC` entries store an occurrence count and the offset of the **first** referencing
   instruction; the word at `instr_offset + 4` (low 24 bits) holds the delta to the
   *next* occurrence, forming a linked chain through every reference to that name.
   Walking these chains to build `offset -> name` is far more reliable than trying to
   decode the reference's packed index field directly. `VARI` entries are 20 bytes each
   after a 12-byte chunk header — trust the chunk size to compute the count, not
   whatever count field the header claims.

## Instruction word layout (bytecode 15+)

`opcode = byte 3` (top byte), `type1 = nibble 4`, `type2 = nibble 5`,
`low u16 = int16 immediate / instance-type / argc` depending on opcode. Value types:
`0 double, 1 float, 2 int, 3 long, 4 bool, 5 var, 6 string, 15 int16`. Instance types
(for the low i16 of a var-referencing instruction): `-1 self, -2 other, -5 global,
-6 builtin, -7 local, -9 stacktop, -15 argument`.

## Finding and patching a literal write site

A literal integer assignment to a global (`global.playerHp = 4`) compiles to
`pushi.e <value>` (a 4-byte instruction, `0x840F0000 | int16`, **no separate operand
word** — the immediate is packed into the instruction word itself) immediately
followed by a `pop.*.v` writing to the target variable. To find every such site:

1. Resolve the variable's name → every instruction offset that references it (via the
   occurrence chain above).
2. Keep only offsets where the instruction is a `pop` (a write, not a read).
3. Check the 4 bytes immediately before each write: if they match `pushi.e`
   (`word & 0xFFFF0000 == 0x840F0000`), it's a patchable literal — anything else means
   the value is computed at runtime, not a literal, and isn't safely patchable this way.
4. **Check for a later writer that overrides yours.** Downwell assigns starting HP in
   `gml_GlobalScript_scrPlayerGlobalStat` (base reset), then
   `gml_GlobalScript_styleUpdate` runs *afterward* and re-assigns it per playstyle —
   patching only the first script produces a change that "does nothing" in game. Use
   the owning-script index (map each instruction offset back to which `CODE` entry it
   falls inside) to confirm you've found every relevant writer, and specifically
   whether any of them execute after the others in the normal call order.
5. Don't patch every literal write to the variable — some are semantically different
   (e.g. `playerHp = 0` on death is a different write site than the run-start
   initializer; patching it would change death behavior, not starting HP).

Because `pushi.e` is a fixed 4-byte instruction with the immediate packed into the
instruction word (a `int16` sub-field), patching is a **2-byte in-place swap** — the
file size never changes, a good sanity check that the patch was applied correctly.

GameMaker does not checksum `data.win`, but **Steam's "verify integrity of game files"
will silently revert this kind of patch** — warn the user before they run it.

## Scripts (`scripts/gamemaker/`)

- `dw_chunks.py` — dump the top-level IFF chunk layout.
- `dw.py` — load string table + `CODE` entries (`load()` → `(data, chunks, strings,
  code_entries)`).
- `dw_names.py` — list `VARI`/`FUNC` names matching a regex, with occurrence count and
  first-reference offset.
- `dw_dis.py` — full disassembler; `context()` builds the offset→name maps via the
  occurrence-chain walk, `dis(...)` renders a code entry as text.
- `dw_refs.py` — every read/write reference to a variable name, tagged `READ`/`WRITE`
  with its owning script (via `owner_index`/`owner_of`).
- `dw_hp.py` — full worked example: locate every literal-assignment site for a set of
  target variable names restricted to specific "init" scripts, print them, and
  optionally patch all of them to a new value with backup + re-read verification.
  Adapt the `TARGETS`/`INIT_SCRIPTS` constants for a different game/variable.

All scripts default to a `data.win` path via a `DW_DATA_WIN` env var override — set it
before running against a different game.
