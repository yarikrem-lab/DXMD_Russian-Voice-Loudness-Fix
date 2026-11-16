import os, sys, json, time
sys.path.insert(0, os.path.abspath('..'))
import archive

ROOT = r"D:\Steam\steamapps\common\Deus Ex Mankind Divided"


def listdir_retry(d, retries=10, delay=3):
    for i in range(retries):
        try:
            return os.listdir(d)
        except PermissionError:
            print('  retry listdir %s (%d)' % (d, i + 1), flush=True)
            time.sleep(delay)
    raise PermissionError('cannot listdir %s' % d)


archives = []
for d in [os.path.join(ROOT, 'runtime'), os.path.join(ROOT, 'DLC', 'runtime')]:
    for fn in listdir_retry(d):
        if fn.endswith('.archive'):
            archives.append(os.path.join(d, fn))
out = {}
for p in archives:
    print('parsing', p, flush=True)
    a = archive.ArchiveFile(p)
    out[os.path.basename(p)] = {
        'path': p,
        'files': {name: {'chunks': len(f.chunks), 'size': f.total_size} for name, f in a.files.items()},
    }
    print('  files', len(a.files), flush=True)
json.dump(out, open('archive_index.json', 'w', encoding='utf-8'))
print('done', len(out))
