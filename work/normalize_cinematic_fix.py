import os, subprocess, re, json, csv

FF = r"D:\opencodeall\work\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
CIN = r"D:\opencodeall\cinematics"
RU = os.path.join(CIN, 'ru')
FIX = os.path.join(CIN, 'fix')

data = json.load(open(r"D:\opencodeall\work\cinematic_loudness.json"))
rows = data['rows']


def measure(path):
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path, '-map', '0:a:0',
                        '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    I = TP = None
    for line in r.stderr.splitlines():
        m = re.search(r'I:\s*(-?[\d.]+)\s*LUFS', line)
        if m:
            I = float(m.group(1))
        m = re.search(r'Peak:\s*(-?[\d.]+)\s*dBFS', line)
        if m:
            TP = float(m.group(1))
    return I, TP


targets = [r for r in rows if r['diff'] is not None and abs(r['diff']) >= 3.0]
targets.sort(key=lambda x: abs(x['diff']), reverse=True)
print("normalizing %d files" % len(targets), flush=True)

log = []
for r in targets:
    rel = r['rel']
    gain = round(r['en_lufs'] - r['ru_lufs'], 2)
    src = os.path.join(RU, rel)
    dst = os.path.join(FIX, rel)
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    filt = "volume=%.2fdB,alimiter=limit=-1dB:level=false" % gain
    rr = subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', src,
                         '-af', filt, '-c:a', 'pcm_s16le', dst],
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    ok = (rr.returncode == 0) and os.path.exists(dst)
    outI = outTP = None
    if ok:
        outI, outTP = measure(dst)
    status = 'ok' if ok else 'error'
    name = rel.replace('\\', '/').split('/')[-1]
    log.append({'file': name, 'rel': rel, 'en_lufs': r['en_lufs'], 'ru_lufs': r['ru_lufs'],
                'diff': r['diff'], 'gain_db': gain, 'out_lufs': outI, 'out_tp': outTP,
                'status': status})
    print("%-30s gain %+6.2f  ru %6.1f -> out %6.1f (target %6.1f)  tp %5.1f  %s" % (
        name, gain, r['ru_lufs'], outI if outI is not None else float('nan'),
        r['en_lufs'], outTP if outTP is not None else float('nan'), status), flush=True)

# log.csv
with open(os.path.join(FIX, 'log.csv'), 'w', newline='') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['file', 'rel', 'en_lufs', 'ru_lufs', 'diff_db', 'gain_db', 'out_lufs', 'out_tp', 'status'])
    for row in log:
        w.writerow([row['file'], row['rel'], row['en_lufs'], row['ru_lufs'], row['diff'],
                    row['gain_db'], row['out_lufs'], row['out_tp'], row['status']])

print("DONE", flush=True)
