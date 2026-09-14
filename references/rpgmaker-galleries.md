# RPG Maker: gallery/recollection unlocks (RGSS and MV/MZ)

## Why RPG Maker galleries are usually easier to generalize than Ren'Py's

Both classic RPG Maker (XP/VX/VX Ace, scripted in Ruby via **RGSS**) and RPG Maker
MV/MZ (scripted in JavaScript, running on NW.js) track all progress through two flat,
indexed arrays that are core to the engine itself, not something each game reinvents:

- **Switches** — a big array of booleans (MV/MZ ships 10,000 slots by default),
  referenced by index, the engine's native "has X happened" flag.
- **Variables** — a parallel array of numbers, for counters/progress values.

A CG/scene gallery, whether it's a hand-built set of common events (the RPG Maker MZ game
case below) or a shared third-party plugin, almost always gates each unlockable entry
behind one specific switch — or, more usefully for us, **a game's own `data/System.json`
ships human-readable names for every switch/variable slot**, since that file is what
the editor itself uses to label them. That means you can often find the exact index you
need by searching switch *names* before ever touching a save, without knowing anything
about which plugin (if any) the game uses.

## MV/MZ save format (confirmed against a real game)

Worked case: **an RPG Maker MZ game** (RPG Maker MZ, NW.js, `js/rmmz_core.js` present, deployed
"loose" — i.e. `package.json`/`js/`/`data/`/`save/` sit directly at the game root with
no `www/` wrapper folder, which is common enough that [ref:workflow]'s engine detector
had to be updated to not require one).

**The save is not what it looks like at a byte level.** `StorageManager.jsonToZip` (in
`js/rmmz_managers.js`) does:

```js
const zip = pako.deflate(json, { to: "string", level: 1 });
```

`pako`'s `to: "string"` output mode is a JS *binary string*: one UTF-16 code unit per
raw deflate byte, values 0–255 (`String.fromCharCode(byte)` for each byte — confirmed by
reading pako's own source, bundled at `js/libs/pako.min.js`). That string is then handed
to `fs.writeFileSync(path, zip)` with no encoding argument, so Node **UTF-8-encodes the
string** to actually write the file. Net effect: every byte 0x80–0xFF in the real
deflate stream becomes a 2-byte UTF-8 sequence on disk, and the `.rmmzsave` file's raw
bytes are *not* the deflate stream — they're UTF-8 text that happens to decode back to
one code point per original byte.

To recover the real stream: decode the file as UTF-8 text, then map each character's
code point back to a single byte (`bytes(ord(c) & 0xFF for c in text)`), then
`zlib.decompress(raw, 15)` (standard zlib format — the `0x78 0x01` you'll see at the
start of the reconstructed bytes is a real, checksum-valid zlib header, not a
coincidence). Writing back is the same transform in reverse: `zlib.compressobj(1,
zlib.DEFLATED, 15)` (level 1, matching the game), then `''.join(chr(b) for b in
compressed_bytes)`, then `.encode('utf-8')`, written in binary mode.

**Read the file in binary mode and decode manually.** Opening it with
`open(path, encoding='utf-8')` in Python's default text mode applies universal-newline
translation, which silently collapses any embedded `\r\n` (or lone `\r`) byte pair
inside the compressed stream. This is exactly what happened the first time this was
tried against the game's real save: decompression produced ~3KB of correct,
readable JSON and then failed with `invalid distance too far back` — a classic symptom
of a stream that's correct up to one silently-dropped byte. Re-reading in `'rb'` mode
and decoding the bytes explicitly fixed it immediately. `scripts/rpgmaker/` has this
already handled.

**Once decompressed, it's normal JSON, but wrapped.** `JsonEx.stringify` (MZ's own
serializer) wraps every engine class instance as `{"_data": <plain value>, "@":
"ClassName"}` so the class identity survives the round trip. The flat arrays you
actually want are one level down:

- `switches._data` — a JS array, `Game_Switches`, indexed exactly by switch ID,
  `true`/`false`/`null` (unset).
- `variables._data` — same shape, `Game_Variables`, holding numbers.
- `selfSwitches._data` — `Game_SelfSwitches`, but this one's a *dict* keyed by
  `"mapId,eventId,letter"` strings (self-switches are per-event local A/B/C/D flags,
  not part of the global switches array) — less commonly relevant to gallery unlocks,
  but worth knowing it's shaped differently if you go looking for it.

Classic RPG Maker (RGSS, XP/VX/VX Ace) saves are Ruby `Marshal.dump` of the game
state — a different, Ruby-specific serialization format, not JSON/pako. Whether
switches are reachable the same way is still unconfirmed; this toolkit hasn't run
against a real RGSS save yet.

## Finding the right index without a save at all

`data/System.json` ships with every MV/MZ game and has `"switches"` and `"variables"`
arrays of names, indexed identically to the runtime arrays — this is literally what the
RPG Maker editor displays instead of raw numbers, so a dev who names their switches at
all (most do, at least for anything they need to find again) gives you a free index.
`scripts/rpgmaker/mz_save_inspect.py --names data/System.json <keyword>` searches it.

In that game, searching for "回想" (the standard JP term for a CG/scene recollection
room) turned up ~45 hits: switches 2703–2745, each named after a specific scene (e.g.
"（回想）マシロが憲兵に誘拐①" — "(Recollection) Mashiro kidnapped by MPs ①"), switch
1807 gating the recollection room's menu entry itself, and — worth specifically checking
for on any new game before individually flipping dozens of entries — **switch 2748,
named literally "全開放した" ("unlocked everything")**: a single master flag the game's
own event logic already uses to bypass every individual check. One switch, patched with
`mz_save_set.py`, verified by reloading and reading it back. Always check for a
game's own all-in-one unlock switch/variable before assuming you need to enumerate and
flip each entry — it's strictly less blast radius and it's common enough to be worth
the one extra name search.

## When there's no clean save-file shortcut: patch live instead

When state isn't cleanly editable at rest — no save yet, or the unlock check depends on
something computed at runtime rather than a stored flag — fall back to live-patching via
[ref:interpreter-hooking]'s pattern:

- **RGSS (Ruby)**: identify the gallery mechanism in use and monkey-patch its "is this
  unlocked" accessor method to unconditionally return true, rather than trying to set
  every switch a given implementation might check.
- **MV/MZ (JavaScript)**: the built-in gallery/recollection classes are
  `Window_RecList` (list UI, with an item-validity check) and `Scene_Recollection`
  (scene wrapper) when a game uses them — patch the validity/enabled check to always
  return true, and/or force the switches array true across the range you care about.
  Since this is plain JavaScript in an NW.js/Node context, any general JS
  injection/DevTools-protocol approach works — check whether the target exposes a
  debug/DevTools port before reaching for anything more invasive.

## Where this sits relative to the rest of the toolkit

- Prefer the save-file approach above whenever it holds — same "check for a plain/simple
  save first" principle as everything else in [ref:workflow], and now a proven recipe
  for MV/MZ specifically, not just documented theory.
- The live-patch fallback is [ref:interpreter-hooking]'s general pattern applied to this
  engine family — see that doc for engine detection and why hooking the interpreter
  beats chasing a memory address.
- Both approaches generalize better across *different* RPG Maker games than
  [ref:renpy-galleries]'s technique does across different Ren'Py games, because the
  switches/variables model (and `System.json`'s free name index) gives you a much
  smaller, shared surface to target instead of each game's bespoke label set.

(scripts/rpgmaker)
