"""Set one switch or variable in an RPG Maker MZ (.rmmzsave) or MV (.rpgsave)
save by index.

Never overwrites an existing backup -- auto-increments (save.bak, save.bak2,
...). Re-reads the file after writing and reports the new value, same
discipline as every other mutating script in this toolkit. See
references/rpgmaker-galleries.md and rm_save_inspect.py for both formats.

Find the index first with `python rm_save_inspect.py --names <System.json>
<keyword>` (searches the game's own switch/variable name list, no save
needed) -- prefer a game's own single "unlock everything" switch/variable
over individually flipping every gallery entry, if one exists (see the
RPG Maker MZ case in references/rpgmaker-galleries.md).

Also works on a cross-save `common.rpgsave` (UTA_CommonSave-style
gameSwitches/gameVariables dicts), see rm_save_inspect.py.

usage: python rm_save_set.py <save> switches <idx> <true|false>
       python rm_save_set.py <save> variables <idx> <int>
"""
import os, shutil, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rm_save_inspect import load_save, save_save

if __name__ == '__main__':
    if len(sys.argv) != 5 or sys.argv[1] in ('-h', '--help'):
        raise SystemExit(__doc__)
    path, kind, idx, val = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    if kind == 'switches':
        val = val.lower() in ('true', '1', 'yes')
    elif kind == 'variables':
        val = int(val)
    else:
        raise SystemExit('kind must be "switches" or "variables"')

    save = load_save(path)
    common_key = 'game' + kind[0].upper() + kind[1:]          # gameSwitches
    if kind in save:
        data = save[kind]['_data']
        old = data[idx] if idx < len(data) else None
    elif common_key in save:
        data = save[common_key]
        old = data.get(str(idx))
    else:
        raise SystemExit('%s has no %s -- pick a fileN save, not config/global' % (path, kind))
    print('%s[%d]: %r -> %r' % (kind, idx, old, val))

    i, bak = 1, path + '.bak'
    while os.path.exists(bak):
        i += 1
        bak = '%s.bak%d' % (path, i)
    shutil.copy2(path, bak)
    print('backup written:', os.path.basename(bak))

    if isinstance(data, dict):
        data[str(idx)] = val
    else:
        while len(data) <= idx:
            data.append(None)
        data[idx] = val
    save_save(path, save)

    reloaded = load_save(path)
    new = (reloaded[kind]['_data'][idx] if kind in reloaded
           else reloaded[common_key].get(str(idx)))
    print('verified %s[%d] = %r' % (kind, idx, new))
