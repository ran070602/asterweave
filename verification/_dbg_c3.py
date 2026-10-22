# -*- coding: utf-8 -*-
"""调试 C 部分第 3 关为何 0 解：检查真值行模式是否在候选集中、列线索/数字是否通过。"""
import json
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cuni", ROOT / "verification" / "c_uniqueness.py")
cuni = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cuni)

lv = json.loads((ROOT / "tools" / "levels.json").read_text(encoding="utf-8"))[2]
ctx = cuni.Ctx(lv)
n = ctx.n
print("revealed:", sorted((i // n + 1, i % n + 1) for i in ctx.revealed))
tm = ctx.true_mines
true_pat = [tuple(1 if (r * n + c) in tm else 0 for c in range(n)) for r in range(n)]
print("真值行模式:")
for r, p in enumerate(true_pat):
    inopts = p in ctx.row_opts[r]
    print("  行%d %s 在候选中=%s (候选数=%d)  rowRuns=%s 重算=%s" % (
        r + 1, "".join(str(x) for x in p), inopts, len(ctx.row_opts[r]),
        lv["rowRuns"][r], cuni.runs_of(p)))
print("真值列线索重算:", [cuni.runs_of([true_pat[r][c] for r in range(n)]) for c in range(n)])
print("声明列线索    :", lv["colRuns"])
print("真值总雷数:", sum(sum(p) for p in true_pat), "声明:", ctx.declared_total)
print("真值可见数字校验:")
bad = []
for i in ctx.revealed:
    m = sum(1 for j in ctx.nbrs[i] if j in tm)
    if m != ctx.counts[i]:
        bad.append((i // n + 1, i % n + 1, ctx.counts[i], m))
print("  违反:", bad if bad else "无")

# 手工重放 col_prune 逻辑，看真值在哪一步被拒
col_runs = [list(x) for x in lv["colRuns"]]
comp = [tuple() for _ in range(n)]
cur = [0] * n
for r in range(n):
    for c in range(n):
        if true_pat[r][c]:
            cur[c] += 1
        elif cur[c] > 0:
            comp[c] = comp[c] + (cur[c],)
            cur[c] = 0
    remaining = n - 1 - r
    for c in range(n):
        prob = []
        if len(comp[c]) > len(col_runs[c]) or comp[c] != tuple(col_runs[c][:len(comp[c])]):
            prob.append("前缀不符")
        if cur[c] > 0:
            if len(comp[c]) >= len(col_runs[c]) or cur[c] > col_runs[c][len(comp[c])]:
                prob.append("当前块超出")
        runs_left = col_runs[c][len(comp[c]):]
        if cur[c] > 0:
            rem = list(runs_left)
            if rem:
                rem[0] -= cur[c]
                need = sum(rem) + (len(rem) - 1 if rem else 0)
            else:
                need = 0
        else:
            need = (sum(runs_left) + len(runs_left) - 1) if runs_left else 0
        if need > remaining:
            prob.append("容量不足 need=%d remaining=%d" % (need, remaining))
        if prob:
            print("  行%d 处理后 列%d: comp=%s cur=%d runs_left=%s -> %s" % (
                r + 1, c + 1, comp[c], cur[c], runs_left, prob))