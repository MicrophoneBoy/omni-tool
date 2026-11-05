"""Scan a game's install folder and guess which engine it is, pointing at the
relevant references/ doc. A cheap first step before manually grepping around --
see SKILL.md "How to approach a new game" step 2.

usage: python detect_engine.py "C:\\path\\to\\game folder"

Matches by file/folder signature, not by asking the game anything -- multiple
signatures can hit at once (e.g. a Unity IL2CPP game that also ships a PDF
manual), so this reports every match rather than picking one guess.
"""
import os, re, sys

# Each entry: (engine label, doc to read, checker(path_list, names_lower) -> bool)
# path_list is every file/dir path found (recursive, depth-limited); names_lower is
# the set of their lowercased basenames, for fast membership checks.


def has_name(names, *candidates):
    return any(c in names for c in candidates)


def has_suffix(paths, suffix):
    return any(p.lower().endswith(suffix) for p in paths)


def has_dir_named(paths, fragment):
    return any(fragment in p.lower() and os.path.isdir(p) for p in paths)


SQLITE_MAGIC = b'SQLite format 3\x00'
# Extension is not reliable for SQLite (see references/sqlite-saves.md), but reading
# every file's header would be slow on a large game folder -- narrow to files that at
# least look like they could be save/database files first.
SQLITE_CANDIDATE_EXTS = ('.db', '.sqlite', '.sqlite3', '.sav', '.dat', '.save')
# OS / image-viewer thumbnail caches that happen to be SQLite (photothumb.db sat
# in an RPG Maker MV game's www/img/ folders) -- never game saves.
SQLITE_IGNORE = {'photothumb.db', 'thumbs.db', 'thumbcache.db'}


def has_sqlite_file(paths):
    for p in paths:
        if (not p.lower().endswith(SQLITE_CANDIDATE_EXTS)
                or os.path.basename(p).lower() in SQLITE_IGNORE or not os.path.isfile(p)):
            continue
        try:
            with open(p, 'rb') as f:
                if f.read(16) == SQLITE_MAGIC:
                    return True
        except OSError:
            continue
    return False


