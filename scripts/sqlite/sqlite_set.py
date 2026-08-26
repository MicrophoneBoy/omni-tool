"""Set a column value in a SQLite save, by a WHERE match on another column.

Checkpoints any pending WAL file into the main .db before AND after editing (see
references/sqlite-saves.md -- a game that wasn't cleanly closed can leave the
real current state sitting in a `-wal` file, invisible if you only look at the
main .db's mtime/content). Backs up the .db (+ -wal/-shm if present) before
writing, never overwriting a prior backup.

usage: python sqlite_set.py <db_path> <table> <set_column> <new_value> <where_column> <where_value>
example: python sqlite_set.py save.db player_stats gold 999999 id 1
"""
import os, shutil, sqlite3, sys


def coerce(s):
    for f in (int, float):
        try:
            return f(s)
        except ValueError:
            pass
    return s


def backup(path):
    for ext in ('', '-wal', '-shm'):
        src = path + ext
        if not os.path.exists(src):
            continue
        i, dst = 1, src + '.bak'
        while os.path.exists(dst):
            i += 1
            dst = '%s.bak%d' % (src, i)
        shutil.copy2(src, dst)
        print('backup written:', os.path.basename(dst))


if __name__ == '__main__':
    if len(sys.argv) != 7:
        raise SystemExit(
            'usage: python sqlite_set.py <db_path> <table> <set_column> <new_value> '
            '<where_column> <where_value>')
    path, table, set_col, new_val, where_col, where_val = sys.argv[1:7]
    new_val, where_val = coerce(new_val), coerce(where_val)

    backup(path)

    conn = sqlite3.connect(path)
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')  # fold any pending WAL data in first

    before = conn.execute(
        'SELECT %s FROM %s WHERE %s = ?' % (set_col, table, where_col),
        (where_val,)).fetchall()
    print('%d matching row(s), current %s: %s' % (len(before), set_col, before))

    cur = conn.execute(
        'UPDATE %s SET %s = ? WHERE %s = ?' % (table, set_col, where_col),
        (new_val, where_val))
    conn.commit()
    conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')  # flush the write back out of the WAL too
    print('rows updated:', cur.rowcount)

    after = conn.execute(
        'SELECT %s FROM %s WHERE %s = ?' % (set_col, table, where_col),
        (where_val,)).fetchall()
    print('verified, new %s: %s' % (set_col, after))
    conn.close()
