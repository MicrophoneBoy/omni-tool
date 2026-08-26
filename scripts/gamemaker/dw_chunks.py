"""Dump the top-level chunk layout of a GameMaker data.win (IFF 'FORM')."""
import os, struct, sys

PATH = os.environ.get('DW_DATA_WIN', r'X:\Steam\steamapps\common\Downwell\data.win')


def chunks(d):
    assert d[:4] == b'FORM', 'not a GameMaker data file'
    (total,) = struct.unpack_from('<I', d, 4)
    p, end = 8, 8 + total
    while p < end:
        name = d[p:p + 4].decode('ascii')
        (size,) = struct.unpack_from('<I', d, p + 4)
        yield name, p + 8, size
        p += 8 + size


if __name__ == '__main__':
    d = open(sys.argv[1] if len(sys.argv) > 1 else PATH, 'rb').read()
    print('%d bytes' % len(d))
    for name, off, size in chunks(d):
        print('  %-4s @0x%08X  %10d bytes' % (name, off, size))
