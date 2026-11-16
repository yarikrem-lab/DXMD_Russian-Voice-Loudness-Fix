import os, sys, csv, json, collections, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive

WORK = os.path.dirname(os.path.abspath(__file__))
RUNTIME = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided\runtime"
DLC_RUNTIME = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided\DLC\runtime"
DRY = '--apply' not in sys.argv

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


def pad_fsb5(new_bytes, old_size):
    if len(new_bytes) == old_size:
        return new_bytes
    if len(new_bytes) > old_size:
        return None
    sh = int.from_bytes(new_bytes[12:16], 'little')
    nt = int.from_bytes(new_bytes[16:20], 'little')
    old_data = old_size - 60 - sh - nt
    data_start = 60 + sh + nt
    new_data = new_bytes[data_start:]
    if len(new_data) > old_data:
        return None
    pad = b'\x00' * (old_data - len(new_data))
    out = bytearray(new_bytes[:data_start] + new_data + pad)
    out[20:24] = old_data.to_bytes(4, 'little')
    return bytes(out)


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
    rows = list(csv.reader(open(os.path.join(WORK, 'rebuilt_banks', 'manifest.csv'), encoding='utf-8-sig'), delimiter=';'))[1:]
    manifest = json.load(open(os.path.join(WORK, 'out', 'voice_fsb_manifest_all.json'), encoding='utf-8'))
    by_key = {(r['lang'], r['rel']): r for r in manifest}

    groups = collections.defaultdict(list)
    for lang, rel, out, status in rows:
        if status != 'ok':
            continue
        rec = by_key.get((lang, rel))
        if rec:
            groups[(lang, rec['container'])].append((lang, rel, out, rec))

    jobs = []
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
            jobs.append((lang2, rel, out, cont, loc[0], loc[1], old_size))

    print('jobs', len(jobs), flush=True)

    bad = 0
    big = 0
    for lang, rel, out, cont, apath, abs_off, old_size in jobs:
        if not DRY:
            continue
        with open(apath, 'rb') as f:
            f.seek(abs_off)
            magic = f.read(4)
        if magic != b'FSB5':
            bad += 1
            if bad <= 8:
                print('BAD', cont, rel.split('/')[-1], 'off', abs_off, 'got', magic)
        else:
            nb = open(out, 'rb').read()
            if len(nb) > old_size:
                big += 1
    if DRY:
        print('DRY: bad_magic', bad, 'new_bigger_than_old', big, flush=True)
        return

    patched = 0
    skipped = 0
    fhs = {}
    for lang, rel, out, cont, apath, abs_off, old_size in jobs:
        if apath not in fhs:
            bak = apath + '.bak'
            if not os.path.exists(bak):
                print('backup', apath, flush=True)
                shutil.copy2(apath, bak)
            fhs[apath] = open(apath, 'r+b')
        nb = open(out, 'rb').read()
        nb = pad_fsb5(nb, old_size)
        if nb is None:
            skipped += 1
            continue
        fhs[apath].seek(abs_off)
        fhs[apath].write(nb)
        patched += 1
    for fh in fhs.values():
        fh.close()
    print('DONE patched', patched, 'skipped', skipped, flush=True)


if __name__ == '__main__':
    main()
