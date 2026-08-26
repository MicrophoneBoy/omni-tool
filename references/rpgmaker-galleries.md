# RPG Maker: gallery/recollection unlocks (RGSS and MV/MZ)

No worked case yet in this toolkit — unlike every other reference doc here, this one
hasn't been run against a real game's actual files. Treat the save-format section as
"well-documented public RPG Maker engine knowledge, needs verification against a real
save the first time it's used," same confidence level as a new engine we haven't
touched yet, not a proven recipe like [ref:renpy-galleries].

## Why RPG Maker galleries are usually easier to generalize than Ren'Py's

Both classic RPG Maker (XP/VX/VX Ace, scripted in Ruby via **RGSS**) and RPG Maker
MV/MZ (scripted in JavaScript, running on NW.js) track all progress through two flat,
indexed arrays that are core to the engine itself, not something each game reinvents:

- **Switches** — a big array of booleans (MV/MZ ships 10,000 slots by default),
  referenced by index, the engine's native "has X happened" flag.
- **Variables** — a parallel array of numbers, for counters/progress values.

A CG/scene gallery plugin (whether built into the game or a common third-party
plugin) almost always gates each unlockable entry behind a specific switch or
variable threshold — or, more usefully for us, behind a plugin class with a small,
predictable method surface (an "is this unlocked" check, an "item count" getter) that
many *different* games share, because the plugin itself is a shared community
download rather than something each dev writes from scratch. That's the opening: a
patch targeting the *plugin's* class/method names generalizes across many games built
with that plugin, the same way patching a common library function beats patching
every call site.

## Two ways to approach an unlock, in order of preference

### 1. Check the save file first (see [ref:workflow])

RPG Maker MV/MZ saves are `JSON.stringify()` of the game's state objects (including
`$gameSwitches._data` and `$gameVariables._data`), then compressed with **LZString**
(`LZString.compressToBase64`, a well-known, standalone JS compression library — not
proprietary to any one game) and written to a `.rpgsave` file (or `localStorage` for
browser deploys). If this holds for a specific game, unlocking is a plain save edit —
decompress with any LZString-compatible implementation, flip the specific switch
indices a gallery plugin checks (or all of them, since the array is fixed-size and
"everything true" is a safe sledgehammer if you don't know which indices matter),
recompress, write back. No running process, no injection, no interpreter access
needed at all — strictly simpler and safer than every technique below, consistent with
this toolkit's general ordering (see [ref:workflow]).

Classic RPG Maker (RGSS) saves are Ruby `Marshal.dump` of the game state — a
different, Ruby-specific serialization format, not JSON/LZString. Whether switches are
reachable the same way needs checking against a real save the first time this comes
up.

### 2. If the save doesn't hold it (or you need it live): patch the plugin's class surface

When state isn't cleanly editable at rest — or the unlock check depends on something
computed at runtime rather than a stored flag — the fallback is live-patching the
gallery plugin's own class methods rather than the underlying switches/variables
array, using [ref:interpreter-hooking]'s pattern:

- **RGSS (Ruby)**: identify the gallery plugin in use (common ones expose
  recognizable class/module names) and monkey-patch its "is this unlocked" accessor
  method to unconditionally return true, rather than trying to set every switch a
  given plugin instance might check.
- **MV/MZ (JavaScript)**: RPG Maker's built-in gallery/recollection classes are
  `Window_RecList` (the list UI, with an item-validity check) and `Scene_Recollection`
  (the scene wrapper) — patch the validity/enabled check on the list window to always
  return true, and/or force the switches array to all-true across its full index
  range. Because this is just JavaScript running in an NW.js/Node context, this can be
  done via **any general JS injection/DevTools-protocol approach** for an NW.js app,
  not necessarily a native DLL hook — worth checking whether the target simply exposes
  a debug/DevTools port before reaching for anything more invasive.

## Where this sits relative to the rest of the toolkit

- Prefer the save-file approach (§1) whenever it holds — it's the same "check for a
  plain/simple save first" principle as everything else in [ref:workflow].
- The live-patch approach (§2) is [ref:interpreter-hooking]'s general pattern applied
  to this specific engine family — see that doc for engine detection (RGSS DLLs,
  `www/`+`package.json`+NW.js exe for MV/MZ) and why hooking the interpreter beats
  chasing a memory address.
- Both approaches generalize better across *different* RPG Maker games than
  [ref:renpy-galleries]'s technique does across different Ren'Py games, because RPG
  Maker's switches/variables model and common community plugins give you a much
  smaller, shared surface to target instead of each game's bespoke label set.
