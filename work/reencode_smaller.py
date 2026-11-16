import os, sys, csv, json, collections, re, shutil, subprocess, hashlib
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fsb5'))
from fsb5 import FSB5

FSBANK = r"C:\Program Files (x86)\FMOD SoundSystem\FMOD Studio API Windows\bin\fsbankcl.exe"
WORK = os.path.dirname(os.path.abspath(__file__))
RU_ROOT = r"D:\opencodeall\convert\ru"
FIX_ROOT = r"D:\opencodeall\convert\fix"
OUT_DIR = os.path.join(WORK, 'rebuilt_banks')


def wavmap(root):
    m = {}
    for r, d, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith('.wav'):
                m[f[:-4]] = os.path.join(r, f)
                m.setdefault(re.sub(r'__[0-9a-f]{8}$', '', f[:-4]), os.path.join(r, f))
    return m


def reencode_one(args):
    lang, rel, out, names, entries, q = args
    tmp = os.path.join(WORK, 'tmp_reenc', hashlib.sha1((lang + rel + str(q)).encode()).hexdigest()[:16])
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp, exist_ok=True)
    for n, src in entries:
        if src:
            shutil.copyfile(src, os.path.join(tmp, n + '.wav'))
    p = subprocess.run([FSBANK, '-o', out, '-format', 'vorbis', '-quality', str(q),
                        '-no_loop', '-recursive', tmp],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    shutil.rmtree(tmp, ignore_errors=True)
    if p.returncode != 0 or not os.path.exists(out):
        return (lang, rel, 'error')
    return (lang, rel, 'ok')


def main():
    quality = int(sys.argv[1]) if len(sys.argv) > 1 else 13
    rows = list(csv.reader(open(os.path.join(OUT_DIR, 'manifest.csv'), encoding='utf-8-sig'), delimiter=';'))[1:]
    manifest = json.load(open(os.path.join(WORK, 'out', 'voice_fsb_manifest_all.json'), encoding='utf-8'))
    by_key = {(r['lang'], r['rel']): r for r in manifest}
    ru = wavmap(RU_ROOT)
    fx = wavmap(FIX_ROOT)

    jobs = []
    for lang, rel, out, status in rows:
        if status != 'ok':
            continue
        old = os.path.join(WORK, 'out', 'voice_fsb', lang, rel)
        old_size = os.path.getsize(old)
        if os.path.getsize(out) <= old_size:
            continue
        rec = by_key.get((lang, rel))
        if rec is None:
            continue
        try:
            f = FSB5(open(old, 'rb').read())
            names = [s.name for s in f.samples]
        except Exception:
            continue
        entries = [(n, fx.get(n) or ru.get(n)) for n in names]
        jobs.append((lang, rel, out, names, entries, quality))

    print('to re-encode at q%d:' % quality, len(jobs), flush=True)
    os.makedirs(os.path.join(WORK, 'tmp_reenc'), exist_ok=True)
    stats = collections.Counter()
    with ThreadPoolExecutor(max_workers=6) as ex:
        for i, (lang, rel, status) in enumerate(ex.map(reencode_one, jobs, chunksize=2), 1):
            stats[status] += 1
            if i % 200 == 0:
                print('progress', i, '/', len(jobs), dict(stats), flush=True)
    shutil.rmtree(os.path.join(WORK, 'tmp_reenc'), ignore_errors=True)
    print('DONE', dict(stats), flush=True)

    bigger = 0
    for lang, rel, out, status in rows:
        if status != 'ok':
            continue
        if os.path.getsize(out) > os.path.getsize(os.path.join(WORK, 'out', 'voice_fsb', lang, rel)):
            bigger += 1
    print('still bigger after q%d:' % quality, bigger, flush=True)


if __name__ == '__main__':
    main()
