"""List every filename packed in a Ren'Py RPA-3.0 archive.

usage: python rpa_list.py path/to/scripts.rpa
"""
import sys, zlib, pickle


def read_index(path):
    with open(path, 'rb') as f:
        header = f.readline()
        parts = header.split()
        # RPA-3.0 <offset_hex> <key_hex>
        version = parts[0]
        offset = int(parts[1], 16)
        key = int(parts[2], 16)

        f.seek(offset)
        data = f.read()
        index = pickle.loads(zlib.decompress(data))

    out = {}
    for name, entries in index.items():
        new_entries = []
        for e in entries:
            if len(e) == 2:
                off, ln = e
                prefix = b''
            else:
                off, ln, prefix = e
                off ^= key
                ln ^= key
            new_entries.append((off, ln, prefix))
        out[name] = new_entries
    return version, offset, key, out


if __name__ == '__main__':
    version, offset, key, index = read_index(sys.argv[1])
    print(f"version={version} offset={offset:#x} key={key:#x} num_files={len(index)}")
    for name in sorted(index.keys()):
        print(name)
