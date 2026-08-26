"""Inspect a SQLite save file: list tables, schema, and (optionally) row contents.

Use the standard library, not a hand-rolled parser -- see
references/sqlite-saves.md for why SQLite is the one format in this toolkit
where that's the right call.

usage:
  python sqlite_inspect.py <db_path>                 # list tables + schema
  python sqlite_inspect.py <db_path> <table>          # dump every row of one table
"""
import sqlite3, sys


def list_tables(conn):
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


def schema_of(conn, table):
    return conn.execute("PRAGMA table_info(%s)" % table).fetchall()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        raise SystemExit('usage: python sqlite_inspect.py <db_path> [table]')
    path = sys.argv[1]

    # Read-only connection (uri mode) so this never accidentally creates or
    # locks a WAL file just from inspecting.
    conn = sqlite3.connect('file:%s?mode=ro' % path, uri=True)

    if len(sys.argv) >= 3:
        table = sys.argv[2]
        cols = [c[1] for c in schema_of(conn, table)]
        print('columns:', cols)
        for row in conn.execute('SELECT * FROM %s' % table):
            print(dict(zip(cols, row)))
    else:
        tables = list_tables(conn)
        print('%d table(s)' % len(tables))
        for t in tables:
            cols = schema_of(conn, t)
            colnames = ', '.join('%s %s' % (c[1], c[2]) for c in cols)
            n = conn.execute('SELECT COUNT(*) FROM %s' % t).fetchone()[0]
            print('  %-24s (%d rows)  %s' % (t, n, colnames))
