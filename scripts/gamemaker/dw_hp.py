"""Worked example: set a global's starting value by patching data.win bytecode.

Written against Downwell's starting HP, which is assigned in two places:
  scrPlayerGlobalStat  -- the base run-start reset (playerHpMax and playerHp)
  styleUpdate          -- runs afterwards, one branch per playstyle, and
                          re-assigns playerHpMax then playerHp = playerHpMax.
styleUpdate wins, so patching only the first would do nothing in game -- see
references/gamemaker-datawin.md for why this pattern (a later writer overriding
an earlier one) is worth checking for on any new target.

Every site is `pushi.e <n>` (0x840F0000 | int16) directly before a
`pop.i.v global.<name>`, so each edit is a 2-byte in-place change and
data.win never changes size. Sites are located by that pattern rather than by
hardcoded offsets.

Adapt TARGETS / INIT_SCRIPTS for a different game or variable.
"""
import os, shutil, struct, sys
from dw_dis import context, decode
from dw_refs import owner_index, owner_of

GAME = os.environ.get('DW_DATA_WIN', r'C:\Program Files (x86)\Steam\steamapps\common\Downwell\data.win')
BACKUP = GAME + '.hpbackup'
TARGETS = ('playerHp', 'playerHpMax')
PUSHI_E = 0x840F0000

# Only the run-start initialisers. objPlayer_n_Step_1 also assigns a literal to
# playerHp, but that one is `playerHp = 0` on death -- raising it would break
# dying, not starting health.
INIT_SCRIPTS = ('gml_GlobalScript_scrPlayerGlobalStat', 'gml_GlobalScript_styleUpdate')


def sites(d, vmap, fmap, strlist, code, initonly=True):
    """[(pushi_offset, current_value, variable, owning_script)]"""
    spans = owner_index(code)
    out = []
    for off, nm in sorted(vmap.items()):
        if nm not in TARGETS:
            continue
        mn, _, _ = decode(d, off, vmap, fmap, strlist)
        if not mn.startswith('pop'):
            continue
        prev = off - 4                       # pushi.e is 4 bytes, no operand
        (word,) = struct.unpack_from('<I', d, prev)
        if word & 0xFFFF0000 != PUSHI_E:
            continue                         # computed, not a literal; skip
        owner = owner_of(spans, off)
        if initonly and owner not in INIT_SCRIPTS:
            continue
        out.append((prev, struct.unpack_from('<h', d, prev)[0], nm, owner))
    return out


def main():
    d, ch, strs, code, strlist, vmap, fmap = context(GAME)
    found = sites(d, vmap, fmap, strlist, code)
    print('literal HP assignments found: %d' % len(found))
    for off, val, nm, owner in found:
        print('  0x%08X  pushi.e %-3d -> global.%-12s  in %s' % (off, val, nm, owner))

    if len(sys.argv) < 3 or sys.argv[1] != 'set':
        return
    new = int(sys.argv[2])
    if not (1 <= new <= 32767):
        raise SystemExit('value must be 1..32767 (it is a 16-bit immediate)')

    if not os.path.exists(BACKUP):
        shutil.copy2(GAME, BACKUP)
        print('backup -> %s' % os.path.basename(BACKUP))

    before = len(d)
    for off, val, nm, owner in found:
        struct.pack_into('<H', d, off, new & 0xFFFF)
    open(GAME, 'wb').write(bytes(d))
    after = os.path.getsize(GAME)
    print('wrote %d site(s); size %d -> %d %s'
          % (len(found), before, after, 'OK' if before == after else 'MISMATCH'))

    print('--- verify (re-read from disk) ---')
    d2, _, _, code2, strlist2, vmap2, fmap2 = context(GAME)
    for off, val, nm, owner in sites(d2, vmap2, fmap2, strlist2, code2):
        print('  0x%08X  pushi.e %-3d -> global.%-12s  in %s' % (off, val, nm, owner))


if __name__ == '__main__':
    main()
