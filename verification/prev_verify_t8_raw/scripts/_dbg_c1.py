# -*- coding: utf-8 -*-
"""调试：检查 C 部分给出的"解"是否真的满足开局可见数字。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
lv = json.loads((ROOT / "tools" / "levels.json").read_text(encoding="utf-8"))[0]
n = lv["size"]
total = n * n
tm = {r * n + c for r, c in lv["mines"]}
nbrs = []
for r in range(n):
    for c in range(n):
        nbrs.append([(r + dr) * n + (c + dc)
                     for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                     if not (dr == 0 and dc == 0) and 0 <= r + dr < n and 0 <= c + dc < n])
counts = [sum(1 for j in nbrs[i] if j in tm) for i in range(total)]
op = lv["opening"]
rev = set()
st = [op[0] * n + op[1]]
while st:
    i = st.pop()
    if i in rev:
        continue
    rev.add(i)
    if counts[i] == 0:
        for j in nbrs[i]:
            if j not in rev:
                st.append(j)
print("revealed(%d):" % len(rev), sorted((i // n + 1, i % n + 1) for i in rev))
print("numbers on revealed:", sorted((i // n + 1, i % n + 1, counts[i]) for i in rev))

sols = json.loads((ROOT / "verification" / "out_c.json").read_text(encoding="utf-8"))
samples = sols["levels"][0]["full"]["sols_sample"]
print("样本解数 =", len(samples))
for k, sol in enumerate(samples):
    mines = {r * n + c for r, rowstr in enumerate(sol) for c, ch in enumerate(rowstr) if ch == "X"}
    bad = []
    for i in rev:
        m = sum(1 for j in nbrs[i] if j in mines)
        if m != counts[i]:
            bad.append((i // n + 1, i % n + 1, counts[i], m))
    print("解%d 雷数=%d 违反可见数字的格=%s" % (k + 1, len(mines), bad if bad else "无（满足所有可见数字）"))
    print("    与真值差异格:", sorted((i // n + 1, i % n + 1) for i in mines ^ tm))