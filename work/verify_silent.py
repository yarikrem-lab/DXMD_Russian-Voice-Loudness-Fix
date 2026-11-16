import os, csv, subprocess, re, json

FF = r"D:\opencodeall\work\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
CONV = r"D:\opencodeall\convert"


def peak_db(path):
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path, '-af', 'volumedetect',
                        '-f', 'null', '-'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for line in r.stderr.splitlines():
        m = re.search(r'max_volume:\s*(-?[\d.]+)\s*dB', line)
        if m:
            return float(m.group(1))
    return None


def mean_db(path):
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path, '-af', 'volumedetect',
                        '-f', 'null', '-'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for line in r.stderr.splitlines():
        m = re.search(r'mean_volume:\s*(-?[\d.]+)\s*dB', line)
        if m:
            return float(m.group(1))
    return None


rows = [r for r in csv.DictReader(open(os.path.join(CONV, 'fix', 'report_silent_fixed.csv'),
                                          encoding='utf-8-sig'), delimiter=';')
        if r['status'] == 'normalized']
print('measuring %d normalized files' % len(rows), flush=True)

out = []
for i, r in enumerate(rows, 1):
    code = r['code']
    fname = r['file']
    en_path = os.path.join(CONV, 'en', code, fname)
    fix_path = os.path.join(CONV, 'fix', code, fname)
    en_peak = peak_db(en_path) if os.path.exists(en_path) else None
    en_mean = mean_db(en_path) if os.path.exists(en_path) else None
    fix_peak = peak_db(fix_path) if os.path.exists(fix_path) else None
    fix_mean = mean_db(fix_path) if os.path.exists(fix_path) else None
    dpeak = (fix_peak - en_peak) if (fix_peak is not None and en_peak is not None) else None
    dmean = (fix_mean - en_mean) if (fix_mean is not None and en_mean is not None) else None
    out.append({'file': fname, 'code': code, 'gain': float(r['gain_db']),
                'en_peak': en_peak, 'fix_peak': fix_peak, 'dpeak': dpeak,
                'en_mean': en_mean, 'fix_mean': fix_mean, 'dmean': dmean})
    if i % 30 == 0:
        print('progress', i, '/', len(rows), flush=True)

json.dump(out, open(os.path.join(CONV, 'fix', 'silent_verify.json'), 'w'), indent=2)

# summary
dps = [o['dpeak'] for o in out if o['dpeak'] is not None]
dms = [o['dmean'] for o in out if o['dmean'] is not None]
print('=== peak diff (fix - EN) ===', flush=True)
if dps:
    import statistics
    print('count', len(dps), 'mean %.2f' % statistics.mean(dps), 'median %.2f' % statistics.median(dps),
          'min %.1f max %.1f' % (min(dps), max(dps)), flush=True)
    too_quiet = [o for o in out if o['dpeak'] is not None and o['dpeak'] < -3.0]
    too_loud = [o for o in out if o['dpeak'] is not None and o['dpeak'] > 3.0]
    print('RU_fix too quiet (peak < EN-3dB):', len(too_quiet), flush=True)
    print('RU_fix too loud (peak > EN+3dB):', len(too_loud), flush=True)
    print('--- worst too-quiet (by peak):', flush=True)
    for o in sorted(too_quiet, key=lambda x: x['dpeak'])[:15]:
        print('  %+6.1f dB (en_peak %.1f -> fix_peak %.1f)  %s [%s]' % (
            o['dpeak'], o['en_peak'], o['fix_peak'], o['file'], o['code']), flush=True)
print('=== mean diff (fix - EN) ===', flush=True)
if dms:
    import statistics
    print('count', len(dms), 'mean %.2f' % statistics.mean(dms), 'median %.2f' % statistics.median(dms),
          'min %.1f max %.1f' % (min(dms), max(dms)), flush=True)
print('DONE', flush=True)
