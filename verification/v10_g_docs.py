# -*- coding: utf-8 -*-
"""v10 独立复核 G：文档对账（关卡表 / 改名 / 文档说 X 实测 Y）"""
import json, os, re

ROOT = r'D:\Asterweave'
LEVELS = json.load(open(os.path.join(ROOT, 'tools', 'levels.json'), encoding='utf-8'))
DOCS = [os.path.join(ROOT, '冉政-设计思路文档.md'), os.path.join(ROOT, '冉政-迭代优化过程文档.md')]
SPEC = os.path.join(ROOT, 'docs', 'SPEC.md')

def num(s):
    m = re.search(r'\d+', s)
    return int(m.group(0)) if m else None

def size_of(s):
    m = re.search(r'(\d+)\s*[×x]\s*(\d+)', s)
    return (int(m.group(1)), int(m.group(2))) if m else None

def tables(text):
    lines = text.splitlines()
    out = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i + 1].strip()):
            header = [c.strip() for c in lines[i].strip().strip('|').split('|')]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith('|'):
                rows.append([c.strip() for c in lines[j].strip().strip('|').split('|')])
                j += 1
            out.append((header, rows, i + 1))
            i = j
        else:
            i += 1
    return out

out = {'docs': {}, 'spec': {}, 'mismatches': []}
for p in DOCS:
    name = os.path.basename(p)
    text = open(p, encoding='utf-8').read()
    d = {'name_ok': ('星织' in text and 'Asterweave' in text and '雷织' not in text),
         'mentions_10': text.count('10 关'), 'mentions_20': text.count('20 关'),
         'tables': [], 'level_table_found': False}
    for header, rows, ln in tables(text):
        if any('星座' in h for h in header) and any('总雷' in h for h in header):
            d['level_table_found'] = True
            idx = {h: k for k, h in enumerate(header)}
            parsed = []
            for r in rows:
                if not r or num(r[0]) is None or not (1 <= num(r[0]) <= 20):
                    continue
                lv = LEVELS[num(r[0]) - 1]
                rec = {
                    'id': num(r[0]),
                    'theme': r[idx.get('星座', 1)] if '星座' in idx else None,
                    'size_raw': r[idx.get('棋盘', idx.get('尺寸', 2))],
                    'stars': num(r[idx['星座星']]) if '星座星' in idx else None,
                    'noise': num(r[idx['杂星']]) if '杂星' in idx else None,
                    'mines': num(r[idx['总雷']]) if '总雷' in idx else None,
                    'digs': num(r[idx.get('探格次数', idx.get('探格', -1))]) if ('探格次数' in idx or '探格' in idx) else None,
                }
                exp_theme = lv['theme']['name']
                exp_size = (lv['size'], lv['size'])
                bad = []
                if rec['theme'] != exp_theme: bad.append('星座 %s≠%s' % (rec['theme'], exp_theme))
                if size_of(rec['size_raw']) != exp_size: bad.append('棋盘 %s≠%dx%d' % (rec['size_raw'], *exp_size))
                if rec['stars'] != len(lv['theme']['stars']): bad.append('星座星 %s≠%s' % (rec['stars'], len(lv['theme']['stars'])))
                if rec['noise'] != len(lv['noise']): bad.append('杂星 %s≠%s' % (rec['noise'], len(lv['noise'])))
                if rec['mines'] != len(lv['mines']): bad.append('总雷 %s≠%s' % (rec['mines'], len(lv['mines'])))
                if bad:
                    out['mismatches'].append({'doc': name, 'line': ln, 'id': rec['id'], 'err': bad})
                rec['ok'] = not bad
                parsed.append(rec)
            d['tables'].append({'line': ln, 'rows': len(parsed), 'all_ok': all(r['ok'] for r in parsed), 'parsed': parsed})
    out['docs'][name] = d

spec = open(SPEC, encoding='utf-8').read()
out['spec'] = {
    'version': (re.search(r'（v[\d.]+）', spec) or [''])[0],
    'mentions_10': spec.count('10 关'),
    'says_l1_3_runs_false': ('第 1–3 关' in spec and 'false' in spec),
    'says_teach_126': ('第 **1、2、6** 关非空' in spec),
    'teach_actual': [lv['id'] for lv in LEVELS if lv.get('teach')],
}

# 关键断言核对
texts = {os.path.basename(p): open(p, encoding='utf-8').read() for p in DOCS}
out['claims'] = {
    'design_l1_3_no_runs': '第 1–3 关**不显示**行列线索' in texts['冉政-设计思路文档.md'],
    'actual_showRuns': [(lv['id'], lv['showRuns']) for lv in LEVELS],
    'design_teach_148': '第 1、4、8 关' in texts['冉政-设计思路文档.md'],
    'iteration_teach_148': '第 1、4、8 关' in texts['冉政-迭代优化过程文档.md'],
    'iteration_16_must_runs': '20 关里有 16 关重新变成' in texts['冉政-迭代优化过程文档.md'],
    'iteration_no_empty_lines': '无空行空列' in texts['冉政-迭代优化过程文档.md'],
    'design_87kb_10levels': '约 87 KB' in texts['冉政-设计思路文档.md'],
}

json.dump(out, open(os.path.join(ROOT, 'verification', 'v10_out_g.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

for name, d in out['docs'].items():
    print('G', name, 'name_ok', d['name_ok'], '10关', d['mentions_10'], '20关', d['mentions_20'])
    for t in d['tables']:
        print('  table@%d rows=%d all_ok=%s' % (t['line'], t['rows'], t['all_ok']))
        for r in t['parsed']:
            if not r['ok']:
                print('   MISMATCH', r)
print('G mismatches', len(out['mismatches']))
for m in out['mismatches']:
    print('  ', m)
print('G spec', out['spec'])
print('G claims', json.dumps(out['claims'], ensure_ascii=False))
print('G PASS(structural tables)', all(t['all_ok'] for d in out['docs'].values() for t in d['tables']) and bool(out['docs']))