# Unity: IL2CPP saves and live patching

Two worked cases with opposite outcomes: **Iron Nest** (custom save format, cracked
easily) and **a Unity IL2CPP management sim** (real AES encryption, save left alone in favor of
patching the running game).

## Custom "obfuscated" save formats: check for XOR before assuming encryption

Iron Nest's saves (`%USERPROFILE%\AppData\LocalLow\<Studio>\<Game>\Live\*.dat`) looked
opaque but weren't: header bytes `5D C9 4A` XORed with `0x42` give `1F 8B 08` — the
gzip magic — followed by six literal `0x42` bytes where gzip's zeroed FLG/MTIME/XFL
fields should be. **XOR every byte with the constant, then gzip-decompress**; no
checksum/HMAC anywhere. Re-encoding is the same in reverse: gzip, then XOR.

General technique: when a "save" file doesn't match any known magic number but the
first several bytes look almost-right, try XORing with small single-byte constants
against the magic number you expect (gzip `1F 8B`, zlib `78`, JSON `{`, etc.) before
concluding it's real encryption.

### Anti-tamper fields that live in memory only

Iron Nest's IL2CPP metadata has fields like `requisitionPointsTampered`,
`CheckTampered`, and odometer shadow copies (`requisitionPointsOdometer_mission`)
meant to catch live memory editors (Cheat Engine style). None of these are actually
*persisted* in the save — the save holds only the plain gameplay keys, and the
odometers get rebuilt from the save on load. Editing the save file directly bypasses
this category of anti-tamper entirely; it's editing *live memory* that would trip it.

### Finding field names in IL2CPP metadata without a full deserializer

`global-metadata.dat` has a versioned binary header (`global-metadata.dat`'s parser
assumes a specific metadata version, e.g. v29); a newer metadata version (e.g. v39)
will make a version-specific parser misread the structure. When that happens, skip the
structured parser and do a **raw ASCII sweep** of the file for printable strings — it's
enough to find field/class names for grepping purposes.

## When the save is genuinely encrypted with an unrecoverable key: patch the running game instead

a Unity IL2CPP management sim's save is AES-CBC via a Unity `EncryptionUtility` asset with a
password baked into a serialized field inside an asset bundle — not worth extracting.
Instead: install a mod loader and patch memory live through it.

### The stack

- **BepInEx** (IL2CPP variant — for a Mono game use the Mono/net6 BepInEx build
  instead) dropped into the game folder (adds `winhttp.dll`, `doorstop_config.ini`,
  `BepInEx/`).
  - **Version trap:** some UnityExplorer builds reference the assembly name
    `BepInEx.IL2CPP`, but current BepInEx IL2CPP builds ship as `BepInEx.Unity.IL2CPP`.
    Mismatched builds fail silently — chainloader logs "0 plugins to load" with no
    error, no crash. Match the UnityExplorer build's expected BepInEx variant exactly.
- **UnityExplorer** (BepInEx.Unity.IL2CPP.CoreCLR build for an IL2CPP game) for a
  live object inspector + C# console.
- Uninstall = delete those files. No VAC risk for single-player games with no
  anti-cheat. **Never let Steam "verify integrity of game files"** after installing —
  it strips the mod loader back out.

### Workflow

1. Launch the (modded) game, get past the main menu / load the save you want to edit.
2. Press the UnityExplorer hotkey (commonly **F7**), open the **C# Console** tab.
3. Find the live object and call its real update method — don't just assign the
   backing field, since a direct field write skips change-notification events the UI
   depends on (HUD tweens, etc. can desync):
   ```csharp
   var w = UnityEngine.Object.FindObjectOfType<Namespace.CharacterWallet>();
   w.MakeMoney(100000f);          // not w.OwnMoney = 100000f
   Log("now = " + w.OwnMoney);
   ```
4. Close the overlay, confirm the HUD updated, then **save in-game** (the live edit is
   memory-only until the game's own save routine persists it).

### Why memory scanning (Cheat Engine etc.) can fail here

If the value is a **float**, not an int, scanning for an int16/32/64 match finds
nothing — the displayed integer is a rounded float (`571.4` internally, shown as
`571`). Confirm the underlying type via the IL2CPP metadata getter name
(`get_Single_0` = float) before scanning. Also: if you try to resolve a matched
address's class name via `Il2CppClass->name`, note the pointer at `klass+0x10` in some
layouts is **byte-aligned, not 8-byte-aligned** — an alignment assumption there can
silently return garbage/no match.

## Unity save-plugin format

If the game uses the **Easy Save 2** asset-store plugin for its saves instead of a
custom format, see [ref:unity-es2-saves] instead — different, simpler, binary record
format.