SIGNATURES = [
    ('Unity (IL2CPP)', 'unity-il2cpp-saves.md',
     lambda paths, names: has_name(names, 'gameassembly.dll')),
    ('Unity (Mono)', 'unity-mono-saves.md',
     lambda paths, names: has_dir_named(paths, 'managed') and not has_name(names, 'gameassembly.dll')),
    ("Ren'Py", 'renpy-galleries.md (or rpa-archives.md if scripts.rpa is packed)',
     lambda paths, names: has_dir_named(paths, 'renpy') and has_dir_named(paths, 'game')),
    ('GameMaker', 'gamemaker-datawin.md',
     lambda paths, names: has_name(names, 'data.win')),
    ('Godot', 'godot-saves.md',
     lambda paths, names: has_suffix(paths, '.pck') or has_name(names, 'project.godot')),
    ('Unreal Engine', 'unreal-gvas-saves.md',
     # bare ".pak" alone false-positives on NW.js/Chromium's own resource paks
     # (nw_100_percent.pak, locales/*.pak -- hit on an RPG Maker MZ
     # case), so require the "Paks" cook-output folder or the WindowsNoEditor
     # naming convention instead of just the extension.
     lambda paths, names: has_dir_named(paths, 'paks') or has_suffix(paths, '-windowsnoeditor.pak')),
    ('PyInstaller (Python)', 'pyinstaller-python-saves.md',
     lambda paths, names: has_name(names, 'base_library.zip') or has_dir_named(paths, '_internal')),
    ('Unity Easy Save 2 plugin', 'unity-es2-saves.md',
     # plain substring "es2" false-positives on ordinary words (valves2.png,
     # titles2, Cobblestones2.png -- also from the RPG Maker MZ case), so require
     # it start a word instead of appearing anywhere in the filename.
     lambda paths, names: any(
         p.lower().endswith('.es3') or re.search(r'\bes2', os.path.basename(p), re.I)
         for p in paths)),
    ('RPG Maker XP/VX/VX Ace (RGSS)', 'interpreter-hooking.md',
     # the RGSS dll often lives in the shared RTP install, not the game folder
     # (an RPG Maker VX Ace game here shipped only Game.exe + Data/*.rvdata2),
     # so also match the engine's own data/archive extensions.
     lambda paths, names: has_name(names, 'rgss1.dll', 'rgss2.dll', 'rgss3.dll')
     or any(p.lower().endswith(('.rxdata', '.rvdata', '.rvdata2', '.rgssad', '.rgss2a', '.rgss3a'))
            for p in paths)),
    ('RPG Maker MZ (NW.js)', 'rpgmaker-galleries.md (gallery unlocks) or interpreter-hooking.md',
     lambda paths, names: has_name(names, 'rmmz_core.js') or has_suffix(paths, '.rmmzsave')),
    ('RPG Maker MV (NW.js)', 'rpgmaker-galleries.md (gallery unlocks) or interpreter-hooking.md',
     # MV's core is rpg_core.js (there is no "rmmv_core.js"). Saves catch MV
     # builds whose js/ is packed or renamed but which still write www/save/.
     # Deliberately NOT "www/ + package.json": every NW.js app has that, and
     # it false-positived on MTool's own UI.
     lambda paths, names: has_name(names, 'rpg_core.js') or has_suffix(paths, '.rpgsave')),
    ('KiriKiri / KiriKiriZ', 'interpreter-hooking.md',
     lambda paths, names: has_suffix(paths, '.xp3')),
    ('Wolf RPG Editor', 'interpreter-hooking.md',
     lambda paths, names: has_name(names, 'data.wolf')),
    ('TyranoScript', 'tyrano-saves.md',
     # NW.js builds usually pack data/ and tyrano/ into the exe, so the save
     # file next to it may be the only loose clue
     lambda paths, names: any(n.startswith('tyranoproject') or n.endswith('_sf.sav') for n in names)
     # exact folder name: MTool's own "TyranoRaw" backup dir matched a prefix test
     or has_name(names, 'tyrano')),
    ('SQLite database present', 'sqlite-saves.md',
     lambda paths, names: has_sqlite_file(paths)),
]

# 4, not 3: downloaded games are often double-wrapped (Game/Game/www/js/...),
# which put an RPG Maker MV game's rpg_core.js one level out of reach.
MAX_DEPTH = 4


def walk(root):
    paths = []
    root = os.path.abspath(root)
    base_depth = root.rstrip('\\/').count(os.sep)
    for dirpath, dirnames, filenames in os.walk(root):
        depth = dirpath.rstrip('\\/').count(os.sep) - base_depth
        if depth >= MAX_DEPTH:
            dirnames[:] = []
            continue
        for name in dirnames + filenames:
            paths.append(os.path.join(dirpath, name))
    return paths


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] in ('-h', '--help'):
        raise SystemExit(__doc__)
    root = sys.argv[1]
    if not os.path.isdir(root):
        raise SystemExit('not a folder: %s' % root)
    paths = walk(root)
    names = {os.path.basename(p).lower() for p in paths}

    hits = [(label, doc) for label, doc, check in SIGNATURES if check(paths, names)]

    print('scanned %d files/dirs (depth <= %d) under %s' % (len(paths), MAX_DEPTH, root))
    if not hits:
        print('no known signature matched -- check references/workflow.md for the '
              'general "look for a plain save first" checklist and inspect by hand')
    else:
        print('possible engine(s):')
        for label, doc in hits:
            print('  %-32s -> references/%s' % (label, doc))
        if len(hits) > 1:
            print('multiple signatures matched -- read the game folder structure to '
                  'disambiguate (e.g. a bundled redistributable can trigger a false hit)')
