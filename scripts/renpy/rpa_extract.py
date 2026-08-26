"""Extract files from a Ren'Py RPA-3.0 archive.

usage: python rpa_extract.py path/to/scripts.rpa out_dir/ [name_filter]

name_filter, if given, is a plain substring match against the archive's internal
paths (e.g. "gallery/" to pull just one folder). Omit it to extract everything.
"""
import sys, os
from rpa_list import read_index

if __name__ == '__main__':
    rpa_path = sys.argv[1]
    out_dir = sys.argv[2]
    name_filter = sys.argv[3] if len(sys.argv) > 3 else None

    _, _, _, index = read_index(rpa_path)

    with open(rpa_path, 'rb') as f:
        for name, entries in index.items():
            if name_filter and name_filter not in name:
                continue
            for off, ln, prefix in entries:
                if isinstance(prefix, str):
                    # Python-2-originated pickle data can hand back str instead of bytes.
                    prefix = prefix.encode('latin-1')
                f.seek(off)
                content = prefix + f.read(ln - len(prefix))
                out_path = os.path.join(out_dir, name)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, 'wb') as out:
                    out.write(content)
                print("extracted", name, len(content))
