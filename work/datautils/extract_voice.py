import os, json, re

WORK = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(WORK, 'out')
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
    by_key = {}
    for r in names:
        if 'error' in r:
            continue
        lang = lang_map.get(r['lang'], r['lang'])
        by_key[(lang, r['container_file'], r['idx'])] = r['path']

    manifest = json.load(open(os.path.join(OUT, 'voice_manifest.json')))
    records = []
    errors = 0
    written = 0
    for lang in ['en', 'ru']:
        src_dir = os.path.join(OUT, lang + '1')
        dst_dir = os.path.join(OUT, 'voice_fsb', lang)
        os.makedirs(dst_dir, exist_ok=True)
        for fn, info in manifest.get(lang, {}).items():
            data = open(os.path.join(src_dir, fn), 'rb').read()
            for it in info['items']:
                path = by_key.get((lang, fn, it['idx']))
                if path:
                    rel = safe_rel(path)
                else:
                    rel = '%s/x%05d.pc_fsb' % (fn, it['idx'])
                    errors += 1
                dst = os.path.join(dst_dir, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                payload = data[it['offset'] + 24: it['offset'] + 24 + it['length']]
                off = it['fsb_offset']
                blob = payload[off:] if off >= 0 else b''
                if not blob.startswith(b'FSB5'):
                    errors += 1
                    continue
                if not os.path.exists(dst):
                    with open(dst, 'wb') as f:
                        f.write(blob)
                    written += 1
                records.append({
                    'lang': lang, 'container': fn, 'idx': it['idx'], 'path': path,
                    'rel': rel, 'fsb_offset': off, 'size': len(blob),
                })
        print(lang, 'done, files', written, 'errors', errors, flush=True)
    json.dump(records, open(os.path.join(OUT, 'voice_fsb_manifest.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('DONE files', written, 'errors', errors)


if __name__ == '__main__':
    main()
