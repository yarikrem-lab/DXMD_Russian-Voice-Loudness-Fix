import os, sys, json, hashlib, subprocess, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datautils'))
import structs

BASE = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"
RUNTIME = os.path.join(BASE, 'runtime')
DLC_RUNTIME = os.path.join(BASE, 'DLC', 'runtime')
FFMPEG = r"D:\opencodeall\work\ffmpeg-bink2\ffmpeg-bink2\ffmpeg.exe"
OUT = r"D:\opencodeall\cinematics"
WORK = os.path.dirname(os.path.abspath(__file__))

HLIB = structs.HLIB.compile()
HLIBInner = structs.HLIBInner

# track ID (hex) -> language code
TRACK_LANGS = {
    '0': 'en', '1': 'ja', '2': 'fr', '3': 'it', '4': 'de',
    '5': 'es', '6': 'ru', '7': 'pl', '8': 'mx', '9': 'pt',
    'c': 'extra_c', 'd': 'extra_d',
}


def binkvid_filename(path):
    base = path.rsplit('.pc_binkvid', 1)[0]
    return hashlib.md5((base + '.').lower().encode()).hexdigest().upper() + '.pc_binkvid'


def scene_rel(path):
    """[assembly:/a/b/scene/scene.bk2].pc_binkvid -> (a/b/scene, scene)"""
    m = re.match(r'^\[assembly:(.*?)\]\.(.*)$', path, re.I)
    inner = m.group(1).lstrip('/')  # /a/b/scene/scene.bk2
    folder = os.path.dirname(inner)
    scene = os.path.basename(inner)[:-4] if os.path.basename(inner).endswith('.bk2') else os.path.basename(inner)
    folder = folder.replace('?/', '/')
    for ch in ':*?"<>|':
        folder = folder.replace(ch, '_')
    return folder, scene


def find_tracks(bk2):
    p = subprocess.run([FFMPEG, '-hide_banner', '-i', bk2],
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    out = {}
    for line in p.stderr.splitlines():
        m = re.match(r'\s*Stream #0:(\d+)\[0x([0-9a-fA-F]+)\]: Audio:', line)
        if m:
            out[m.group(2).lower()] = int(m.group(1)) - 1
    return out


def main():
    path_to_hash = {}
    for d in (RUNTIME, DLC_RUNTIME):
        for fn in os.listdir(d):
            if not fn.endswith('.pc_headerlib'):
                continue
            try:
                hlib = HLIB.parse_file(os.path.join(d, fn))
                hi = HLIBInner.parse(hlib.bin1.inner)
                for s in hi.external_resources.arr:
                    if '.pc_binkvid' in s.string:
                        path_to_hash[s.string] = binkvid_filename(s.string)
            except Exception:
                pass
    print('binkvid paths:', len(path_to_hash), flush=True)
    hash_to_path = {v.upper(): k for k, v in path_to_hash.items()}

    files = []
    for d in (RUNTIME, DLC_RUNTIME):
        for fn in os.listdir(d):
            if fn.endswith('.pc_binkvid'):
                files.append((os.path.join(d, fn), fn))
    print('binkvid files:', len(files), flush=True)

    os.makedirs(OUT, exist_ok=True)
    done = noaudio = errors = 0
    lang_counts = {}
    for i, (fp, fn) in enumerate(sorted(files), 1):
        path = hash_to_path.get(fn.upper())
        if path is None:
            continue
        data = open(fp, 'rb').read()
        bk2 = data[24:]
        if not bk2.startswith(b'KB2'):
            continue
        tmpbk = os.path.join(WORK, 'tmp_movie.bk2')
        open(tmpbk, 'wb').write(bk2)
        tracks = find_tracks(tmpbk)
        if not tracks:
            noaudio += 1
            os.remove(tmpbk)
            continue
        folder, scene = scene_rel(path)
        for tid, lang in TRACK_LANGS.items():
            if tid not in tracks:
                continue
            outdir = os.path.join(OUT, lang, folder)
            os.makedirs(outdir, exist_ok=True)
            outwav = os.path.join(outdir, scene + '.wav')
            r = subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', tmpbk,
                                '-map', '0:a:%d' % tracks[tid], '-vn', outwav],
                               stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            if r.returncode == 0 and os.path.exists(outwav):
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
            else:
                errors += 1
        os.remove(tmpbk)
        done += 1
        if i % 25 == 0:
            print('progress', i, '/', len(files), 'done', done, 'noaudio', noaudio, flush=True)
    print('DONE done', done, 'noaudio', noaudio, 'errors', errors, flush=True)
    print('per-language files:', dict(sorted(lang_counts.items())), flush=True)


if __name__ == '__main__':
    main()
