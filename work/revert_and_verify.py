import os, subprocess, re, json

BASE = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"
RUNTIME = os.path.join(BASE, 'runtime')
DLC = os.path.join(BASE, 'DLC', 'runtime')
FF = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
FFULL = r"D:\opencodeall\work\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
WORK = r"D:\opencodeall\work"

# 1. revert m01_700_cut (its game file hash)
M01_700 = 'E97D72A3B3C4A97B74B2F91DF27E67EB.pc_binkvid'
for d in (RUNTIME, DLC):
    p = os.path.join(d, M01_700)
    bak = p + '.bak'
    if os.path.exists(bak):
        os.remove(p)
        os.rename(bak, p)
        print("REVERTED m01_700_cut:", p, flush=True)
        break

# 2. verify the other 12 files' track 9
results = json.load(open(os.path.join(WORK, 'cine_repack_results.json')))
print("checking %d files (excluding m01_700_cut)" % len([r for r in results if r['rel'].find('m01_700')<0]), flush=True)

def measure_lufs(path):
    r = subprocess.run([FFULL, '-hide_banner', '-nostats', '-i', path, '-map', '0:a:0',
                        '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    for line in r.stderr.splitlines():
        m = re.search(r'I:\s*(-?[\d.]+)\s*LUFS', line)
        if m:
            return float(m.group(1))
    return None

for r in results:
    if 'm01_700' in r['rel']:
        continue
    src = r['src']
    found = None
    for d in (RUNTIME, DLC):
        p = os.path.join(d, src)
        if os.path.exists(p):
            found = p
            break
    if not found:
        print("  %-30s NOT FOUND" % r['rel'], flush=True)
        continue
    data = open(found, 'rb').read()
    bk2 = data[24:]
    size_hdr = int.from_bytes(data[12:16], 'little')
    tmp = os.path.join(WORK, 'vchk.bk2')
    open(tmp, 'wb').write(bk2)
    # find track 0x9 stream index
    rr = subprocess.run([FF, '-hide_banner', '-i', tmp], stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE, text=True)
    t9 = None
    for m in re.finditer(r'Stream #0:(\d+)\[0x9\]: Audio', rr.stderr):
        t9 = int(m.group(1))
    lufs = None
    if t9 is not None:
        vw = os.path.join(WORK, 'vchk.wav')
        subprocess.run([FF, '-hide_banner', '-loglevel', 'error', '-y', '-i', tmp,
                        '-map', '0:%d' % t9, '-vn', vw], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        lufs = measure_lufs(vw)
    name = os.path.basename(r['rel'])
    print("  %-28s knib_ok=%s track9_stream=%s track9=%.1f LUFS  (target EN)" % (
        name, (size_hdr == len(bk2)), t9, lufs if lufs is not None else -999), flush=True)
print("DONE", flush=True)
