import os, csv, wave, sys

CONV = r"D:\opencodeall\convert"
FIX = os.path.join(CONV, 'fix')
LOG = os.path.join(FIX, 'log.csv')

# normalized files from log
norm = []
for r in csv.DictReader(open(LOG, encoding='utf-8-sig'), delimiter=';'):
    if r.get('status') == 'normalized':
        norm.append(r)
print('normalized files:', len(norm), flush=True)

silent = []
empty = []
missing = []
for i, r in enumerate(norm, 1):
    code = r['code']
    fname = r['file']
    p = os.path.join(FIX, code, fname)
    if not os.path.exists(p):
        missing.append((code, fname))
        continue
    sz = os.path.getsize(p)
    if sz == 0:
        empty.append((code, fname))
        continue
    # check silence: read samples
    try:
        w = wave.open(p, 'rb')
        n = w.getnframes()
        data = w.readframes(n)
        w.close()
        # check if all bytes zero (silence for PCM)
        if data.strip(b'\x00') == b'':
            silent.append((code, fname))
    except Exception as e:
        empty.append((code, fname))
    if i % 5000 == 0:
        print('progress', i, '/', len(norm), 'silent', len(silent), flush=True)

print('=== RESULTS ===', flush=True)
print('silent (all-zero):', len(silent), flush=True)
print('empty/corrupt:', len(empty), flush=True)
print('missing:', len(missing), flush=True)
for code, f in silent[:50]:
    print('  SILENT:', code, f, flush=True)
for code, f in empty[:20]:
    print('  EMPTY:', code, f, flush=True)
for code, f in missing[:20]:
    print('  MISSING:', code, f, flush=True)
