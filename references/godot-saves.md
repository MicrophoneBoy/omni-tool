# Godot 4.x: encrypted saves, embedded PCK, compiled script tokens

Worked case: **a Godot dating sim** (Godot 4.6.2, single exe with embedded PCK).

## `GDEC` encrypted save format

Godot's `FileAccess.open_encrypted_with_pass()` produces:

```
'GDEC' | md5(plaintext)[16 bytes] | length:u64 LE | iv[16 bytes] | ciphertext
key = ASCII bytes of md5_hex(password)      # String.md5_text(), 32 bytes
ciphertext = AES-256-CFB128(plaintext, zero-padded to a 16-byte boundary)
```

**It is CFB128, not CBC**, for Godot 4.6 — most documentation and cached knowledge of
`FileAccessEncrypted` says CBC, which is wrong for this version and will burn time
decrypting garbage that *almost* looks right. Diagnostic if you're unsure which mode
you're looking at: try CTR — if only the *first* block decrypts correctly, the key and
IV offset are right and it's a stream-cipher mode, which points at CFB (or OFB/CTR
variants) rather than a block-chaining mode like CBC. Verify your candidate mode by
checking the decrypted plaintext's MD5 against the stored header hash.

Finding the password: it's typically a plain string constant in the game's own GDScript
(e.g. `SAVE_ENCRYPTION_PASSWORD = "..."`) — see the `GDSC` section below for finding it
without a decompiler.

## Embedded PCK (single-exe distributions)

When the game ships as one exe with assets embedded rather than a separate `.pck`
file, the archive is appended to the executable:

```
last 4 bytes of file:  magic 'GDPC'
preceding 8 bytes:     u64 pck size
pck_start = filesize - pck_size - 12
```

**Pack format v3** (Godot 4.5+) moved the file directory to the **end** of the pack
instead of right after the header — a parser written against the older layout
(directory immediately following the header) will report `files: 0` and appear to work
but find nothing. v3 header: magic, version, three format-version fields, `flags:u32`,
`file_base:u64`, **`dir_off:u64`**, then reserved padding out to offset `0x70`. Flag
bit `0x2` means offsets in the directory are relative to the pack's start rather than
absolute in the containing exe.

## `GDSC` compiled script token buffers (finding strings without a decompiler)

Godot 4.3+ compiles GDScript to `.gdc` files with this shape:

```
magic 'GDSC' | version:u32 | decompressed_size:u32 | zstd-compressed body
```

The decompressed body: 4 count fields, then an **identifier table** (UTF-32 code
units, each byte XORed with `0xB6`), then a **constants table** using Godot's standard
Variant binary encoding. Parsing just far enough to dump the identifier and constant
tables gives you every string literal and symbol name in the script — including
hardcoded passwords/keys — without needing a full GDScript decompiler.

Same lesson as everywhere else in this toolkit: locate and read the save/script content
before touching live memory or the binary — see [ref:workflow].
