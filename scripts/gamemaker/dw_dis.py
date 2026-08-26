"""Disassemble GameMaker bytecode-17 GML.

Names resolve the way the runtime does: VARI/FUNC store the file offset of a
name's FIRST reference, and the word *after* each referencing instruction holds
the delta to the next one. Walking those chains gives offset -> name directly,
which beats trying to decode the reference's packed index field.
"""
import struct, sys
from dw import load
from dw_names import vari_names, func_names

TYPES = {0: 'd', 1: 'f', 2: 'i', 3: 'l', 4: 'b', 5: 'v', 6: 's', 15: 'e'}
INST = {-1: 'self', -2: 'other', -3: 'all', -4: 'noone', -5: 'global',
        -6: 'builtin', -7: 'local', -9: 'stacktop', -15: 'arg', -16: 'static'}

# bytecode 15+ opcode table
OPS = {0x07: 'conv', 0x08: 'mul', 0x09: 'div', 0x0A: 'rem', 0x0B: 'mod',
       0x0C: 'add', 0x0D: 'sub', 0x0E: 'and', 0x0F: 'or', 0x10: 'xor',
       0x11: 'neg', 0x12: 'not', 0x13: 'shl', 0x14: 'shr', 0x15: 'cmp',
       0x45: 'pop', 0x86: 'dup', 0x9C: 'ret', 0x9D: 'exit', 0x9E: 'popz',
       0xB6: 'b', 0xB7: 'bt', 0xB8: 'bf', 0xBA: 'pushenv', 0xBB: 'popenv',
       0xC0: 'push', 0xC1: 'pushloc', 0xC2: 'pushglb', 0xC3: 'pushbltn',
       0x84: 'pushi', 0xD9: 'call', 0xDA: 'callv', 0xFF: 'break'}
BINARY = {0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x10,
          0x13, 0x14}
PUSHES = {0xC0, 0xC1, 0xC2, 0xC3, 0x84}
CMP = {1: '<', 2: '<=', 3: '==', 4: '!=', 5: '>=', 6: '>'}


def chain(d, first, count):
    """Instruction offsets of every reference in an occurrence chain."""
    out, p = [], first
    for _ in range(count):
        if p <= 0 or p + 8 > len(d):
            break
        out.append(p)
        (raw,) = struct.unpack_from('<I', d, p + 4)
        delta = raw & 0x00FFFFFF
        if delta == 0:
            break
        p += delta
    return out


def name_maps(d, ch, strs):
    """(instr_offset -> varname, instr_offset -> funcname)."""
    vmap, fmap = {}, {}
    for nm, _, _, occ, first in vari_names(d, ch, strs):
        for p in chain(d, first, occ):
            vmap[p] = nm
    for nm, occ, first in func_names(d, ch, strs):
        for p in chain(d, first, occ):
            fmap[p] = nm
    return vmap, fmap


def decode(d, p, vmap, fmap, strlist):
    """(mnemonic, argtext, size_in_bytes) for the instruction at p."""
    (word,) = struct.unpack_from('<I', d, p)
    op = (word >> 24) & 0xFF
    t1, t2 = (word >> 16) & 0xF, (word >> 20) & 0xF
    short = struct.unpack_from('<h', d, p)[0]
    mn, arg, size = OPS.get(op, 'op%02X' % op), '', 4

    if op in PUSHES:
        mn += '.' + TYPES.get(t1, '?')
        if t1 == 5:                                    # variable reference
            arg = '%s.%s' % (INST.get(short, 'inst%d' % short), vmap.get(p, '?'))
            size = 8
        elif t1 == 6:
            (idx,) = struct.unpack_from('<I', d, p + 4)
            arg = '"%s"' % strlist[idx] if idx < len(strlist) else '<str%d>' % idx
            size = 8
        elif t1 == 0:
            arg, size = repr(struct.unpack_from('<d', d, p + 4)[0]), 12
        elif t1 == 3:
            arg, size = str(struct.unpack_from('<q', d, p + 4)[0]), 12
        elif t1 in (1, 2):
            fmt = '<f' if t1 == 1 else '<i'
            arg, size = str(struct.unpack_from(fmt, d, p + 4)[0]), 8
        elif t1 == 15:
            arg = str(short)
    elif op == 0x45:
        mn = 'pop.%s.%s' % (TYPES.get(t2, '?'), TYPES.get(t1, '?'))
        arg, size = '%s.%s' % (INST.get(short, 'inst%d' % short), vmap.get(p, '?')), 8
    elif op == 0xD9:
        mn = 'call.%s' % TYPES.get(t1, '?')
        arg, size = '%s, argc=%d' % (fmap.get(p, '?'), word & 0xFFFF), 8
    elif op in (0xB6, 0xB7, 0xB8, 0xBA, 0xBB):
        rel = word & 0xFFFFFF
        if rel & 0x800000:
            rel -= 0x1000000
        arg = '-> 0x%08X' % (p + rel * 4)
    elif op == 0x15:
        mn = 'cmp.%s.%s %s' % (TYPES.get(t1, '?'), TYPES.get(t2, '?'),
                               CMP.get((word >> 8) & 0xFF, '?'))
    elif op in BINARY:
        mn += '.%s.%s' % (TYPES.get(t1, '?'), TYPES.get(t2, '?'))
    return mn, arg, size


def dis(d, start, length, vmap, fmap, strlist):
    p, end, out = start, start + length, []
    while p < end:
        mn, arg, size = decode(d, p, vmap, fmap, strlist)
        out.append('  0x%08X  %-20s %s' % (p, mn, arg))
        p += size
    return out


def context(path=None):
    d, ch, strs, code = load(path) if path else load()
    strlist = [strs[k] for k in sorted(strs)]
    vmap, fmap = name_maps(d, ch, strs)
    return d, ch, strs, code, strlist, vmap, fmap


if __name__ == '__main__':
    d, ch, strs, code, strlist, vmap, fmap = context()
    want = sys.argv[1]
    for name, bc, ln, _ in code:
        if name == want or name.endswith('_' + want) or want in name:
            print('=== %s @0x%08X (%d bytes) ===' % (name, bc, ln))
            print('\n'.join(dis(d, bc, ln, vmap, fmap, strlist)))
            break
    else:
        print('no code entry matching %r' % want)
