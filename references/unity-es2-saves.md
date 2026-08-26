# Unity: Easy Save 2 (ES2) binary save format

Worked case: **Orbt XL** (`%USERPROFILE%\AppData\LocalLow\<Studio>\<Game>\dat01.orbtxl`).

Easy Save 2 is a popular Unity Asset Store save plugin. Its binary record format is a
flat, delimiter-based sequence with no compression and no encryption by default:

```
7E <name_len:u8> <name:ascii> <mid:4 bytes> FF <type_tag:4 bytes> <value:4 bytes> 7B
```

repeated back-to-back for every saved field. `name` is the ES2 tag/key you referenced
from game code (`ES2.Save(x, "tagName")`). `value` is 4 bytes, read as either `<i`
(int32) or `<f` (float32) depending on what you expect the field to hold — print both
interpretations when scanning, since the type tag isn't worth fully decoding for a
one-off edit.

## Reading every record

`scripts/unity_es2/es2_read.py` walks the whole file and prints
`offset, name, mid, tag, raw, as_int, as_float` for every record — run it first to find
the tag name you want (override the path with `ES2_SAVE=...`):

```
ES2_SAVE="C:\Users\me\AppData\LocalLow\Studio\Game\save.orbtxl" python es2_read.py
```

## Patching one field

`scripts/unity_es2/es2_set.py <tag> <value>` finds the record by tag name, patches the
4-byte int value in place, and verifies:

- Never overwrites an existing backup — auto-increments (`save.bak`, `save.bak2`, ...)
  so every prior state survives.
- Re-reads the file after writing and asserts the size didn't change (fixed-width
  in-place edit — a good sanity check that nothing shifted).
- Prints the full list of changed byte offsets so you can eyeball that only the
  intended bytes moved.

```
ES2_SAVE="...\save.orbtxl" python es2_set.py dat06 1750
```

Close the game before editing — like most Unity saves, ES2 files get rewritten by the
game itself on autosave/exit, which will silently revert an edit made while it's still
running (see [ref:workflow]).
