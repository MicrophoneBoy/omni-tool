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


def has_sqlite_file(paths):
    for p in paths:
        if not p.lower().endswith(SQLITE_CANDIDATE_EXTS) or not os.path.isfile(p):
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
     # (nw_100_percent.pak, locales/*.pak -- hit on the an RPG Maker MZ game RPG Maker MZ
     # case), so require the "Paks" cook-output folder or the WindowsNoEditor
     # naming convention instead of just the extension.
     lambda paths, names: has_dir_named(paths, 'paks') or has_suffix(paths, '-windowsnoeditor.pak')),
    ('PyInstaller (Python)', 'pyinstaller-python-saves.md',
     lambda paths, names: has_name(names, 'base_library.zip') or has_dir_named(paths, '_internal')),
    ('Unity Easy Save 2 plugin', 'unity-es2-saves.md',
     # plain substring "es2" false-positives on ordinary words (valves2.png,
     # titles2, Cobblestones2.png -- also from the an RPG Maker MZ game case), so require
     # it start a word instead of appearing anywhere in the filename.
     lambda paths, names: any(
         p.lower().endswith('.es3') or re.search(r'\bes2', os.path.basename(p), re.I)
         for p in paths)),
    ('RPG Maker XP/VX/VX Ace (RGSS)', 'interpreter-hooking.md',
     lambda paths, names: has_name(names, 'rgss1.dll', 'rgss2.dll', 'rgss3.dll')),
    ('RPG Maker MZ/MV (NW.js)', 'rpgmaker-galleries.md (gallery unlocks) or interpreter-hooking.md',
     lambda paths, names: has_name(names, 'rmmz_core.js', 'rmmv_core.js')
     or (has_dir_named(paths, 'www') and has_name(names, 'package.json'))),
    ('KiriKiri / KiriKiriZ', 'interpreter-hooking.md',
     lambda paths, names: has_suffix(paths, '.xp3')),
    ('Wolf RPG Editor', 'interpreter-hooking.md',
     lambda paths, names: has_name(names, 'data.wolf')),
    ('SQLite database present', 'sqlite-saves.md',
     lambda paths, names: has_sqlite_file(paths)),
]

MAX_DEPTH = 3


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
    if len(sys.argv) < 2:
        raise SystemExit('usage: python detect_engine.py <game folder>')
    root = sys.argv[1]
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
