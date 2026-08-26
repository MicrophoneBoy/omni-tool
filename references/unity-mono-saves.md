# Unity: Mono builds (as distinct from IL2CPP)

[ref:unity-il2cpp-saves] covers IL2CPP Unity games exclusively (BepInEx.Unity.IL2CPP,
IL2CPP metadata string sweeps). A **Mono** Unity build needs a different toolchain —
check which one you're dealing with before reaching for BepInEx/UnityExplorer.

## Telling them apart

- **IL2CPP**: `GameAssembly.dll` present in the game folder; C# is AOT-compiled to
  native code, no managed assemblies to decompile directly.
- **Mono**: a `<Game>_Data\Managed\` folder full of ordinary .NET assemblies
  (`Assembly-CSharp.dll` and friends), no `GameAssembly.dll`. These are normal IL
  assemblies — decompilable directly, no native-code metadata-walking required.

## Mono-specific toolchain

Because Mono ships real .NET assemblies, you have an option IL2CPP doesn't offer at
all: **edit the code itself**, no mod loader required.

- **ILSpy / dnSpyEx** — decompile `Assembly-CSharp.dll` (and any other managed
  assembly) straight to readable C#, and in dnSpyEx's case, edit and re-save the
  assembly in place. For a Mono game, this can replace the entire
  "install a mod loader, write a script that runs at launch" workflow we use for
  IL2CPP — you can just patch the compiled method directly.
- **Cheat Engine's Mono dissector** — Cheat Engine has a mode specifically for
  resolving managed objects/fields in a running Mono process (analogous to what
  UnityExplorer's reflection-based object browser gives you for IL2CPP). Use this for
  live inspection/scanning instead of UnityExplorer, which is IL2CPP/BepInEx-oriented.
- **AssetRipper / UABE** — unpack `.assets`/`.resS` files when what you need is
  *content* (images, audio, prefab data) rather than code or save data. Not something
  our other docs touch, since our cases so far have all been about state (money, HP,
  unlock flags), not assets.

## Still check the save file first

Everything in [ref:workflow]'s ordering still applies — a Mono game is just as likely
to have a plain or trivially-decoded save file as an IL2CPP one. The Mono/IL2CPP
distinction only matters once you've confirmed you actually need to touch code or
live memory.
