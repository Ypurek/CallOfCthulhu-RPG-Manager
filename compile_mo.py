import struct

def unescape(s):
    result = []
    i = 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            c = s[i+1]
            if c == 'n':
                result.append('\n')
            elif c == 't':
                result.append('\t')
            elif c == '\\':
                result.append('\\')
            elif c == '"':
                result.append('"')
            else:
                result.append(s[i])
                result.append(c)
            i += 2
        else:
            result.append(s[i])
            i += 1
    return ''.join(result)


def compile_po(po_path, mo_path):
    entries = {}
    with open(po_path, encoding='utf-8') as f:
        lines = f.readlines()

    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False

    def flush():
        nonlocal current_msgid, current_msgstr
        if current_msgid is not None and current_msgstr is not None:
            entries[unescape(current_msgid)] = unescape(current_msgstr)
        current_msgid = None
        current_msgstr = None

    for line in lines:
        line = line.rstrip('\n')
        stripped = line.strip()
        if stripped.startswith('#') or stripped == '':
            if in_msgstr:
                flush()
            in_msgid = False
            in_msgstr = False
            continue
        if stripped.startswith('msgid '):
            if in_msgstr:
                flush()
            in_msgid = True
            in_msgstr = False
            current_msgid = stripped[7:-1]
            current_msgstr = None
            continue
        if stripped.startswith('msgstr '):
            in_msgid = False
            in_msgstr = True
            current_msgstr = stripped[8:-1]
            continue
        if stripped.startswith('"') and stripped.endswith('"'):
            val = stripped[1:-1]
            if in_msgid and current_msgid is not None:
                current_msgid += val
            elif in_msgstr and current_msgstr is not None:
                current_msgstr += val

    if in_msgstr:
        flush()

    # Build .mo
    keys = sorted(entries.keys())
    offsets = []
    ids = b''
    strs = b''
    for k in keys:
        v = entries[k]
        kid = k.encode('utf-8')
        vstr = v.encode('utf-8')
        offsets.append((len(kid), len(ids), len(vstr), len(strs)))
        ids += kid + b'\x00'
        strs += vstr + b'\x00'

    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)

    output = struct.pack('<IIIIIII',
        0x950412de, 0, n, 7*4, 7*4 + n*8, 0, 7*4 + n*16)
    for i in range(n):
        output += struct.pack('<II', offsets[i][0], offsets[i][1] + keystart)
    for i in range(n):
        output += struct.pack('<II', offsets[i][2], offsets[i][3] + valuestart)
    output += ids
    output += strs

    with open(mo_path, 'wb') as f:
        f.write(output)
    print(f'Compiled {n} strings to {mo_path}')


compile_po(
    'locale/uk/LC_MESSAGES/django.po',
    'locale/uk/LC_MESSAGES/django.mo'
)
