# Ren'Py: scene/replay gallery unlocks

Worked case: **a Ren'Py visual novel**. Contrast case (no lock existed): **a second Ren'Py visual novel**.

## How Ren'Py galleries are usually gated

Ren'Py tracks, per install, whether the player has ever executed a given label in any
playthrough:

```python
renpy.seen_label(label)   # -> label in renpy.game.persistent._seen_ever
```

`_seen_ever` is a plain `{label_name: True}` dict living in the persistent data file
(survives across saves, tied to the install, not a specific save slot). A gallery
screen typically gates each thumbnail with `if renpy.seen_label(some_label):` where
`some_label` is the label that plays the actual story scene.

**Find the gate before writing anything.** Extract (or just open, if the game ships
loose `.rpy` source) the gallery screen file and grep for `seen_label`, `_seen_ever`,
or a persistent flag check. Two real outcomes seen so far:

- **a Ren'Py visual novel**: `gallery/gallery.rpy` line ~271, `if renpy.seen_label(temp_gallery_array[z][1]):`
  gates every thumbnail. The label list is the *second element* of each
  `[gal_replay_label, real_story_label, caption, ...]` entry in each area's
  `*_replays` list — that's your full set of labels to mark seen.
- **a second Ren'Py visual novel**: grepped the entire `game/` tree for `seen_label` and
  `_seen_ever` — zero hits. Every chapter/scene button was an unconditional
  `Jump(...)`, thumbnails were real (non-placeholder) art already on disk. Conclusion:
  **no lock exists**; nothing to patch. Don't assume a gallery is gated just because
  the user expects it to be — verify first (see [ref:workflow]).

## The fix: use Ren'Py's own unlock API, don't hand-edit the persistent file

The persistent file is protected by a per-install ECDSA (NIST256p) signature — see
`renpy/savetoken.py`: `sign_data`/`verify_data`, keys generated on first run into a
`tokens/security_keys.txt` next to saves. Hand-editing the persistent file's pickle
would require re-deriving and re-signing correctly, which is fragile and unnecessary.

Ren'Py ships exactly the API you need (`renpy/exports.py`), and its docstring
literally says what it's for:

```python
renpy.mark_label_seen(label)   # sets persistent._seen_ever[str(label)] = True
                                # "This can be used to unlock scene galleries."
renpy.save_persistent()        # renpy.persistent.update(True); writes + signs to disk
```

Calling these from **inside the running game** means the game's own code performs the
write, so it signs correctly automatically — no crypto to reverse.

### Delivery mechanism: a loose `.rpy` mod file

If the game distribution includes the Ren'Py SDK folder loose (not a single obfuscated
executable), any new `.rpy` file dropped into `game/` is auto-compiled and loaded at
next launch. No archive repacking, no exe patching. Confirmed via `log.txt` line
ordering that persistent data is loaded (`"Loading persistent."`) *before*
`init python:` blocks run (`"Running init code."`), so reading/writing `persistent.*`
inside `init python:` is always safe.

```python
# game/998_unlock_gallery.rpy
init python:
    _all_gallery_labels = [
        "label_one", "label_two", # ... every real_story_label from the gate condition
    ]

    if not persistent._gallery_all_unlocked:   # one-time flag, avoid re-running every launch
        for _lbl in _all_gallery_labels:
            renpy.mark_label_seen(_lbl)
        persistent._gallery_all_unlocked = True
        renpy.save_persistent()
```

Extract the label list programmatically from the gallery script rather than
transcribing by hand — regex over `["gal_label", "real_label", "caption", ...]`
entries, **but strip commented-out lines first** (`gallery.rpy` had a commented-out
documentation example line that would otherwise inject a bogus placeholder label like
`"exactNameAsSceneDontChange"` into the set).

## Verifying it worked

Launch the game once with the mod file in place, then close it and check
`game/saves/persistent`: it should have grown (new `_seen_ever` entries + your one-time
flag), and should still end in a valid-looking signature block (`renpy.savetoken`
appends `encode_line("signature", verifying_key_der, sig)` lines, base64-wrapped, after
a zlib-compressed pickle body) — that block being present and non-empty confirms the
game itself re-signed the file, which is the whole point of using the API instead of
hand-editing.

## RPA archives

If the game ships a packed `.rpa` instead of loose `.rpy` source, see
[ref:rpa-archives] to extract just the gallery script(s) you need to read.
