"""Every reference to a named variable, with the owning code entry and a
few instructions of context. Writes (pop) are what matter for patching."""
import re, sys
from dw_dis import context, decode
from dw_names import vari_names


def owner_index(code):
    """Sorted (bytecode_start, end, name) so an offset maps back to its script."""
    spans = sorted((bc, bc + ln, nm) for nm, bc, ln, _ in code
                   if nm.startswith('gml_Script_') or nm.startswith('gml_Object_')
                   or nm.startswith('gml_GlobalScript_'))
    return spans


def owner_of(spans, off):
    best = None
    for bc, end, nm in spans:
        if bc <= off < end:
            # prefer the tightest span (Script_ and GlobalScript_ alias each other)
            if best is None or (end - bc) < (best[1] - best[0]):
                best = (bc, end, nm)
    return best[2] if best else '?'


if __name__ == '__main__':
    d, ch, strs, code, strlist, vmap, fmap = context()
    pat = re.compile(sys.argv[1], re.I)
    spans = owner_index(code)
    for nm, _, _, occ, first in vari_names(d, ch, strs):
        if not pat.fullmatch(nm):
            continue
        print('### %s  (%d references)' % (nm, occ))
        for off in sorted(p for p, n in vmap.items() if n == nm):
            mnem, arg, _ = decode(d, off, vmap, fmap, strlist)
            kind = 'WRITE' if mnem.startswith('pop') else 'read '
            print('  %s 0x%08X  %-22s %-28s  in %s'
                  % (kind, off, mnem, arg, owner_of(spans, off)))
