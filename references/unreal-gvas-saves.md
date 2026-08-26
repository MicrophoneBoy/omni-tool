# Unreal Engine: GVAS save format

Worked case: **One-armed robber** (UE 4.27).

## Format

Many UE4/UE5 games save with **no compression, no encryption, no checksum** — a raw
`GVAS` container:

```
'GVAS' | package version | engine version string (e.g. "++UE4+Release-4.27") |
custom-version GUID table | savegame class path | serialized properties...
```

Properties serialize as `(name, type, size, value)` tuples — `IntProperty`,
`FloatProperty`, `StrProperty`, `MapProperty<K,V>`, `ArrayProperty`, etc., each
self-describing enough to parse generically by walking the property list rather than
hardcoding offsets.

## `Secure*` fields are shadow copies, not real protection

A pattern like `CashSave: IntProperty` + `SecureCashSave: MapProperty<IntProperty,
ObjectProperty>` is an anti-tamper duplicate: the map has exactly one entry, and its
**key is a copy of the real value** (the map's value side is just a dummy object
reference, ignored). **Patch both together** — writing only the human-readable field
leaves the shadow copy stale and the game (or its anti-tamper check) notices the
mismatch. This is the same pattern as Iron Nest's odometer fields and worth checking
for by name (`Secure*`, `*Shadow*`, `*Verify*`) in any newly-seen GVAS save.

Both sides are typically fixed-width (`i32`), so patching in place doesn't change file
size — use that as a free sanity check.

## Don't trust `SavedBytes`-style fields as checksums without verifying

One save had an `ArrayProperty<ByteProperty>` field holding what looked like a short
content hash/checksum string. It wasn't: multiple save files with completely different
content carried the **identical** string, and the field wasn't even required — a save
saved without it loaded fine and the game just regenerated one on next write (file grew
by exactly the field's serialized size). Don't assume a checksum-shaped field is
load-bearing; check whether its value actually correlates with content, and whether
omitting it breaks loading, before spending time trying to recompute it correctly.

Array serialization detail if you do need to write one: `size:u64, inner_type:ue_str,
has_guid:u8, count:u32, data` — note the inner-type string comes **before** the guid
byte, not after.

## The game must be fully closed — see [ref:workflow]

UE4 games commonly read the save once at startup, keep the value in RAM, and flush
back to disk on exit or on a timer. An edit made while the game is running gets
silently discarded on the next flush. Don't trust a process-name check to confirm it's
closed (a differently-named or child process can still be holding the game open) —
compare the file's `LastWriteTime` before and after, or ask the user directly.

## Steam Cloud duplicate saves

If the game syncs via Steam Cloud, there's a second copy at
`<Steam>\userdata\<your_steam_id>\<appid>\remote\` in the same format. Patch both
locations, or Steam Cloud can push the stale local (or stale cloud) copy back down.
Cloud-side files are sometimes **hash-named** rather than keeping the original
filename (e.g. a save that's locally `Level.sav` appears as `db9e2940….sav` in
`remote\`) — match by parsing out the embedded savegame-class/property name, not by
filename, or you'll miss a duplicate.

## Transferring a save between Steam accounts

The owning SteamID64 (17 digits, fixed-width) typically appears **twice**: as the save
filename's numeric prefix, and again inside a `SecureSteamID:
MapProperty<StrProperty,ObjectProperty>` key. Both need to be swapped to the target
account's ID for the game to accept a shared save — same-length in-place string
replace, no length-prefix fixups needed since the ID string length doesn't change.
Files with no embedded ID (pure settings/tutorial-state files) aren't account-bound and
don't need touching.
