"""List VARI / FUNC names matching a pattern."""
import re, struct, sys
from dw import load


def vari_names(d, ch, strs):
    off, size = ch['VARI']
    # GMS2.3 VARI header: 3 x u32 (var counts) then the entries
    p = off + 12
    out = []
    end = off + size
    while p + 20 <= end:
        name_ptr, vtype, vindex, occ, first = struct.unpack_from('<IiiiI', d, p)
        if name_ptr not in strs:
            break
        out.append((strs[name_ptr], vtype, vindex, occ, first))
        p += 20
    return out


def func_names(d, ch, strs):
    off, size = ch['FUNC']
    (n,) = struct.unpack_from('<I', d, off)
    out = []
    p = off + 4
    for _ in range(n):
        name_ptr, occ, first = struct.unpack_from('<IiI', d, p)
        if name_ptr not in strs:
            break
        out.append((strs[name_ptr], occ, first))
        p += 12
    return out


if __name__ == '__main__':
    d, ch, strs, code = load()
    pat = re.compile(sys.argv[1] if len(sys.argv) > 1 else 'hp', re.I)
    print('=== VARI ===')
    for nm, vtype, vidx, occ, first in vari_names(d, ch, strs):
        if pat.search(nm):
            print('  %-34s type=%-3d idx=%-5d occurrences=%-5d first=0x%08X'
                  % (nm, vtype, vidx, occ, first))
    print('=== FUNC ===')
    for nm, occ, first in func_names(d, ch, strs):
        if pat.search(nm):
            print('  %-34s occurrences=%-5d first=0x%08X' % (nm, occ, first))
