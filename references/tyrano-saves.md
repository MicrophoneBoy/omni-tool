# TyranoScript saves

TyranoScript (and its paid sibling TyranoBuilder) is a Japanese HTML5 visual-novel
engine: scenario files are `.ks` scripts, game logic is JavaScript, and desktop builds
ship as an NW.js app. Worked case: **an NW.js-packaged TyranoScript visual novel**
(verified 2026-11-04).

## Spotting it

- A `tyrano/` folder next to `data/scenario/*.ks` in unpacked builds.
- NW.js builds often have neither: the whole game is a zip appended to the exe (the
  worked case was a single 1.1 GB `.exe` plus the usual Chromium DLLs, `nw.pak` and
  `locales/`). The only loose clue was the save file sitting next to the exe,
  `tyranoproject_sf.sav`. `detect_engine.py` matches on that.

## Save format

The file is `escape(JSON.stringify(obj))`, JavaScript's legacy `escape()`, not URL
encoding: ASCII outside `[A-Za-z0-9@*_+-./]` becomes `%XX`, and every character above
U+00FF becomes `%uXXXX`. Python's `urllib.parse.unquote` leaves the `%uXXXX` sequences
alone, which is the one trap here (it looks like it worked, but every non-Latin string
is still escaped). `scripts/tyrano/tyrano_save.py` has a small codec for it, and
re-encoding the untouched real save reproduced it byte for byte.

Two files, named after the project (`<project>` is usually `tyranoproject`):

| file | holds |
| --- | --- |
| `<project>_sf.sav` | `sf.*` **system variables**, shared by every slot. Gallery, recollection, ending and "cleared once" flags live here, because they must outlive any one save. |
| `<project>_tyrano_data.sav` | the save slots; each slot carries its own `f.*` game variables and the scenario position. |

On NW.js the files sit next to the exe (or in the working directory). Browser builds
keep the same strings in `localStorage` instead.

## Finding the flag names

Gallery flags are just `sf.<name>` assignments in the scenario scripts, so grep for
`sf.`. On an NW.js build you don't need to unpack anything: Python's `zipfile` opens
the exe directly, since a zip's directory is read from the end of the file.

```python
import zipfile, re, collections
z = zipfile.ZipFile('Game.exe')
hits = collections.Counter()
for n in z.namelist():
    if n.endswith('.ks'):
        hits.update(re.findall(r'sf\.(\w+)', z.read(n).decode('utf-8', 'replace')))
print(hits.most_common(40))
```

Older Japanese builds may store `.ks` files as Shift-JIS; decode with `cp932` if the
UTF-8 output is garbled.

In the worked case this showed the gallery (`sf.allchaplist`) was a static chapter list
that the title screen rebuilds from `chaplist.ks` on every launch, with no unlock
condition at all, so there was nothing to patch. That is SKILL.md step 4 ("verify the
lock actually exists") paying off again: check before you edit.

## Editing

```
python tyrano_save.py tyranoproject_sf.sav                        # pretty-print
python tyrano_save.py tyranoproject_sf.sav get cg_view
python tyrano_save.py tyranoproject_sf.sav set cg_view true       # value is JSON
python tyrano_save.py tyranoproject_sf.sav set replay.3 1         # dotted path, list index ok
```

`set` backs up (`.bak`, `.bak2`, ...), writes, then re-reads from disk and prints the
value, same as every other mutating script here. Close the game first: TyranoScript
rewrites `_sf.sav` on exit and on most system-variable changes, which would silently
undo the edit (see [ref:workflow]).
