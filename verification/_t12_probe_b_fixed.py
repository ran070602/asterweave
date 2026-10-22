# -*- coding: utf-8 -*-
"""T12：用「修正后的行枚举」重跑 B 部分教学带判定，确认 b_solver 的枚举缺陷
（line_placements 在最后一块之后多跳一格）是否影响 B 的结论。
做法：把 bs.line_placements 运行时替换为干净枚举，其余（Player/apply_a/apply_b/main）不动。
"""
import importlib.util
import io
import json
import contextlib
from pathlib import Path

ROOT = Path(r"D:\AI-Native casual game")
spec = importlib.util.spec_from_file_location("b_solver", ROOT / "verification/b_solver.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)


def runs_of(vals):
    out, cur = [], 0
    for v in vals:
        if v:
            cur += 1
        else:
            if cur:
                out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out


def cleanroom(n, runs, known):
    out = []
    for mask in range(1 << n):
        bits = [(mask >> c) & 1 for c in range(n)]
        if runs_of(bits) != list(runs):
            continue
        if any(known[c] == 1 and not bits[c] for c in range(n)):
            continue
        if any(known[c] == 0 and bits[c] for c in range(n)):
            continue
        out.append(tuple(bits))
    return out, (len(out) == 0)


print("== 修正 line_placements 后重跑 B 部分 ==")
bs.line_placements = cleanroom
# 注意：b_solver.main() 会把结果写到 ROOT/verification/out_b.json。
# 本探针不得覆盖复核证据，故把它的 ROOT 指到 scratch 目录。
SCRATCH = ROOT / "verification" / "_t12_scratch"
(SCRATCH / "verification").mkdir(parents=True, exist_ok=True)
bs.ROOT = SCRATCH
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = bs.main()
txt = buf.getvalue()
for line in txt.splitlines():
    if line.startswith("第 ") and "[教学带" in line or line.startswith("B 部分总判定"):
        print("  " + line)
print("  b_solver.main() 返回码 =", rc)

out_b = json.loads((ROOT / "verification/out_b.json").read_text(encoding="utf-8"))
print()
print("== 与修正前 out_b.json（b_solver 原实现，仍留在磁盘上）的判定对比 ==")
for lv in out_b["levels"]:
    v = lv["verdict"]
    print("  第 %2d 关：a_only能通关=%s  a+b能通关=%s  需要b=%s  (b)贡献格数=%s ｜ 原实现 b步数=%s" % (
        lv["id"], v["a_only_solves"], v["a_plus_b_solves"], v["b_needed"],
        v["b_contribution_cells"], lv["a_plus_b"]["steps_b"]))