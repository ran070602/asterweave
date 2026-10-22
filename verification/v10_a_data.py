# -*- coding: utf-8 -*-
"""v10 独立复核：A 数据自洽 + C 难度指标（自写，不 import tools/*）"""
import json, re, sys, os

ROOT = r'D:\Asterweave'
LEVELS = os.path.join(ROOT, 'tools', 'levels.json')
DIST = os.path.join(ROOT, 'dist', '星织-游戏本体', 'index.html')

def load_json(p):
    with open(p, encoding='utf-8') as f:
        return json.load(f)

def nbrs(n, i):
    r, c = divmod(i, n)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n:
                yield rr * n + cc

def cells(mines, n):
    return {r * n + c for r, c in mines}

def runs_line(mine_set, n, k, by_row):
    out, cur = [], 0
    for t in range(n):
        i = k * n + t if by_row else t * n + k
        if i in mine_set:
            cur += 1
        else:
            if cur:
                out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out

def flood(n, mine_set, start, seen):
    stack = [start]
    while stack:
        i = stack.pop()
        if i in seen or i in mine_set:
            continue
        seen.add(i)
        r, c = divmod(i, n)
        cnt = sum(1 for j in nbrs(n, i) if j in mine_set)
        if cnt == 0:
            for j in nbrs(n, i):
                if j not in seen and j not in mine_set:
                    stack.append(j)

levels = load_json(LEVELS)
html = open(DIST, encoding='utf-8').read()

res = {'A': {}, 'C': {}}
a = res['A']
a['level_count'] = len(levels)
a['ids'] = [lv.get('id') for lv in levels]
a['ids_ok'] = a['ids'] == list(range(1, len(levels) + 1))

# --- 内嵌 LEVELS ---
m = re.search(r'/\* LEVELS_INJECT_START \*/\s*const LEVELS = (\[.*?\]);\s*/\* LEVELS_INJECT_END \*/', html, re.S)
a['levels_block_found'] = bool(m)
if m:
    embedded = json.loads(m.group(1))
    a['embedded_count'] = len(embedded)
    a['embedded_equals_json'] = embedded == levels

bad = []
det = []
for idx, lv in enumerate(levels):
    lid, n = lv['id'], lv['size']
    ms, nz = lv.get('mines', []), lv.get('noise', [])
    st = lv.get('theme', {}).get('stars', [])
    mset, nset, sset = cells(ms, n), cells(nz, n), cells([(s['rc'][0], s['rc'][1]) for s in st], n)
    e = []
    if len(ms) != len(mset):
        e.append('mines 重复')
    if any(not (0 <= r < n and 0 <= c < n) for r, c in ms):
        e.append('mines 越界')
    if len(nz) != len(nset):
        e.append('noise 重复')
    if not nset <= mset:
        e.append('noise 不在 mines')
    if nset & sset:
        e.append('noise 与星座星重叠 %s' % sorted(nset & sset))
    if mset != (sset | nset) or len(mset) != len(sset | nset):
        e.append('mines != stars∪noise')
    rr = [runs_line(mset, n, r, True) for r in range(n)]
    cr = [runs_line(mset, n, c, False) for c in range(n)]
    if rr != lv.get('rowRuns'):
        e.append('rowRuns 不一致')
    if cr != lv.get('colRuns'):
        e.append('colRuns 不一致')
    op = lv.get('opening')
    op_ok = bool(op and len(op) >= 2 and 0 <= op[0] < n and 0 <= op[1] < n and (op[0] * n + op[1]) not in mset)
    if op_ok:
        oi = op[0] * n + op[1]
        cnt, zero = sum(1 for j in nbrs(n, oi) if j in mset), 0
        op_ok = cnt == 0
    if not op_ok:
        e.append('opening 非安全 0 格')
    want_show = (idx != 0)
    if bool(lv.get('showRuns')) != want_show:
        e.append('showRuns=%s 期望 %s' % (lv.get('showRuns'), want_show))
    if lv.get('lives') != 3:
        e.append('lives=%s' % lv.get('lives'))
    if e:
        bad.append({'id': lid, 'err': e})
    # C
    safe = n * n - len(mset)
    opened = set()
    if op_ok:
        flood(n, mset, op[0] * n + op[1], opened)
    zeros = sum(1 for i in range(n * n) if i not in mset and
                sum(1 for j in nbrs(n, i) if j in mset) == 0)
    isolated = sum(1 for i in mset if sum(1 for j in nbrs(n, i) if j in mset) == 0)
    det.append({
        'id': lid, 'name': lv.get('name'), 'theme': lv.get('theme', {}).get('name'),
        'n': n, 'stars': len(st), 'noise': len(nz), 'mines': len(mset),
        'open_pct': round(100.0 * len(opened) / (n * n), 2),
        'open_cells': len(opened),
        'zero_pct': round(100.0 * zeros / safe, 2),
        'zeros': zeros, 'safe': safe,
        'isolated': isolated,
        'themes_lines': len(lv.get('theme', {}).get('lines', [])),
        'teach': bool(lv.get('teach')),
    })

a['bad_levels'] = bad
a['pass'] = (a['ids_ok'] and a.get('embedded_equals_json') and not bad)
res['C']['levels'] = det
res['C']['max_open_pct'] = max(d['open_pct'] for d in det)
res['C']['max_zero_pct'] = max(d['zero_pct'] for d in det)
res['C']['max_isolated'] = max(d['isolated'] for d in det)
res['C']['limits'] = {'open': 38, 'zero': 40, 'isolated': 2}
res['C']['fails'] = [d for d in det if d['open_pct'] > 38 or d['zero_pct'] > 40 or d['isolated'] > 2]

json.dump(res, open(os.path.join(ROOT, 'verification', 'v10_out_a.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

print('A level_count', a['level_count'], 'ids_ok', a['ids_ok'])
print('A embedded_count', a.get('embedded_count'), 'embedded_equals_json', a.get('embedded_equals_json'))
print('A bad_levels', json.dumps(bad, ensure_ascii=False))
print('A PASS', a['pass'])
print('C max_open %.2f%% max_zero %.2f%% max_isolated %d' % (res['C']['max_open_pct'], res['C']['max_zero_pct'], res['C']['max_isolated']))
for d in det:
    flag = ' <-- OVER' if (d['open_pct'] > 38 or d['zero_pct'] > 40 or d['isolated'] > 2) else ''
    print('C L%02d %-10s %2dx%-2d open %5.1f%% (%2d) zero %5.1f%% (%2d/%2d) iso %d%s' % (
        d['id'], d['theme'], d['n'], d['n'], d['open_pct'], d['open_cells'],
        d['zero_pct'], d['zeros'], d['safe'], d['isolated'], flag))
print('C fails', [d['id'] for d in res['C']['fails']])