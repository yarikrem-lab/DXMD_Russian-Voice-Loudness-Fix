import os, csv, sys, json
sys.path.insert(0, '.')
sys.path.insert(0, 'fsb5')
from fsb5 import FSB5

OUT = 'rebuilt_banks'
rows = list(csv.reader(open(os.path.join(OUT, 'manifest.csv.fullbak'), encoding='utf-8-sig'), delimiter=';'))[1:]
print('banks:', len(rows), flush=True)

drops = []
missing_rebuilt = 0
for i, (lang, rel, out, status) in enumerate(rows, 1):
    if status != 'ok':
        continue
    orig = os.path.join('out', 'voice_fsb', lang, rel)
    if not os.path.exists(orig) or not os.path.exists(out):
        missing_rebuilt += 1
        continue
    try:
        fo = FSB5(open(orig, 'rb').read())
        fr = FSB5(open(out, 'rb').read())
    except Exception:
        continue
    no = set(s.name for s in fo.samples)
    nr = set(s.name for s in fr.samples)
    diff = no - nr
    if diff:
        drops.append((rel, sorted(diff)))
    if i % 3000 == 0:
        print('progress', i, '/', len(rows), 'drops', len(drops), flush=True)

print('=== RESULT ===', flush=True)
print('banks with dropped subsongs:', len(drops), 'missing files:', missing_rebuilt, flush=True)
for rel, diff in drops[:30]:
    print('  DROP:', rel, '->', diff, flush=True)
print('DONE', flush=True)
