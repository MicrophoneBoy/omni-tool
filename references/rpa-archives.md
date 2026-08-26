# Ren'Py RPA-3.0 archive format

Ren'Py packs `game/`'s scripts and assets into `.rpa` files (e.g. `scripts.rpa`) when
the dev ships a "compiled" distribution instead of loose files. Format:

```
line 1 (text header):  RPA-3.0 <offset_hex> <key_hex>\n
at <offset>:            zlib-compressed pickle of {filename: [(off, len, prefix), ...]}
```

- `offset` and `key` are hex integers parsed straight off the header line.
- Every `(offset, length)` pair in the index (for entries with 3 elements — 2-element
  legacy entries are already plain) is **XORed with `key`** before use.
- `prefix` is raw bytes prepended to the file's content (empty for most files); under
  Python 3, unpickling data written by Python 2 can hand you `prefix` back as `str`
  instead of `bytes` — coerce with `prefix.encode('latin-1')` before concatenating, or
  you'll hit `TypeError: can only concatenate str (not "bytes") to str`.

Both scripts below only need the archive path — no per-game constants.

`scripts/renpy/rpa_list.py` — list every filename in the archive:

```
python rpa_list.py path/to/scripts.rpa
```

`scripts/renpy/rpa_extract.py` — extract files matching a substring filter (omit the
filter to extract everything):

```
python rpa_extract.py path/to/scripts.rpa out_dir/ gallery/
```

Archives commonly include both `.rpy` (source) and `.rpyc` (compiled) for each file —
extract and read the `.rpy` source directly rather than dealing with `.rpyc`
deserialization.
