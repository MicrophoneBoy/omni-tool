"""Read/write an RPG Maker MZ (.rmmzsave) or MV (.rpgsave) save.

Both engines save the same JSON (JsonEx-wrapped game objects), only the outer
encoding differs. The format is picked by extension, falling back to the first
byte (MZ's zlib stream starts 0x78, MV's base64 text never does).

MZ -- pako deflate + a "binary string" (confirmed against a real game, see the
RPG Maker MZ case in references/rpgmaker-galleries.md): the file on disk is NOT
raw deflate bytes. `StorageManager.jsonToZip` calls
`pako.deflate(json, {to: "string", level: 1})`, and pako's "to: string" output
is a JS *binary string* -- one UTF-16 code unit per raw output byte, values
0-255. `fs.writeFileSync(path, thatString)` then UTF-8-encodes the string to
actually write it, so every byte 0x80-0xFF in the compressed stream becomes a
2-byte UTF-8 sequence on disk. To recover the real deflate stream: decode the
file as UTF-8 text, then map each character's code point back to a single byte.

Read the file in **binary mode** and decode manually -- Python's text-mode
`open(path, encoding='utf-8')` does universal-newline translation by default,
which silently mangles any embedded 0x0D/0x0A byte pair in the compressed
stream (this is what broke the first attempt against a real save; a handful of
KB decompressed fine, then failed with "invalid distance too far back").

MV -- `LZString.compressToBase64(json)`, plain ASCII on disk. See lzstring.py;
re-encoding an untouched MV save reproduces the game's file byte for byte
(checked against saves from four different MV games).

Once decoded, it's normal JSON, but every engine class instance (switches,
variables, self-switches, ...) is wrapped by `JsonEx.stringify` as
`{"_data": <plain array/object>, "@": "ClassName"}`. The actual flat
switches/variables arrays are at `switches['_data']` / `variables['_data']`,
indexed exactly by switch/variable ID -- unset entries are `null`.

Cross-save files: MV plugins like UTA_CommonSave keep a separate
`common.rpgsave` holding `{"gameSwitches": {"<id>": v}, "gameVariables": {...}}`
-- only the IDs the plugin is configured to share, keyed by string ID. Games
often put gallery/recollection flags there because it survives across every
save slot, so check it when flipping a switch in fileN does nothing.

usage:
  python rm_save_inspect.py <save>                    dump a summary
  python rm_save_inspect.py <save> switches           list every True switch index
  python rm_save_inspect.py <save> switches <idx>     print one switch's value
  python rm_save_inspect.py <save> variables <idx>    print one variable's value
  python rm_save_inspect.py --names <System.json> <text>
      search switch/variable names for <text> -- no save needed. System.json
      ships with the game (data/ on MZ, www/data/ on MV) and names every slot.
      This is how the RPG Maker MZ case found its master "unlock everything"
      switch without touching a save.
"""
import json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lzstring import compress_to_base64, decompress_from_base64


def save_format(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == '.rmmzsave':
        return 'mz'
    if ext == '.rpgsave':
        return 'mv'
    with open(path, 'rb') as f:
        return 'mz' if f.read(1) == b'\x78' else 'mv'


def load_save(path):
    with open(path, 'rb') as f:
        data = f.read()
    if save_format(path) == 'mv':
        return json.loads(decompress_from_base64(data.decode('ascii')))
    raw = bytes(ord(c) & 0xFF for c in data.decode('utf-8'))
    return json.loads(zlib.decompress(raw, 15))


def save_save(path, obj):
    new_json = json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
    if save_format(path) == 'mv':
        out = compress_to_base64(new_json).encode('ascii')
    else:
        comp = zlib.compressobj(1, zlib.DEFLATED, 15)
        new_raw = comp.compress(new_json.encode('utf-8')) + comp.flush()
        out = ''.join(chr(b) for b in new_raw).encode('utf-8')
    with open(path, 'wb') as f:
        f.write(out)


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
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        raise SystemExit(__doc__)
    if args[0] == '--names':
        if len(args) != 3:
            raise SystemExit(__doc__)
        for kind, i, name in find_names(args[1], args[2]):
            print('%-10s %5d  %s' % (kind, i, name))
        raise SystemExit

    save = load_save(args[0])
    kind = args[1] if len(args) > 1 else None
    idx = int(args[2]) if len(args) > 2 else None

    if kind is None:
        print('format       %s' % save_format(args[0]).upper())
        if 'gameSwitches' in save:
            print('cross-save file (e.g. UTA_CommonSave): switches=%s variables=%s'
                  % (save['gameSwitches'], save.get('gameVariables')))
            raise SystemExit
        if 'switches' not in save:
            # config/global saves (and plugin side-saves) carry no game state
            print('no switches/variables in this file; top-level keys: %s'
                  % ', '.join(save) if isinstance(save, dict) else type(save).__name__)
            raise SystemExit
        for k in ('switches', 'variables', 'selfSwitches'):
            data = save[k]['_data']
            n = len(data) if isinstance(data, list) else len(data.keys())
            truthy = sum(1 for v in (data if isinstance(data, list) else data.values()) if v)
            print('%-12s %-17s slots=%d truthy/nonzero=%d' % (k, save[k]['@'], n, truthy))
    elif idx is None:
        data = save[kind]['_data']
        for i, v in enumerate(data):
            if v:
                print(i, v)
    else:
        data = save[kind]['_data']
        print(data[idx] if idx < len(data) else None)
