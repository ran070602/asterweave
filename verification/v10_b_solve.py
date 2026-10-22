# -*- coding: utf-8 -*-
"""v10 独立复核 B：零猜测可解性。
自写求解器：邻域计数传播 + 数织行列枚举 + flood fill 到不动点。
不 import / 不复制 tools/* 代码。
"""
import json, os, sys

ROOT = r'D:\Asterweave'
LEVELS = json.load(open(os.path.join(ROOT, 'tools', 'levels.json'), encoding='utf-8'))

def nbrs(n, i):
    r, c = divmod(i, n)
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr or dc:
                rr, cc = r + dr, c + dc
                if 0 <= rr < n and 0 <= cc < n:
                    out.append(rr * n + cc)
    return out

def line_cells(n, k, by_row):
    return [k * n + t if by_row else t * n + k for t in range(n)]

def enumerate_line(runs, n, known_mine_mask, known_safe_mask):
    """返回所有与已知格子兼容的布雷方案（行内位掩码列表）。"""
    known_mine, known_safe = known_mine_mask, known_safe_mask
    sols = []
    total_needed = sum(runs)

    def rec(k, pos, mask):
        if k == len(runs):
            if mask & known_safe:
                return
            # 未布点必须全是已知安全/未知（未知允许，后续再推）
            if (known_mine & ~mask):
                return
            sols.append(mask)
            return
        # 剩余块（含间隔）至少要占的空间
        remain = sum(runs[k:]) + (len(runs) - k - 1)
        last_start = n - remain
        L = runs[k]
        for s in range(pos, last_start + 1):
            m = 0
            ok = True
            for t in range(s, s + L):
                m |= 1 << t
            if m & known_safe:
                continue
            # 与前一块之间的间隔（至少 1 格）必须不是已知雷
            if k > 0 and (known_mine >> (s - 1)) & 1:
                continue
            if mask & m:
                continue
            rec(k + 1, s + L + 1, mask | m)

    rec(0, 0, 0)
    return sols

def solve(level, use_runs):
    n = level['size']
    total = n * n
    mine_set = {r * n + c for r, c in level['mines']}
    safe_set = set(range(total)) - mine_set
    cnt = [sum(1 for j in nbrs(n, i) if j in mine_set) for i in range(total)]

    known_mine = set()
    known_safe = set()
    revealed = set()
    clicks = 0

    def flood(i):
        stack = [i]
        while stack:
            x = stack.pop()
            if x in revealed or x in known_mine:
                continue
            revealed.add(x)
            known_safe.add(x)
            if x in mine_set:
                continue
            if cnt[x] == 0:
                for y in nbrs(n, x):
                    if y not in revealed and y not in known_mine:
                        stack.append(y)

    # 开局：opening 是 0 格，直接连锁展开（不计探格）
    op = level['opening']
    flood(op[0] * n + op[1])

    def add_safe(s):
        new = s - known_safe - known_mine
        known_safe.update(new)
        return new

    def add_mine(s):
        new = s - known_mine - known_safe
        known_mine.update(new)
        return new

    rounds = 0
    while True:
        rounds += 1
        if rounds > 500:
            raise RuntimeError('no convergence')
        before = (len(known_safe), len(known_mine), len(revealed))

        # 1) 邻域计数传播
        for i in revealed:
            unknown = [j for j in nbrs(n, i) if j not in known_mine and j not in known_safe]
            need = cnt[i] - sum(1 for j in nbrs(n, i) if j in known_mine)
            if need < 0 or need > len(unknown):
                raise RuntimeError('contradiction at %d' % i)
            if need == 0 and unknown:
                add_safe(set(unknown))
            elif need == len(unknown) and unknown:
                add_mine(set(unknown))

        # 2) 数织行列约束枚举（第 1 关 showRuns=false，此步为空）
        if use_runs and level.get('showRuns'):
            for by_row in (True, False):
                for k in range(n):
                    idxs = line_cells(n, k, by_row)
                    runs = level['rowRuns'][k] if by_row else level['colRuns'][k]
                    if not runs:
                        # 空行/列：整条都是安全格
                        add_safe(set(idxs) - known_mine)
                        continue
                    sols = enumerate_line(
                        runs, n,
                        sum(1 << t for t in range(n) if idxs[t] in known_mine),
                        sum(1 << t for t in range(n) if idxs[t] in known_safe))
                    if not sols:
                        raise RuntimeError('line %s%d no solution' % ('row' if by_row else 'col', k))
                    common_m = None
                    common_s = None
                    for m in sols:
                        if common_m is None:
                            common_m, common_s = m, ((1 << n) - 1) ^ m
                        else:
                            common_m &= m
                            common_s &= ((1 << n) - 1) ^ m
                    add_mine({idxs[t] for t in range(n) if (common_m >> t) & 1})
                    add_safe({idxs[t] for t in range(n) if (common_s >> t) & 1})

        # 3) 翻开所有已判定安全但未翻开的格（点击；0 格连锁）
        newly = [i for i in known_safe if i not in revealed and i in safe_set]
        # 先点 0 格以触发最大连锁，再点其余
        newly.sort(key=lambda i: (cnt[i] != 0, i))
        for i in newly:
            if i in revealed:
                continue
            clicks += 1
            flood(i)

        after = (len(known_safe), len(known_mine), len(revealed))
        if after == before:
            break

    solved = safe_set <= revealed
    return {
        'id': level['id'], 'theme': level['theme']['name'], 'n': n,
        'safe': len(safe_set), 'mines': len(mine_set),
        'revealed': len(revealed & safe_set),
        'mines_deduced': len(known_mine),
        'solved': solved, 'clicks': clicks, 'rounds': rounds,
    }

out = {'levels': [], 'pass': True}
for lv in LEVELS:
    r = solve(lv, use_runs=True)
    out['levels'].append(r)
    out['pass'] = out['pass'] and r['solved']
    print('B L%02d %-8s %2dx%-2d safe %2d revealed %2d mines %2d deduced %2d clicks %2d %s' % (
        r['id'], r['theme'], r['n'], r['n'], r['safe'], r['revealed'],
        r['mines'], r['mines_deduced'], r['clicks'], 'OK' if r['solved'] else 'STUCK'))

# 第 1 关只用邻域推理
l1 = solve(LEVELS[0], use_runs=False)
out['level1_neighborhood_only'] = l1['solved']
print('B level1 neighborhood-only :', l1['solved'], 'clicks', l1['clicks'])

json.dump(out, open(os.path.join(ROOT, 'verification', 'v10_out_b.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('B PASS', out['pass'], '| L1 neighborhood-only', out['level1_neighborhood_only'])