# SQLite saves

Common for Android games (`/data/data/<package>/databases/`), many Unity games via a
plugin (there's no single standard one — several asset-store SQLite wrappers exist),
Godot via the community `GDSQLite` addon, and Electron-based games. Verified against a
synthetic test database (not a specific game yet) — see the "verifying" section below
for why that's a meaningfully strong test for this format specifically, unlike a
synthetic test would be for one of our other hand-rolled-parser formats.

## Detecting it

Check the file's **magic bytes**, not its extension — a save can be named `.sav`,
`.dat`, or anything else and still be a SQLite database underneath:

```
first 16 bytes == b'SQLite format 3\x00'
```

## Use the standard library, not a hand-rolled parser

Every other binary format in this toolkit (RPA, GVAS, `data.win`, ES2, GDEC) gets a
hand-rolled parser because the format is simple enough that writing one is less
overhead than pulling in a real implementation, and because in-place byte patching
keeps edits minimal and easy to verify. **SQLite is the opposite case**: the on-disk
format (B-tree pages, a freelist, overflow pages, varint-encoded cell headers) is
complex enough that hand-patching bytes is genuinely risky — a row's serialized size
can change when a value's byte-width changes, which can force a page split and move
data around. Meanwhile Python's `sqlite3` module is in the standard library, handles
every one of those complexities correctly, and needs zero extra dependencies. There is
no reason to hand-roll this one — always go through the real API
(`scripts/sqlite/sqlite_inspect.py`, `sqlite_set.py`), never raw byte patching.

## Reading

```
python scripts/sqlite/sqlite_inspect.py <db_path>            # list tables + schema
python scripts/sqlite/sqlite_inspect.py <db_path> <table>    # dump every row
```

Uses a read-only URI connection (`mode=ro`) so inspecting a file never creates or
disturbs a WAL file just from looking at it.

## Writing

```
python scripts/sqlite/sqlite_set.py <db_path> <table> <set_column> <new_value> <where_column> <where_value>
```

Same discipline as everywhere else in this toolkit: backs up before writing (never
overwrites an existing backup), prints the matched row count and old value before
writing, and re-reads to verify the new value after.

## The WAL gotcha (verified empirically while building this doc)

`PRAGMA journal_mode=WAL` is a **sticky, on-disk property of the database file
itself**, not a per-connection setting — once a database has been opened in WAL mode
even once, every future connection to it operates in WAL mode by default, even a
connection that never explicitly asked for it. In WAL mode, a write goes to a
separate `<dbname>-wal` file first; the main `.db` file isn't necessarily up to date
until a checkpoint happens. Practical consequences:

- **The real current state can be sitting in `-wal` (and `-shm`, its shared-memory
  index), not the main file.** If a game wasn't cleanly closed, don't assume the
  `.db` file alone reflects reality — back up and consider both.
- **Backing up only the `.db` file is not enough.** `sqlite_set.py` backs up `.db`,
  `.db-wal`, and `.db-shm` together, whichever of those exist. This was confirmed
  necessary in practice while testing this very doc: a `-wal`/`-shm` pair that did
  *not* exist moments earlier reappeared the instant a write connection touched the
  database, purely because the file's WAL-mode flag was already set from an earlier
  session.
- **`sqlite_set.py` checkpoints before *and* after writing** (`PRAGMA
  wal_checkpoint(TRUNCATE)`), so edits land in the main file and don't get left
  stranded in a WAL file that a later checkpoint could reorder against.
- Same rule as everywhere else in [ref:workflow]: make sure the game is actually
  closed before editing. A live WAL connection held open by a running game can still
  overwrite your edit on its own next checkpoint.

## If the header doesn't match

A file that's clearly database-shaped (fixed page size, consistent structure) but
whose first bytes *aren't* the plain `SQLite format 3\0` magic may be **SQLCipher**
(an encrypted SQLite variant) rather than something else entirely. Same approach as
any other engine-specific encryption in this toolkit (the dating sim in [ref:godot-saves], the management sim in [ref:unity-il2cpp-saves]): check whether the
game's own code has the key hardcoded before assuming it's unrecoverable.

## Verifying against a real game

This doc and both scripts are validated against a synthetic test database, not yet a
real game save — reasonable confidence here is higher than for our other
not-yet-verified docs (compare [ref:rpgmaker-galleries]) because SQLite is a
standardized format with a correct, well-tested implementation doing all the actual
parsing (Python's `sqlite3`), rather than something we're inferring from one game's
specific quirks. The only genuinely game-specific step left, the first time this comes
up for real, is finding *which* table/column holds the value you want — everything
else in this doc should just work.
