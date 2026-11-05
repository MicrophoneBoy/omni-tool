"""Pure-Python LZString compressToBase64 / decompressFromBase64.

RPG Maker MV saves (.rpgsave) are `LZString.compressToBase64(JSON)` -- the
pieroxy lz-string library bundled as www/js/libs/lz-string.js. No pip package
needed; this is a straight port of the two functions MV's StorageManager uses.

JS strings are UTF-16, so both directions work on UTF-16 code units (a 🎮 is two
units, a surrogate pair) -- iterating Python code points instead would write
different bits than the game and break on anything outside the BMP.
"""
import base64, struct


def _to_units(s):
    b = s.encode('utf-16-le', 'surrogatepass')
    return [chr(u) for u in struct.unpack('<%dH' % (len(b) // 2), b)]


def _from_units(parts):
    s = ''.join(parts)
    return s.encode('utf-16-le', 'surrogatepass').decode('utf-16-le')

KEY = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
_REV = {c: i for i, c in enumerate(KEY)}


def decompress_from_base64(s):
    s = s.strip()
    if not s:
        return ''
    vals = [_REV[c] for c in s if c in _REV]
    reset = 32
    pos, val, idx = reset, vals[0], 1
    dictionary = {0: 0, 1: 1, 2: 2}
    enlarge, dict_size, num_bits = 4, 4, 3

    def bits(n):
        nonlocal pos, val, idx
        out, power, maxp = 0, 1, 1 << n
        while power != maxp:
            resb = val & pos
            pos >>= 1
            if pos == 0:
                pos = reset
                val = vals[idx] if idx < len(vals) else 0
                idx += 1
            if resb:
                out |= power
            power <<= 1
        return out

    nxt = bits(2)
    if nxt == 2:
        return ''
    c = chr(bits(8 if nxt == 0 else 16))
    dictionary[3] = c
    w = c
    result = [c]
    while True:
        if idx > len(vals):
            return _from_units(result)
        cc = bits(num_bits)
        if cc in (0, 1):
            dictionary[dict_size] = chr(bits(8 if cc == 0 else 16))
            dict_size += 1
            cc = dict_size - 1
            enlarge -= 1
        elif cc == 2:
            return _from_units(result)
        if enlarge == 0:
            enlarge = 1 << num_bits
            num_bits += 1
        if cc in dictionary:
            entry = dictionary[cc]
        elif cc == dict_size:
            entry = w + w[0]
        else:
            raise ValueError('corrupt LZString data')
        result.append(entry)
        dictionary[dict_size] = w + entry[0]
        dict_size += 1
        enlarge -= 1
        w = entry
        if enlarge == 0:
            enlarge = 1 << num_bits
            num_bits += 1


def compress_to_base64(s):
    """Byte-identical to the lz-string 1.3.x that MV ships: LZ bit stream packed
    into 16-bit chars (flush always pads to the next char), then plain base64 of
    those chars as big-endian bytes. Newer 1.4.x emits 6-bit groups directly and
    differs in the trailing char -- the game reads either, but matching its own
    writer means an untouched save round-trips to the exact same file."""
    if not s:
        return ''
    bitbuf = []

    def write(value, n):
        for _ in range(n):
            bitbuf.append(value & 1)
            value >>= 1

    dictionary, to_create = {}, set()
    w, enlarge, dict_size, num_bits = '', 2, 3, 2

    def emit(w):
        nonlocal enlarge, num_bits
        if w in to_create:
            code = ord(w[0])
            if code < 256:
                write(0, num_bits)
                write(code, 8)
            else:
                write(1, num_bits)
                write(code, 16)
            enlarge -= 1
            if enlarge == 0:
                enlarge = 1 << num_bits
                num_bits += 1
            to_create.discard(w)
        else:
            write(dictionary[w], num_bits)
        enlarge -= 1
        if enlarge == 0:
            enlarge = 1 << num_bits
            num_bits += 1

    for c in _to_units(s):
        if c not in dictionary:
            dictionary[c] = dict_size
            dict_size += 1
            to_create.add(c)
        wc = w + c
        if wc in dictionary:
            w = wc
        else:
            emit(w)
            dictionary[wc] = dict_size
            dict_size += 1
            w = c
    if w:
        emit(w)
    write(2, num_bits)
    bitbuf.extend([0] * (16 - len(bitbuf) % 16))
    out = bytearray()
    for i in range(0, len(bitbuf), 8):
        byte = 0
        for b in bitbuf[i:i + 8]:
            byte = (byte << 1) | b
        out.append(byte)
    return base64.b64encode(bytes(out)).decode('ascii')
