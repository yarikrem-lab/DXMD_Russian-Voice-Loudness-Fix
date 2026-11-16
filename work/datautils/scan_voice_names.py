import os, sys, json, re
from concurrent.futures import ProcessPoolExecutor
import structs, paths

BASE = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"
RUNTIME = os.path.join(BASE, 'runtime')
DLC_RUNTIME = os.path.join(BASE, 'DLC', 'runtime')

HLIB = structs.HLIB.compile()
HLIBInner = structs.HLIBInner

LANG_RE = re.compile(r'/sound/localization/[^/]+/(english|russian)/', re.I)


def scan_one(args):
    hdir, fn = args
    p = os.path.join(hdir, fn)
    try:
        raw = open(p, 'rb').read()
        if b'/sound/localization/' not in raw.lower():
            return []
        hlib = HLIB.parse(raw)
        hi = HLIBInner.parse(hlib.bin1.inner)
        containers = {paths.get_resid(c.path1.string): c for c in hi.resource_containers.arr}
        by_lib = {}
        for res in hi.resources.inner.resources:
            by_lib.setdefault(paths.get_lib_id(res.container_id), []).append(res)
        out = []
        for lib_rid, ress in by_lib.items():
            c = containers[lib_rid]
            cf = paths.get_container_filename(c.path1.string)
            for idx, res in enumerate(ress):
                s = res.path1.string
                low = s.lower()
                if '.pc_fsb' not in low:
                    continue
                m = LANG_RE.search(s)
                if not m:
                    continue
                out.append({
                    'hlib': fn, 'hlib_dir': hdir, 'path': s, 'lang': m.group(1).lower(),
                    'container_file': cf, 'flags': c.flags, 'extra': c.extra_header_len,
                    'idx': idx, 'nres': len(ress), 'nheaders': c.resource_headers.arr_len,
                })
        return out
    except Exception as e:
        return [{'error': repr(e), 'hlib': fn, 'hlib_dir': hdir}]


if __name__ == '__main__':
    args = []
    for d in (RUNTIME, DLC_RUNTIME):
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.pc_headerlib'):
                args.append((d, fn))
    print('headerlibs', len(args), flush=True)
    results = []
    with ProcessPoolExecutor(max_workers=8) as ex:
        for i, recs in enumerate(ex.map(scan_one, args, chunksize=4), 1):
            results.extend(recs)
            if i % 100 == 0:
                print('progress', i, '/', len(args), 'records', len(results), flush=True)
    json.dump(results, open('voice_names.json', 'w', encoding='utf-8'), ensure_ascii=False)
    print('done records', len(results), 'errors', sum(1 for r in results if 'error' in r))
