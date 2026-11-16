import os, sys, csv, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive

WORK = os.path.dirname(os.path.abspath(__file__))
RUNTIME = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided\runtime"
DLC_RUNTIME = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided\DLC\runtime"
GAME_ROOT = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"

_arc_index = None
_arch_objs = {}
_chunk_cache = {}


def walk_resource_offset(data, idx):
    off = 24
    for i in range(idx):
        if off + 24 > len(data):
            raise RuntimeError('walk overflow')
        ln = int.from_bytes(data[off + 12:off + 16], 'little')
        off += 24 + ln
    return off


def get_chunks(lang, rec):
    global _arc_index
    if _arc_index is None:
        _arc_index = json.load(open(os.path.join(WORK, 'datautils', 'archive_index.json'), encoding='utf-8'))
    key = rec['container']
    if key in _chunk_cache:
        return _chunk_cache[key]
    cands = [an for an, info in _arc_index.items() if rec['container'] in info['files']]
    an = None
    for c in cands:
        if lang == 'ru' and 'ru' in c:
            an = c
            break
    if an is None and cands:
        an = cands[0]
    if an is None:
        _chunk_cache[key] = None
        return None
    root = DLC_RUNTIME if an.startswith('DLC') else RUNTIME
    apath = os.path.join(root, an)
    if apath not in _arch_objs:
        _arch_objs[apath] = archive.ArchiveFile(apath)
    a = _arch_objs[apath]
    f = a.files[rec['container']]
    chunks = []
    for c in f.chunks:
        cpath = os.path.join(os.path.dirname(apath), str(a.links[c.archive]))
        chunks.append((cpath, c.offset, c.begin, c.length))
    _chunk_cache[key] = chunks
    return chunks


def locate(chunks, off):
    for cpath, c_off, c_begin, c_len in chunks:
        if c_begin <= off < c_begin + c_len:
            return (cpath, c_off + (off - c_begin))
    return None


def main():
    rows = list(csv.reader(open(os.path.join(WORK, 'rebuilt_banks', 'manifest.csv.fullbak'), encoding='utf-8-sig'), delimiter=';'))[1:]
    manifest = json.load(open(os.path.join(WORK, 'out', 'voice_fsb_manifest_all.json'), encoding='utf-8'))
    by_key = {(r['lang'], r['rel']): r for r in manifest}

    groups = collections.defaultdict(list)
    for lang, rel, out, status in rows:
        if status != 'ok':
            continue
        rec = by_key.get((lang, rel))
        if rec:
            groups[(lang, rec['container'])].append((lang, rel, out, rec))

    patches = []
    missing = 0
    for (lang, cont), items in sorted(groups.items()):
        rec0 = items[0][3]
        if rec0.get('source_archive'):
            cpath = os.path.join(WORK, 'work', 'containers_extra', rec0['source_archive'], cont)
        else:
            cpath = os.path.join(WORK, 'out', lang + '1', cont)
        if not os.path.exists(cpath):
            continue
        cdata = open(cpath, 'rb').read()
        chunks = get_chunks(lang, rec0)
        if chunks is None:
            continue
        for lang2, rel, out, rec in items:
            try:
                res_off = walk_resource_offset(cdata, rec['idx'])
            except Exception:
                continue
            fsb_off = res_off + 24 + rec['fsb_offset']
            old_size = os.path.getsize(os.path.join(WORK, 'out', 'voice_fsb', lang2, rel))
            loc = locate(chunks, fsb_off)
            if loc is None:
                continue
            apath, abs_off = loc
            # relative path from game root
            rel_archive = os.path.relpath(apath, GAME_ROOT)
            new_fsb = out  # absolute path; we'll store basename + copy
            patches.append({
                'archive': rel_archive,
                'offset': abs_off,
                'old_size': old_size,
                'new_fsb': os.path.basename(out),
                'rel': rel,
            })

    print('patches:', len(patches), flush=True)
    # check sizes (exclude too-big)
    out_dir = os.path.join(WORK, 'rebuilt_banks')
    fit = 0
    too_big = 0
    final = []
    for p in patches:
        nb = os.path.getsize(os.path.join(out_dir, p['new_fsb']))
        if nb > p['old_size']:
            too_big += 1
            continue
        final.append(p)
        fit += 1
    print('fit:', fit, 'too_big:', too_big, flush=True)

    json.dump(final, open(os.path.join(WORK, 'mod_patches.json'), 'w'), indent=1)
    print('dumped mod_patches.json with', len(final), 'patches', flush=True)


if __name__ == '__main__':
    main()
