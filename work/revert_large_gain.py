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
FIX_LOG = os.path.join(FIX_ROOT, 'log.csv')
OUT_DIR = os.path.join(WORK, 'rebuilt_banks')
QUALITY = 15
THRESHOLD = 20.0  # revert files with |gain| >= this


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
    # 1. files to revert: |gain| >= THRESHOLD
    targets = []
    for r in csv.DictReader(open(FIX_LOG, encoding='utf-8-sig'), delimiter=';'):
        if r.get('status') != 'normalized':
            continue
        try:
            g = float(r['gain_db'])
        except Exception:
            continue
        if abs(g) >= THRESHOLD:
            f = r['file']
            targets.append((f[:-4] if f.lower().endswith('.wav') else f, f))
    print('files to revert (|gain|>=%.0f):' % THRESHOLD, len(targets), flush=True)

    # 2. overwrite fix WAVs with original RU (via recursive stem map)
    ru_wav = build_wav_map(RU_ROOT)
    reverted = 0
    no_ru = []
    for stem, fname in targets:
        src = ru_wav.get(stem)
        if src is None:
            no_ru.append(fname)
            continue
        # find fix WAV path (search recursively for the stem)
        dst = None
        for r, d, fs in os.walk(FIX_ROOT):
            if fname in fs:
                dst = os.path.join(r, fname)
                break
        if dst is None:
            continue
        shutil.copyfile(src, dst)
        reverted += 1
    print('reverted fix WAVs:', reverted, 'no RU original:', len(no_ru), flush=True)
    if no_ru:
        print('  no RU:', no_ru[:15], flush=True)

    # 3. map to banks
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

    affected = collections.defaultdict(set)
    for stem, fname in targets:
        r = rel_of(stem)
        if r:
            affected[r].add(stem)
    print('affected banks:', len(affected), flush=True)

    # 4. rebuild
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
            if i % 50 == 0 or i == len(jobs):
                print('progress', i, '/', len(jobs), dict(stats), flush=True)

    shutil.rmtree(os.path.join(WORK, 'tmp_build'), ignore_errors=True)
    with open(os.path.join(OUT_DIR, 'manifest.csv'), 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';')
        w.writerow(['lang', 'rel', 'out_fsb', 'status'])
        w.writerows(rows)
    print('REBUILD DONE', dict(stats), flush=True)


if __name__ == '__main__':
    main()
