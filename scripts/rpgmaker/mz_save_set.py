"""Set one switch or variable in an RPG Maker MZ save (.rmmzsave) by index.

Never overwrites an existing backup -- auto-increments (save.bak, save.bak2,
...). Re-reads the file after writing and reports the new value, same
discipline as every other mutating script in this toolkit. See
references/rpgmaker-galleries.md and mz_save_inspect.py for the format.

Find the index first with `python mz_save_inspect.py --names data/System.json
<keyword>` (searches the game's own switch/variable name list, no save
needed) -- prefer a game's own single "unlock everything" switch/variable
over individually flipping every gallery entry, if one exists (see the
RPG Maker MZ case in references/rpgmaker-galleries.md).

usage: python mz_save_set.py <save.rmmzsave> switches <idx> <true|false>
       python mz_save_set.py <save.rmmzsave> variables <idx> <int>
"""
import os, shutil, sys

sys.path.insert(0, os.path.dirname(__file__))
from mz_save_inspect import load_save, save_save

if __name__ == '__main__':
    if len(sys.argv) != 5:
        raise SystemExit(__doc__)
    path, kind, idx, val = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
    if kind == 'switches':
        val = val.lower() in ('true', '1', 'yes')
    elif kind == 'variables':
        val = int(val)
    else:
        raise SystemExit('kind must be "switches" or "variables"')

    save = load_save(path)
    data = save[kind]['_data']
    print('%s[%d]: %r -> %r' % (kind, idx, data[idx] if idx < len(data) else None, val))

    i, bak = 1, path + '.bak'
    while os.path.exists(bak):
        i += 1
        bak = '%s.bak%d' % (path, i)
    shutil.copy2(path, bak)
    print('backup written:', os.path.basename(bak))

    while len(data) <= idx:
        data.append(None)
    data[idx] = val
    save_save(path, save)

    reloaded = load_save(path)
    print('verified %s[%d] = %r' % (kind, idx, reloaded[kind]['_data'][idx]))
