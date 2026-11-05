"""Dump or edit a TyranoScript save (<project>_sf.sav / <project>_tyrano_data.sav).

Format (verified against a real NW.js-packaged TyranoScript game): the file is
`escape(JSON.stringify(obj))` -- JS's legacy escape(), so ASCII outside
[A-Za-z0-9@*_+-./] becomes %XX and every non-Latin-1 char becomes %uXXXX.
Python's urllib unquote does NOT handle %uXXXX, hence the hand-rolled codec
below. Re-encoding an untouched file reproduces it byte for byte.

  <project>_sf.sav           `sf.*` system variables, shared by every slot --
                             gallery / recollection / ending flags live here
  <project>_tyrano_data.sav  the save slots (each slot carries its own `f.*`)

See references/tyrano-saves.md.

usage:
  python tyrano_save.py <file.sav>                       pretty-print the JSON
  python tyrano_save.py <file.sav> get <dotted.key>      print one value
  python tyrano_save.py <file.sav> set <dotted.key> <json_value>
      e.g. set cg_view true / set replay_list.3 1 / set name '"x"'
      backup + re-read verify, same discipline as the other mutating scripts
"""
import json, os, re, shutil, sys

SAFE = set(b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@*_+-./')


def js_escape(s):
    b = s.encode('utf-16-le', 'surrogatepass')     # escape() works on UTF-16 units
    out = []
    for i in range(0, len(b), 2):
        unit = b[i] | (b[i + 1] << 8)
        if unit in SAFE:
            out.append(chr(unit))
        elif unit < 256:
            out.append('%%%02X' % unit)
        else:
            out.append('%%u%04X' % unit)
    return ''.join(out)


def js_unescape(s):
    def rep(m):
        return chr(int(m.group(1) or m.group(2), 16))
    t = re.sub(r'%u([0-9A-Fa-f]{4})|%([0-9A-Fa-f]{2})', rep, s)
    return t.encode('utf-16-le', 'surrogatepass').decode('utf-16-le')


def load(path):
    with open(path, 'rb') as f:
        return json.loads(js_unescape(f.read().decode('ascii').strip()))


def dump(path, obj):
    with open(path, 'wb') as f:
        f.write(js_escape(json.dumps(obj, separators=(',', ':'), ensure_ascii=False)).encode('ascii'))


def walk(obj, key):
    parts = key.split('.')
    for p in parts[:-1]:
        obj = obj[int(p)] if isinstance(obj, list) else obj[p]
    last = parts[-1]
    return obj, (int(last) if isinstance(obj, list) else last)


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        raise SystemExit(__doc__)
    path = args[0]
    obj = load(path)
    if len(args) == 1:
        print(json.dumps(obj, ensure_ascii=False, indent=1))
    elif args[1] == 'get' and len(args) == 3:
        parent, k = walk(obj, args[2])
        print(json.dumps(parent[k], ensure_ascii=False))
    elif args[1] == 'set' and len(args) == 4:
        parent, k = walk(obj, args[2])
        new = json.loads(args[3])
        old = parent[k] if (isinstance(parent, list) and k < len(parent)) or (
            isinstance(parent, dict) and k in parent) else None
        print('%s: %s -> %s' % (args[2], json.dumps(old, ensure_ascii=False),
                                json.dumps(new, ensure_ascii=False)))
        i, bak = 1, path + '.bak'
        while os.path.exists(bak):
            i += 1
            bak = '%s.bak%d' % (path, i)
        shutil.copy2(path, bak)
        print('backup written:', os.path.basename(bak))
        parent[k] = new
        dump(path, obj)
        parent2, k2 = walk(load(path), args[2])
        print('verified %s = %s' % (args[2], json.dumps(parent2[k2], ensure_ascii=False)))
    else:
        raise SystemExit(__doc__)
