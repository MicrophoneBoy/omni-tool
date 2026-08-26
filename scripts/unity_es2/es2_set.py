"""Set an Easy Save 2 int field in a Unity save by tag name.

usage: python es2_set.py <tag> <value> [path]

Never overwrites an existing backup -- auto-increments (save.bak, save.bak2, ...)
so every prior state survives. Re-reads the file after writing and asserts the
size didn't change, since these records are fixed-width. See
references/unity-es2-saves.md.

Written against Orbt XL but generic to any ES2 binary save -- override the
target with the ES2_SAVE env var, a trailing path argument, or edit PATH below.
"""
import os, struct, shutil, sys

PATH = os.environ.get(
    'ES2_SAVE',
    os.path.expanduser(r'~\AppData\LocalLow\Adamvision Studios\Orbt XL\dat01.orbtxl'))


def find_value_offset(d, tag):
    o = 0
    while o < len(d):
        assert d[o] == 0x7E, 'bad record marker at %d' % o
        n = d[o + 1]
        name = d[o + 2:o + 2 + n].decode()
        vo = o + 2 + n + 4 + 1 + 4          # skip mid, FF, type tag
        assert d[vo + 4] == 0x7B, 'bad record terminator at %d' % (vo + 4)
        if name == tag:
            return vo
        o = vo + 5
    return None


if __name__ == '__main__':
    tag, new = sys.argv[1], int(sys.argv[2])
    path = sys.argv[3] if len(sys.argv) > 3 else PATH

    d = bytearray(open(path, 'rb').read())
    hit = find_value_offset(d, tag)
    assert hit is not None, '%s not found' % tag

    before = bytes(d)
    old = struct.unpack_from('<i', d, hit)[0]
    print('%s at offset %d: %d -> %d' % (tag, hit, old, new))

    i, bak = 1, path + '.bak'
    while os.path.exists(bak):
        i += 1
        bak = '%s.bak%d' % (path, i)
    shutil.copy2(path, bak)
    print('backup written:', os.path.basename(bak))

    struct.pack_into('<i', d, hit, new)
    open(path, 'wb').write(d)

    e = open(path, 'rb').read()
    assert len(e) == len(before), 'size changed!'
    print('bytes changed:', [j for j in range(len(e)) if e[j] != before[j]])
    print('verified %s = %d' % (tag, struct.unpack_from('<i', e, hit)[0]))
