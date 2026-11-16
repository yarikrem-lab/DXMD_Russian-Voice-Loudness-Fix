import os, sys, json, csv, subprocess, shutil, collections, re, hashlib
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fsb5'))
from fsb5 import FSB5

FSBANK = r"C:\Program Files (x86)\FMOD SoundSystem\FMOD Studio API Windows\bin\fsbankcl.exe"
WORK = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(WORK, 'out', 'voice_fsb_manifest_all.json')
RU_ROOT = r"D:\opencodeall\convert\ru"
FIX_ROOT = r"D:\opencodeall\convert\fix"
SILENT_REPORT = os.path.join(FIX_ROOT, 'report_silent_fixed.csv')
OUT_DIR = os.path.join(WORK, 'rebuilt_banks')
QUALITY = 15


def bank_stem(rel):
    b = os.path.basename(rel.replace('\\', '/'))
    if b.lower().endswith('.pc_fsb'):
        b = b[:-7]
    if b.lower().endswith('.wavebank'):
        b = b[:-9]
    return b


def build_wav_map(root):
    m = {}
    for r, d, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith('.wav'):
                base = f[:-4]
                m[base] = os.path.join(r, f)
                m.setdefault(re.sub(r'__[0-9a-f]{8}$', '', base), os.path.join(r, f))
    return m


def build_one(args):
    lang, rel, entries = args
    tmp = os.path.join(WORK, 'tmp_build', hashlib.sha1((lang + rel).encode()).hexdigest()[:16])
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    for n, src in entries:
        if src is None:
            continue
        shutil.copyfile(src, os.path.join(tmp, n + '.wav'))
    out = os.path.join(OUT_DIR, hashlib.sha1((lang + rel).encode()).hexdigest() + '.fsb')
    p = subprocess.run([FSBANK, '-o', out, '-format', 'vorbis', '-quality', str(QUALITY),
                        '-no_loop', '-recursive', tmp],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    shutil.rmtree(tmp, ignore_errors=True)
    if p.returncode != 0 or not os.path.exists(out):
        return (lang, rel, out, 'error:' + p.stderr.decode('utf-8', 'replace')[-120:])
    return (lang, rel, out, 'ok')


def main():
    # 1. read 249 silent normalized files
    silent = []
    with open(SILENT_REPORT, encoding='utf-8-sig') as f:
        for row in csv.DictReader(f, delimiter=';'):
            if row['status'] == 'normalized':
                silent.append(row)
    print('silent normalized files:', len(silent), flush=True)

    # 2. overwrite fix WAVs with original RU
    reverted = 0
    for s in silent:
        src = os.path.join(RU_ROOT, s['code'], s['file'])
        dst = os.path.join(FIX_ROOT, s['code'], s['file'])
        if os.path.exists(src) and os.path.exists(dst):
            shutil.copyfile(src, dst)
            reverted += 1
        else:
            print('  MISSING', s['code'], s['file'], 'src', os.path.exists(src), 'dst', os.path.exists(dst), flush=True)
    print('reverted fix WAVs:', reverted, flush=True)

    # 3. map files to banks
    recs = json.load(open(MANIFEST, encoding='utf-8'))
    stem_rel = {}
    seen = set()
    for r in recs:
        k = (r['lang'], r['rel'])
        if k in seen:
            continue
        seen.add(k)
        stem_rel[bank_stem(r['rel'])] = (r['lang'], r['rel'])
    stems = sorted(stem_rel.keys(), key=len, reverse=True)

    def rel_of(subsong):
        for s in stems:
            if subsong == s or subsong.startswith(s + '_'):
                return stem_rel[s]
        return None

    fixed = set()
    for s in silent:
        f = s['file']
        fixed.add(f[:-4] if f.lower().endswith('.wav') else f)

    affected = collections.defaultdict(set)
    unmapped = []
    for f in fixed:
        r = rel_of(f)
        if r:
            affected[r].add(f)
        else:
            unmapped.append(f)
    print('affected banks:', len(affected), 'unmapped files:', len(unmapped), flush=True)
    if unmapped:
        print('  unmapped sample:', unmapped[:10], flush=True)

    # 4. rebuild affected banks
    ru_wav = build_wav_map(RU_ROOT)
    fix_wav = build_wav_map(FIX_ROOT)

    jobs = []
    for (lang, rel), fs in sorted(affected.items()):
        fsb_path = os.path.join(WORK, 'out', 'voice_fsb', lang, rel)
        try:
            f = FSB5(open(fsb_path, 'rb').read())
            names = [s.name for s in f.samples]
        except Exception:
            names = sorted(fs)
        entries = [(n, fix_wav.get(n) or ru_wav.get(n)) for n in names]
        jobs.append((lang, rel, entries))

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(os.path.join(WORK, 'tmp_build'), exist_ok=True)

    rows = []
    stats = collections.Counter()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, (lang, rel, out, status) in enumerate(ex.map(build_one, jobs, chunksize=2), 1):
            rows.append([lang, rel, out, status])
            stats[status.split(':')[0]] += 1
            if i % 20 == 0 or i == len(jobs):
                print('progress', i, '/', len(jobs), dict(stats), flush=True)

    shutil.rmtree(os.path.join(WORK, 'tmp_build'), ignore_errors=True)
    with open(os.path.join(OUT_DIR, 'manifest.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['lang', 'rel', 'out_fsb', 'status'])
        w.writerows(rows)
    print('REBUILD DONE', dict(stats), flush=True)


if __name__ == '__main__':
    main()
