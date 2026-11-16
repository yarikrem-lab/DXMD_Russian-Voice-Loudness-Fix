import os, json, struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'out'))
OUT = os.path.join(ROOT, 'voice_manifest.json')


def walk(data):
    off = 24
    n = 0
    total = 0
    items = []
    while off + 24 <= len(data):
        fourcc = data[off:off+4]
        length = int.from_bytes(data[off+12:off+16], 'little')
        tot = length + 24
        if fourcc != b'SBSF' or length <= 0 or off + tot > len(data):
            break
        payload = data[off+24:off+tot]
        fsb = payload.find(b'FSB5')
        items.append({'idx': n, 'offset': off, 'length': length, 'fsb_offset': fsb if fsb >= 0 else -1})
        total += length
        off += tot
        n += 1
    return items, total


def main():
    out = {}
    for lang in ['en', 'ru']:
        d = os.path.join(ROOT, lang + '1')
        files = sorted(f for f in os.listdir(d) if f.endswith('.pc_resourcelib'))
        grand = 0
        conts = 0
        for i, fn in enumerate(files, 1):
            p = os.path.join(d, fn)
            data = open(p, 'rb').read()
            if data[24:28] != b'SBSF':
                continue
            items, total = walk(data)
            if not items:
                continue
            conts += 1
            grand += total
            out.setdefault(lang, {})[fn] = {'size': len(data), 'items': items}
            if i % 100 == 0:
                print(lang, i, '/', len(files), 'voice containers', conts, flush=True)
        print(lang, 'containers', conts, 'bytes', grand, flush=True)
    json.dump(out, open(OUT, 'w'))
    print('done')


if __name__ == '__main__':
    main()
