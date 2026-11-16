import os, shutil, sys

CIN = r"D:\opencodeall\cinematics"

# current folder name -> track id
FOLDER_TRACK = {
    'en': '0x0', 'ja': '0x1', 'fr': '0x2', 'it': '0x3', 'de': '0x4',
    'es': '0x5', 'ru': '0x6', 'pl': '0x7', 'mx': '0x8', 'pt': '0x9',
    'extra_c': '0xc', 'extra_d': '0xd',
}

# correct track -> language
TRACK_LANG = {
    '0x0': None, '0x1': None, '0x2': None, '0x3': None,  # placeholders
    '0x4': 'en', '0x5': 'fr', '0x6': 'it', '0x7': 'de',
    '0x8': 'es', '0x9': 'ru', '0xc': 'mx', '0xd': 'pt',
}

ph_dir = os.path.join(CIN, '_placeholder')
os.makedirs(ph_dir, exist_ok=True)

# 1. move placeholder folders (tracks 0x0-0x3) out of the way
for folder, tid in FOLDER_TRACK.items():
    if TRACK_LANG[tid] is not None:
        continue  # real language, keep for rename
    src = os.path.join(CIN, folder)
    if not os.path.isdir(src):
        continue
    dst = os.path.join(ph_dir, "track_%s" % tid)
    print("move placeholder %s -> %s" % (folder, dst), flush=True)
    if os.path.exists(dst):
        shutil.rmtree(dst)  # shouldn't happen; safety
    os.rename(src, dst)

# 2. rename real language folders via temp names (collision-free)
pairs = []  # (source, final)
for folder, tid in FOLDER_TRACK.items():
    lang = TRACK_LANG[tid]
    if lang is None:
        continue
    pairs.append((folder, lang))

# phase A: -> temp
for src, dst in pairs:
    tmp = os.path.join(CIN, "__tmp_%s" % dst)
    os.rename(os.path.join(CIN, src), tmp)
    print("stage %s -> __tmp_%s" % (src, dst), flush=True)
# phase B: temp -> final
for src, dst in pairs:
    tmp = os.path.join(CIN, "__tmp_%s" % dst)
    os.rename(tmp, os.path.join(CIN, dst))
    print("stage __tmp_%s -> %s" % (dst, dst), flush=True)

print("RENAME DONE", flush=True)

# 3. report
print("--- final folders ---", flush=True)
for folder in sorted(os.listdir(CIN)):
    p = os.path.join(CIN, folder)
    if os.path.isdir(p):
        n = sum(len(fs) for _, _, fs in os.walk(p))
        print("  %-16s %d files" % (folder, n), flush=True)
