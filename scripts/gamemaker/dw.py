"""GameMaker data.win reader (bytecode 15+).

Enough of the format to find and patch GML bytecode:
  STRG -> string table (offset -> text; note pointers point at the CHARS,
          which sit 4 bytes past the length field)
  CODE -> per-script/event bytecode, with the actual instructions living in a
          shared blob that each entry points into via a *relative* offset
  VARI/FUNC -> name tables the bytecode references

Written against Downwell but generic to any bytecode-15+ data.win. Override the
default target with the DW_DATA_WIN env var or an explicit path argument.
"""
import os, struct, sys

PATH = os.environ.get('DW_DATA_WIN', r'C:\Program Files (x86)\Steam\steamapps\common\Downwell\data.win')


def chunks(d):
    assert d[:4] == b'FORM'
    (total,) = struct.unpack_from('<I', d, 4)
    p, end = 8, 8 + total
    out = {}
    while p < end:
        name = d[p:p + 4].decode('ascii')
        (size,) = struct.unpack_from('<I', d, p + 4)
        out[name] = (p + 8, size)
        p += 8 + size
    return out


def cstr_at(d, off):
    """String whose CHARS start at off; length u32 sits just before."""
    (n,) = struct.unpack_from('<I', d, off - 4)
    return d[off:off + n].decode('utf-8', 'replace')


def pointer_list(d, off):
    (n,) = struct.unpack_from('<I', d, off)
    return list(struct.unpack_from('<%dI' % n, d, off + 4))


def strings(d, ch):
    """{char_offset: text} for every entry in STRG."""
    off, _ = ch['STRG']
    out = {}
    for p in pointer_list(d, off):
        (n,) = struct.unpack_from('<I', d, p)
        out[p + 4] = d[p + 4:p + 4 + n].decode('utf-8', 'replace')
    return out


def code_entries(d, ch, strs):
    """[(name, bytecode_abs_offset, length, entry_header_offset)]"""
    off, _ = ch['CODE']
    out = []
    for p in pointer_list(d, off):
        name_ptr, length = struct.unpack_from('<II', d, p)
        # bytecode 15+: locals u16, args u16, rel_offset i32, then offset u32
        rel = struct.unpack_from('<i', d, p + 12)[0]
        bc = p + 12 + rel                    # relative to its own field
        out.append((strs.get(name_ptr, '?'), bc, length, p))
    return out


def load(path=None):
    d = bytearray(open(path or PATH, 'rb').read())
    ch = chunks(d)
    strs = strings(d, ch)
    return d, ch, strs, code_entries(d, ch, strs)


if __name__ == '__main__':
    d, ch, strs, code = load()
    print('%d code entries, %d strings' % (len(code), len(strs)))
    pat = (sys.argv[1] if len(sys.argv) > 1 else 'hp').lower()
    for name, bc, ln, _ in code:
        if pat in name.lower():
            print('  %-60s @0x%08X %6d bytes' % (name, bc, ln))
