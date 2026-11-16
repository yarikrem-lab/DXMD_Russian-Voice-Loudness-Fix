import os, subprocess, re, json, sys

CIN = r"D:\opencodeall\cinematics"
EN = os.path.join(CIN, 'en')
RU = os.path.join(CIN, 'ru')

# ffmpeg full build (has ebur128); fall back to bink2 build
FF = r"D:\opencodeall\work\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
if not os.path.exists(FF):
    FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"


def measure(path):
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path,
                        '-map', '0:a:0', '-af', 'ebur128=peak=true',
                        '-f', 'null', '-'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    I = LRA = TP = None
    for line in r.stderr.splitlines():
        m = re.search(r'I:\s*(-?[\d.]+)\s*LUFS', line)
        if m:
            I = float(m.group(1))
        m = re.search(r'LRA:\s*([\d.]+)\s*LU', line)
        if m:
            LRA = float(m.group(1))
        m = re.search(r'Peak:\s*(-?[\d.]+)\s*dBFS', line)
        if m:
            TP = float(m.group(1))
    return I, LRA, TP


# build ru -> rel path list
ru_files = []
for root, dirs, files in os.walk(RU):
    for f in files:
        if f.lower().endswith('.wav'):
            ru_files.append(os.path.relpath(os.path.join(root, f), RU))

print("ru files:", len(ru_files), flush=True)

rows = []
no_en = []
for i, rel in enumerate(sorted(ru_files), 1):
    en_path = os.path.join(EN, rel)
    ru_path = os.path.join(RU, rel)
    if not os.path.exists(en_path):
        no_en.append(rel)
        continue
    eI, eL, eT = measure(en_path)
    rI, rL, rT = measure(ru_path)
    rows.append({'rel': rel, 'en_lufs': eI, 'ru_lufs': rI,
                 'en_lra': eL, 'ru_lra': rL, 'en_tp': eT, 'ru_tp': rT,
                 'diff': (rI - eI) if (eI is not None and rI is not None) else None})
    if i % 10 == 0:
        print("progress", i, "/", len(ru_files), flush=True)

json.dump({'rows': rows, 'no_en': no_en}, open(os.path.join(CIN, '..', 'work', 'cinematic_loudness.json'), 'w'), indent=2)

# summary
diffs = [r['diff'] for r in rows if r['diff'] is not None]
print("=== SUMMARY ===", flush=True)
print("pairs measured:", len(rows), " no-en counterpart:", len(no_en), flush=True)
if diffs:
    diffs.sort()
    n = len(diffs)
    import statistics
    mean = statistics.mean(diffs)
    med = statistics.median(diffs)
    ge3 = sum(1 for d in diffs if abs(d) >= 3.0)
    ge1 = sum(1 for d in diffs if abs(d) >= 1.0)
    ru_quieter = sum(1 for d in diffs if d < -3.0)
    ru_louder = sum(1 for d in diffs if d > 3.0)
    print("mean diff (ru-en): %.2f dB" % mean, flush=True)
    print("median diff: %.2f dB" % med, flush=True)
    print("min: %.2f  max: %.2f" % (min(diffs), max(diffs)), flush=True)
    print("|diff|>=3 dB:", ge3, " (ru quieter:", ru_quieter, ", ru louder:", ru_louder, ")", flush=True)
    print("|diff|>=1 dB:", ge1, flush=True)
    # worst offenders
    worst = sorted(rows, key=lambda r: abs(r['diff']) if r['diff'] is not None else 0, reverse=True)[:15]
    print("--- worst 15 ---", flush=True)
    for r in worst:
        print("  %+.2f dB  en=%.1f ru=%.1f  %s" % (r['diff'], r['en_lufs'], r['ru_lufs'], r['rel'].replace('\\','/')), flush=True)
print("DONE", flush=True)
