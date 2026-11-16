import os, sys, subprocess, hashlib, re, json

BASE = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"
RUNTIME = os.path.join(BASE, 'runtime')
DLC_RUNTIME = os.path.join(BASE, 'DLC', 'runtime')
RAD = r"D:\opencodeall\work\radtools_full\radvideo64.exe"
FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
FFULL = r"D:\opencodeall\work\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
FIX = r"D:\opencodeall\cinematics\fix"
WORK = r"D:\opencodeall\work"


def binkvid_hash(resource_path):
    base = resource_path.rsplit('.pc_binkvid', 1)[0]
    return hashlib.md5((base + '.').lower().encode()).hexdigest().upper() + '.pc_binkvid'


def fix_rel_to_resource(rel):
    """cinematiques\\10_cutscenes\\...\\m01_515_cut.wav -> [assembly:/.../m01_515_cut.bk2].pc_binkvid"""
    p = rel.replace('\\', '/')
    assert p.endswith('.wav')
    inner = p[:-4] + '.bk2'  # strip .wav, add .bk2
    return '[assembly:/' + inner + '].pc_binkvid'


def find_source(resource_path):
    h = binkvid_hash(resource_path)
    for d in (RUNTIME, DLC_RUNTIME):
        p = os.path.join(d, h)
        if os.path.exists(p):
            return p
    return None


def measure_lufs(path):
    r = subprocess.run([FFULL, '-hide_banner', '-nostats', '-i', path, '-map', '0:a:0',
                        '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for line in r.stderr.splitlines():
        m = re.search(r'I:\s*(-?[\d.]+)\s*LUFS', line)
        if m:
            return float(m.group(1))
    return None


def stream_count(bk2):
    r = subprocess.run([FF, '-hide_banner', '-i', bk2],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    return len(re.findall(r'Stream #0:\d+\[', r.stderr))


# collect fix wavs
fix_wavs = []
for root, dirs, files in os.walk(FIX):
    for f in files:
        if f.lower().endswith('.wav'):
            fix_wavs.append(os.path.relpath(os.path.join(root, f), FIX))

print("fix wavs:", len(fix_wavs), flush=True)

results = []
for i, rel in enumerate(sorted(fix_wavs), 1):
    resource_path = fix_rel_to_resource(rel)
    src = find_source(resource_path)
    if src is None:
        print("[%d/%d] SOURCE NOT FOUND: %s" % (i, len(fix_wavs), rel), flush=True)
        results.append({'rel': rel, 'status': 'no_source'})
        continue

    name = os.path.basename(rel)
    # extract bk2
    data = open(src, 'rb').read()
    bk2 = data[24:]
    tmp_in = os.path.join(WORK, 'cine_in.bk2')
    tmp_out = os.path.join(WORK, 'cine_out.bk2')
    open(tmp_in, 'wb').write(bk2)

    # BinkMix into track 9
    fix_wav = os.path.join(FIX, rel)
    r = subprocess.run([RAD, 'BinkMix', tmp_in, fix_wav, tmp_out, '/T9'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if r.returncode != 0 or not os.path.exists(tmp_out):
        print("[%d/%d] BinkMix FAILED: %s (rc=%d)" % (i, len(fix_wavs), name, r.returncode), flush=True)
        results.append({'rel': rel, 'status': 'binkmix_failed'})
        continue

    new_bk2 = open(tmp_out, 'rb').read()

    # repack .pc_binkvid: KNIB header + new bk2, update size
    knib = bytearray(24)
    knib[0:4] = b'KNIB'
    knib[12:16] = len(new_bk2).to_bytes(4, 'little')
    knib[16:24] = b'\xff' * 8
    out_data = bytes(knib) + new_bk2

    # write next to source (in place, with .bak) - full replacement build
    bak = src + '.bak'
    if not os.path.exists(bak):
        os.rename(src, bak)
    else:
        os.remove(src)
    open(src, 'wb').write(out_data)

    # verify
    sc = stream_count(tmp_out)
    # track 9 is now the last audio stream; find its index
    r2 = subprocess.run([FF, '-hide_banner', '-i', tmp_out],
                        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    tid_lines = [(m.start(), m.group(1)) for m in re.finditer(r'Stream #0:(\d+)\[0x([0-9a-f]+)\]: Audio', r2.stderr)]
    track9_stream = None
    for m in re.finditer(r'Stream #0:(\d+)\[0x9\]: Audio', r2.stderr):
        track9_stream = int(m.group(1))
    out_lufs = None
    if track9_stream is not None:
        vwav = os.path.join(WORK, 'cine_verify.wav')
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp_out,
                        '-map', '0:%d' % track9_stream, '-vn', vwav],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out_lufs = measure_lufs(vwav)

    status = 'ok' if (sc == 13 and track9_stream is not None) else 'verify_fail'
    results.append({'rel': rel, 'status': status, 'streams': sc,
                    'track9_lufs': out_lufs, 'src': os.path.basename(src),
                    'size_orig': len(bk2), 'size_new': len(new_bk2)})
    print("[%d/%d] %-30s %s streams=%d track9=%.1f  %d->%d" % (
        i, len(fix_wavs), name, status, sc,
        out_lufs if out_lufs is not None else -999,
        len(bk2), len(new_bk2)), flush=True)

json.dump(results, open(os.path.join(WORK, 'cine_repack_results.json'), 'w'), indent=2)
print("DONE", flush=True)
