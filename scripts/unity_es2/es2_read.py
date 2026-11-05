"""Dump every record in a Unity Easy Save 2 (ES2) binary save file.

Record layout: 7E <name_len:u8> <name:ascii> <mid:4 bytes> FF <type_tag:4 bytes>
<value:4 bytes> 7B, repeated back-to-back. See references/unity-es2-saves.md.

Written against Orbt XL but generic to any ES2 binary save.

usage: python es2_read.py <save_file>     (or set ES2_SAVE and omit it)
"""
import os, struct, sys

PATH = os.environ.get('ES2_SAVE')


def records(d):
    o = 0
    while o < len(d):
        assert d[o] == 0x7E, ('bad record marker', o, d[o])
        n = d[o + 1]
        name = d[o + 2:o + 2 + n].decode()
        p = o + 2 + n
        mid = d[p:p + 4]; p += 4
        assert d[p] == 0xFF; p += 1
        tag = d[p:p + 4]; p += 4
        val = d[p:p + 4]; p += 4
        assert d[p] == 0x7B, ('bad record terminator', p, d[p])
        yield (o, name, mid.hex(), tag.hex(), val.hex(),
               struct.unpack('<i', val)[0], struct.unpack('<f', val)[0])
        o = p + 1


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        raise SystemExit(__doc__)
    path = sys.argv[1] if len(sys.argv) > 1 else PATH
    if not path:
        raise SystemExit(__doc__)
    d = open(path, 'rb').read()
    print('size', len(d))
    recs = list(records(d))
    print('records', len(recs))
    print('%-6s %-6s %-8s %-8s %-10s %12s %14s' % ('off', 'name', 'mid', 'tag', 'raw', 'int', 'float'))
    for r in recs:
        print('%-6d %-6s %-8s %-8s %-10s %12d %14.6g' % r)
