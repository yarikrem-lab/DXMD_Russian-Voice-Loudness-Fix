import os, sys, json, re, importlib.util
import structs, paths

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(WORK, 'out')
BASE = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"
RUNTIME = os.path.join(BASE, 'runtime')
DLC_RUNTIME = os.path.join(BASE, 'DLC', 'runtime')

spec = importlib.util.spec_from_file_location('sean_archive', os.path.join(WORK, 'archive.py'))
sean_archive = importlib.util.module_from_spec(spec)
sys.path.insert(0, WORK)
spec.loader.exec_module(sean_archive)

HLIB = structs.HLIB.compile()
HLIBInner = structs.HLIBInner
lang_map = {'english': 'en', 'russian': 'ru'}


def safe_rel(path):
    m = re.match(r'^\[assembly:(.*?)\]\.(.*)$', path, re.I)
    s = (m.group(1).lstrip('/') + '.' + m.group(2)) if m else path
    s = s.replace('?/', '/')
    for ch in ':*?"<>|':
        s = s.replace(ch, '_')
    return os.path.join(*[p for p in s.split('/') if p not in ('', '.', '..')])


def main():
    names = json.load(open(os.path.join(WORK, 'datautils', 'voice_names.json'), encoding='utf-8'))
    idx = json.load(open(os.path.join(WORK, 'datautils', 'archive_index.json'), encoding='utf-8'))
    manifest = json.load(open(os.path.join(OUT, 'voice_manifest.json')))

    loc = {}
    for an, info in idx.items():
        for f in info['files']:
            loc.setdefault(f, []).append(an)

    base = {lang: set(manifest[lang]) for lang in ['en', 'ru']}
    by_key = {}
    for r in names:
        lang = lang_map.get(r['lang'], r['lang'])
        by_key[(lang, r['container_file'], r['idx'])] = r

    targets = {}
    for r in names:
        lang = lang_map.get(r['lang'], r['lang'])
        cf = r['container_file']
        if cf in base[lang] and r['flags'] != 2:
            continue
        targets.setdefault((lang, cf), []).append(r)

    print('extra targets', len(targets), flush=True)
    archives = {}

    def arch(name):
        if name not in archives:
            root = DLC_RUNTIME if (name.startswith('DLC') or name.startswith('DLCPack')) else RUNTIME
            archives[name] = sean_archive.ArchiveFile(os.path.join(root, name))
        return archives[name]

    meta_cache = {}

    def headers_for(hlib_dir, hname, cf):
        key = (hlib_dir, hname)
        if key not in meta_cache:
            hlib = HLIB.parse_file(os.path.join(hlib_dir, hname))
            hi = HLIBInner.parse(hlib.bin1.inner)
            m = {}
            for c in hi.resource_containers.arr:
                m[paths.get_container_filename(c.path1.string)] = c
            meta_cache[key] = m
        return meta_cache[key][cf]

    records = []
    ok = 0
    errors = 0
    for (lang, cf), rs in sorted(targets.items()):
        av = [a for a in loc.get(cf, []) if not a.startswith('Game.layer.0.en') and not a.startswith('Game.layer.0.ru')]
        if not av:
            av = loc.get(cf, [])
        if not av:
            errors += len(rs)
            continue
        an = av[0]
        d = os.path.join(WORK, 'work', 'containers_extra', an)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, cf)
        if not os.path.exists(p):
            try:
                arch(an).extract(cf, d)
            except Exception as e:
                errors += len(rs)
                continue
        data = open(p, 'rb').read()
        flags = rs[0]['flags']
        if flags & 4:
            items = []
            off = 24
            n = 0
            while off + 24 <= len(data):
                if data[off:off + 4] != b'SBSF':
                    break
                ln = int.from_bytes(data[off + 12:off + 16], 'little')
                if ln <= 0 or off + 24 + ln > len(data):
                    break
                payload = data[off + 24:off + 24 + ln]
                items.append((n, payload))
                off += 24 + ln
                n += 1
        else:
            h = headers_for(rs[0]['hlib_dir'], rs[0]['hlib'], cf)
            hdrs = [x.inner for x in h.resource_headers.arr]
            items = []
            off = 24
            for i, hd in enumerate(hdrs):
                items.append((i, data[off:off + hd.length]))
                off += hd.length
        if len(items) < len(rs):
            errors += 1
            continue
        for i, payload in items:
            r = by_key.get((lang, cf, i))
            if r is None:
                continue
            off = payload.find(b'FSB5')
            if off < 0:
                errors += 1
                continue
            blob = payload[off:]
            rel = safe_rel(r['path'])
            dst = os.path.join(OUT, 'voice_fsb', lang, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if not os.path.exists(dst):
                with open(dst, 'wb') as f:
                    f.write(blob)
            records.append({'lang': lang, 'container': cf, 'idx': i, 'path': r['path'],
                            'rel': rel, 'fsb_offset': off, 'size': len(blob), 'source_archive': an})
            ok += 1
        print('container', lang, cf, 'items', len(rs), 'written', ok, flush=True)
    json.dump(records, open(os.path.join(OUT, 'voice_fsb_manifest_extra.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('DONE extra files', ok, 'errors', errors, flush=True)


if __name__ == '__main__':
    main()
