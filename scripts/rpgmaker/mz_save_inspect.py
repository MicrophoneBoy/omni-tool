"""Read/write an RPG Maker MZ save (.rmmzsave): the pako-deflate + JsonEx format.

Save format background (confirmed against a real game, see the RPG Maker MZ case
in references/rpgmaker-galleries.md): the file on disk is NOT raw deflate bytes.
`StorageManager.jsonToZip` calls `pako.deflate(json, {to: "string", level: 1})`,
and pako's "to: string" output is a JS *binary string* -- one UTF-16 code unit
per raw output byte, values 0-255. `fs.writeFileSync(path, thatString)` then
UTF-8-encodes the string to actually write it, so every byte 0x80-0xFF in the
compressed stream becomes a 2-byte UTF-8 sequence on disk. To recover the real
deflate stream: decode the file as UTF-8 text, then map each character's code
point back to a single byte.

Read the file in **binary mode** and decode manually -- Python's text-mode
`open(path, encoding='utf-8')` does universal-newline translation by default,
which silently mangles any embedded 0x0D/0x0A byte pair in the compressed
stream (this is what broke the first attempt against a real save; a handful of
KB decompressed fine, then failed with "invalid distance too far back").

Once decompressed, it's normal JSON, but every engine class instance (switches,
variables, self-switches, ...) is wrapped by `JsonEx.stringify` as
`{"_data": <plain array/object>, "@": "ClassName"}`. The actual flat
switches/variables arrays are at `switches['_data']` / `variables['_data']`,
indexed exactly by switch/variable ID -- unset entries are `null`.

usage:
  python mz_save_inspect.py <save.rmmzsave>                    dump a summary
  python mz_save_inspect.py <save.rmmzsave> switches           list every True switch index
  python mz_save_inspect.py <save.rmmzsave> switches <idx>     print one switch's value
  python mz_save_inspect.py <save.rmmzsave> variables <idx>    print one variable's value
  python mz_save_inspect.py --names <data/System.json> <text>  search switch/variable
                                                                 names for <text> -- no
                                                                 save needed, System.json
                                                                 ships with the game and
                                                                 names every slot. This is
                                                                 how the RPG Maker MZ case
                                                                 found its master
                                                                 "unlock everything" switch
                                                                 without touching a save.
"""
import json, sys, zlib


def load_save(path):
    with open(path, 'rb') as f:
        text = f.read().decode('utf-8')
    raw = bytes(ord(c) & 0xFF for c in text)
    return json.loads(zlib.decompress(raw, 15))


def save_save(path, obj):
    new_json = json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
    comp = zlib.compressobj(1, zlib.DEFLATED, 15)
    new_raw = comp.compress(new_json.encode('utf-8')) + comp.flush()
    new_text = ''.join(chr(b) for b in new_raw)
    with open(path, 'wb') as f:
        f.write(new_text.encode('utf-8'))


def find_names(system_path, needle):
    with open(system_path, encoding='utf-8') as f:
        sysd = json.load(f)
    hits = []
    for kind in ('switches', 'variables'):
        for i, name in enumerate(sysd.get(kind, [])):
            if name and needle in name:
                hits.append((kind, i, name))
    return hits


if __name__ == '__main__':
    if len(sys.argv) >= 2 and sys.argv[1] == '--names':
        system_path, needle = sys.argv[2], sys.argv[3]
        for kind, i, name in find_names(system_path, needle):
            print('%-10s %5d  %s' % (kind, i, name))
        raise SystemExit

    if len(sys.argv) < 2:
        raise SystemExit(__doc__)

    save = load_save(sys.argv[1])
    kind = sys.argv[2] if len(sys.argv) > 2 else None
    idx = int(sys.argv[3]) if len(sys.argv) > 3 else None

    if kind is None:
        for k in ('switches', 'variables', 'selfSwitches'):
            data = save[k]['_data']
            n = len(data) if isinstance(data, list) else len(data.keys())
            truthy = sum(1 for v in (data if isinstance(data, list) else data.values()) if v)
            print('%-12s %-10s slots=%d truthy/nonzero=%d' % (k, save[k]['@'], n, truthy))
    elif idx is None:
        data = save[kind]['_data']
        for i, v in enumerate(data):
            if v:
                print(i, v)
    else:
        print(save[kind]['_data'][idx])
