import os, json, shutil

WORK = r"D:\opencodeall\work"
MOD = r"D:\opencodeall\mod_deusex_ru_voice"

patches = json.load(open(os.path.join(WORK, 'mod_patches.json'), encoding='utf-8'))
fsb_names = sorted(set(p['new_fsb'] for p in patches))
print('unique fsb files:', len(fsb_names), flush=True)

fsb_dir = os.path.join(MOD, 'fsb')
os.makedirs(fsb_dir, exist_ok=True)
src_dir = os.path.join(WORK, 'rebuilt_banks')

copied = 0
missing = 0
for i, name in enumerate(fsb_names, 1):
    src = os.path.join(src_dir, name)
    dst = os.path.join(fsb_dir, name)
    if os.path.exists(src):
        if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(src):
            shutil.copyfile(src, dst)
        copied += 1
    else:
        missing += 1
    if i % 2000 == 0:
        print('progress', i, '/', len(fsb_names), flush=True)

# copy patches.json
shutil.copyfile(os.path.join(WORK, 'mod_patches.json'), os.path.join(MOD, 'patches.json'))

print('copied', copied, 'missing', missing, flush=True)
total = sum(os.path.getsize(os.path.join(fsb_dir, n)) for n in fsb_names if os.path.exists(os.path.join(fsb_dir, n)))
print('fsb total size: %.1f MB' % (total / 1024 / 1024), flush=True)
print('DONE', flush=True)
