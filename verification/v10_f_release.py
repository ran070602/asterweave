# -*- coding: utf-8 -*-
"""v10 独立复核 F：发布包 / manifest / 离线自包含。"""
import json, os, re, hashlib, zipfile

ROOT = r'D:\Asterweave'
DIST = os.path.join(ROOT, 'dist', '星织-游戏本体', 'index.html')
ZIP = os.path.join(ROOT, '星织-游戏本体.zip')
MAN = os.path.join(ROOT, 'dist', 'build_manifest.json')

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

out = {}
out['html_sha256'] = sha(DIST)
out['html_bytes'] = os.path.getsize(DIST)
out['zip_sha256'] = sha(ZIP)
out['zip_bytes'] = os.path.getsize(ZIP)

raw = open(MAN, 'rb').read()
for enc in ('utf-8', 'gbk'):
    try:
        man = json.loads(raw.decode(enc)); out['manifest_encoding'] = enc; break
    except Exception:
        continue
out['manifest'] = man
out['manifest_fields_match'] = {
    'levels_sha256': man.get('levels_sha256') == sha(os.path.join(ROOT, 'tools', 'levels.json')),
    'build_sha256': man.get('build_sha256') == out['html_sha256'],
    'html_bytes': man.get('html_bytes') == out['html_bytes'],
    'zip_sha256': man.get('zip_sha256') == out['zip_sha256'],
    'zip_bytes': man.get('zip_bytes') == out['zip_bytes'],
    'level_count': man.get('level_count') == 20,
}

with zipfile.ZipFile(ZIP) as z:
    infos = z.infolist()
    out['zip_entries'] = [i.filename for i in infos]
    out['zip_root_index'] = 'index.html' in out['zip_entries']
    zi = z.getinfo('index.html')
    data = z.read('index.html')
    out['zip_index_bytes'] = zi.file_size
    out['zip_index_sha256'] = hashlib.sha256(data).hexdigest()
    out['zip_index_equals_dist'] = (data == open(DIST, 'rb').read())

html = open(DIST, encoding='utf-8').read()
out['external_refs'] = {
    'http(s)://': len(re.findall(r'https?://', html)),
    'fetch(': len(re.findall(r'fetch\(', html)),
    'XMLHttpRequest': len(re.findall(r'XMLHttpRequest', html)),
    'WebSocket': len(re.findall(r'WebSocket', html)),
    '<link': len(re.findall(r'<link', html)),
    '<img': len(re.findall(r'<img', html)),
    'import(': len(re.findall(r'import\(', html)),
}
out['script_src'] = len(re.findall(r'<script[^>]*\bsrc\s*=', html))
out['title'] = re.search(r'<title>(.*?)</title>', html, re.S).group(1)
out['title_claims_10'] = '10 关' in out['title']

json.dump(out, open(os.path.join(ROOT, 'verification', 'v10_out_f.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1, default=str)

print('F html_sha256', out['html_sha256'], 'bytes', out['html_bytes'])
print('F zip_sha256 ', out['zip_sha256'], 'bytes', out['zip_bytes'])
print('F manifest encoding', out.get('manifest_encoding'))
print('F manifest_fields_match', out['manifest_fields_match'])
print('F zip entries', out['zip_entries'])
print('F zip_root_index', out['zip_root_index'], 'index_bytes', out['zip_index_bytes'],
      'equals_dist', out['zip_index_equals_dist'])
print('F external_refs', out['external_refs'], 'script_src', out['script_src'])
print('F title', out['title'], '| claims 10:', out['title_claims_10'])
print('F manifest build_output raw:', repr(man.get('build_output')), 'zip:', repr(man.get('zip')))