# -*- coding: utf-8 -*-
"""v21 复核 B：独立零猜测求解器（邻域计数传播 + 数织行列枚举 + flood fill 到不动点）
   不使用 tools/ 下任何生成器代码。"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LV = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))

def runs_of(vals):
    out, cur = [], 0
    for v in vals:
        if v: cur += 1
        elif cur: out.append(cur); cur = 0
    if cur: out.append(cur)
    return out

def line_placements(n, runs, cons):
    """cons: list of None/0/1；枚举所有满足 runs 与 cons 的 0/1 放置。
       返回 list[tuple]，或 None 表示无解。"""
    res = []
    total = sum(runs) + max(0, len(runs) - 1)
    if total > n: return res
    def rec(i, pos, acc):
        if i == len(runs):
            tail = acc + [0] * (n - pos)
            for k in range(n):
                if cons[k] is not None and tail[k] != cons[k]: return
            res.append(tuple(tail)); return
        r = runs[i]
        gap_after = sum(runs[i + 1:]) + max(0, len(runs) - i - 2)
        last_start = n - gap_after - r
        for s in range(pos, last_start + 1):
            if any(cons[k] == 1 for k in range(pos, s)): break
            if any(cons[k] == 0 for k in range(s, s + r)): continue
            if s + r < n and cons[s + r] == 1: continue
            rec(i + 1, s + r + 1, acc + [0] * (s - pos) + [1] * r + [0])
    rec(0, 0, [])
    return res

def solve(level, use_runs=True, verbose=False):
    n = level["size"]
    mines = {tuple(m) for m in level["mines"]}
    stats = dict(reveal_actions=0, revealed_cells=0, runs_cells=0, nb_cells=0, steps=0, ok=False,
                 safe_order=[], mine_order=[])
    known = {}                    # (r,c) -> 'safe'|'mine'
    revealed = set()
    def cnt(r, c):
        return sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr or dc) and (r + dr, c + dc) in mines)
    def nbrs(r, c):
        return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                if (dr or dc) and 0 <= r + dr < n and 0 <= c + dc < n]
    def flood(r, c):
        """翻开 (r,c)；若为 0 格连锁"""
        stack = [(r, c)]
        act = 0
        while stack:
            p = stack.pop()
            if p in revealed: continue
            revealed.add(p); known[p] = 'safe'
            stats["safe_order"].append(p[0] * n + p[1])
            if cnt(*p) == 0:
                for q in nbrs(*p):
                    if q not in revealed and q not in mines: stack.append(q)
        return 1
    stats["reveal_actions"] += flood(*tuple(level["opening"]))
    guard = 0
    while True:
        guard += 1
        if guard > 5000: return stats, "loop-guard"
        new = {}
        # --- 1) 邻域计数传播 ---
        for (r, c) in list(revealed):
            d = cnt(r, c)
            U = [q for q in nbrs(r, c) if q not in known]
            F = [q for q in nbrs(r, c) if known.get(q) == 'mine']
            if not U: continue
            if d == len(F):
                for q in U: new[q] = 'safe'
            elif d - len(F) == len(U):
                for q in U: new[q] = 'mine'
        nb_new = len(new)
        # --- 2) 数织行列枚举 ---
        runs_new = {}
        if use_runs:
            for axis in (0, 1):
                for i in range(n):
                    cells = [(i, j) for j in range(n)] if axis == 0 else [(j, i) for j in range(n)]
                    runs = (level["rowRuns"][i] if axis == 0 else level["colRuns"][i])
                    runs = [int(v) for v in runs]
                    cons = [None] * n
                    for k, p in enumerate(cells):
                        if known.get(p) == 'mine': cons[k] = 1
                        elif known.get(p) == 'safe': cons[k] = 0
                    if not any(c is None for c in cons): continue
                    ps = line_placements(n, runs, cons)
                    if not ps: return stats, "no-placement axis=%d i=%d" % (axis, i)
                    for k, p in enumerate(cells):
                        vals = {pl[k] for pl in ps}
                        if vals == {1} and known.get(p) is None: runs_new[p] = 'mine'
                        elif vals == {0} and known.get(p) is None: runs_new[p] = 'safe'
        # 合并：邻域优先（两者冲突即数据/逻辑矛盾）
        for p, v in runs_new.items():
            if p in new and new[p] != v: return stats, "conflict at %s" % (p,)
            new.setdefault(p, v)
        if not new: break
        for p, v in new.items():
            if known.get(p) is not None: continue
            known[p] = v
            if v == 'mine': stats["mine_order"].append(p[0] * n + p[1])
            if v == 'safe':
                stats["reveal_actions"] += flood(*p)
        stats["steps"] += 1
    stats["revealed_cells"] = len(revealed)
    safe_total = n * n - len(mines)
    stats["unknown"] = n * n - len(known)
    stats["mines_deduced"] = sum(1 for v in known.values() if v == 'mine')
    stats["ok"] = (len(revealed) == safe_total) and all(p in known for p in mines)
    return stats, None

def metrics(level):
    n = level["size"]; mines = {tuple(m) for m in level["mines"]}
    zeros = sum(1 for r in range(n) for c in range(n)
                if (r, c) not in mines and sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                    if (dr or dc) and (r + dr, c + dc) in mines) == 0)
    iso = 0
    for (r, c) in mines:
        if not any((r + dr, c + dc) in mines for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc): iso += 1
    er = sum(1 for r in range(n) if not any((r, c) in mines for c in range(n)))
    ec = sum(1 for c in range(n) if not any((r, c) in mines for r in range(n)))
    return dict(size=n, mines=len(mines), density=len(mines) / (n * n),
                zeros=zeros, zero_ratio=zeros / (n * n), iso=iso, empty_rows=er, empty_cols=ec)

rows = []
bad = []
for x in LV:
    st, err = solve(x, use_runs=bool(x["showRuns"]))
    m = metrics(x)
    rows.append((x["id"], x["theme"]["name"], m, st, err))
    if err or not st["ok"]:
        bad.append((x["id"], x["theme"]["name"], err, st.get("revealed_cells"), st.get("unknown")))

# 第 1 关额外：仅邻域（禁用行列枚举）也必须可解
st1, err1 = solve(LV[0], use_runs=False)

print("%-3s %-10s %-6s %-6s %-7s %-6s %-6s %-6s %-6s %-6s %-6s %-5s %s" % (
    "关", "星座", "尺寸", "雷", "雷密%", "0格%", "孤立", "空行", "空列", "探格", "步", "可解", "备"))
print("-" * 118)
for lid, name, m, st, err in rows:
    print("%-3d %-10s %-6s %-6d %-7.1f %-6.1f %-6d %-6d %-6d %-6d %-6d %-5s %s" % (
        lid, name, "%dx%d" % (m["size"], m["size"]), m["mines"], m["density"] * 100,
        m["zero_ratio"] * 100, m["iso"], m["empty_rows"], m["empty_cols"],
        st["reveal_actions"], st["steps"], "OK" if st["ok"] and not err else "NO",
        err or ("elim=%d" % st["unknown"] if st["unknown"] else "")))
print("-" * 118)
print("B 可解 %d/50" % (50 - len(bad)))
for b in bad: print("  ✗ 第 %d 关 %s err=%s revealed=%s unknown=%s" % b)
print("B 第1关 仅邻域推理（禁用行列枚举）：ok=%s err=%s revealed=%d/%d" % (
    st1["ok"], err1, st1["revealed_cells"], LV[0]["size"] ** 2 - len(LV[0]["mines"])))
# 附加：前五关空行空列
f5 = [(r[0], r[2]["empty_rows"], r[2]["empty_cols"]) for r in rows[:5]]
print("B 前五关空行/空列:", f5)
print("B 尺寸<=11:", all(r[2]["size"] <= 11 for r in rows), "max=%d" % max(r[2]["size"] for r in rows))
print("B 展开占比<=38%:", all(r[2]["zero_ratio"] <= 0.38 for r in rows),
      "max=%.1f%%" % (max(r[2]["zero_ratio"] for r in rows) * 100))
print("B 0格占比<=40%:", all((r[2]["zeros"] / (r[2]["size"] ** 2 + 0.0)) <= 0.40 for r in rows))
print("B 孤立雷<=2:", all(r[2]["iso"] <= 2 for r in rows), "max=%d" % max(r[2]["iso"] for r in rows))
print("B_VERDICT", "PASS" if (not bad and st1["ok"] and not err1) else "FAIL")
json.dump([dict(lid=r[0], name=r[1], **r[2], **r[3]) for r in rows],
          open(os.path.join(ROOT, "verification/v21b_out_b.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump([dict(lid=r[0], n=r[2]["size"], safe_order=r[3]["safe_order"], mine_order=r[3]["mine_order"],
                ok=r[3]["ok"]) for r in rows],
          open(os.path.join(ROOT, "verification/v21b_solution.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
