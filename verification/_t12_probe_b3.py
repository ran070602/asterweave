# -*- coding: utf-8 -*-
"""T12 独立探针：
1) 复核 B3 对第 5 关第 12 步 / 第 7 关第 15 步的判定（在打印顺序下两类规则是否真的推不出）。
2) 对照 tools/report.md 的打印顺序 vs b_solver 自己的合法求解顺序（同一动作集合的两种排列）。
"""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(r"D:\AI-Native casual game")
spec = importlib.util.spec_from_file_location("b_solver", ROOT / "verification" / "b_solver.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

levels = json.loads((ROOT / "tools/levels.json").read_text(encoding="utf-8"))
out_b = json.loads((ROOT / "verification/out_b.json").read_text(encoding="utf-8"))
B = {x["id"]: x for x in out_b["levels"]}
rep_txt = (ROOT / "tools/report.md").read_text(encoding="utf-8")

STEP_RE = re.compile(r"^\s*-\s*(\d+)\.\s*\[(邻域|连续块)\]\s*(判定雷|探开安全格)\s*\((\d+),(\d+)\)\s*$")
SEC_RE = re.compile(r"^###\s*第\s*(\d+)\s*关")


def parse_report():
    cur, secs = None, {}
    for line in rep_txt.splitlines():
        m = SEC_RE.match(line)
        if m:
            cur = int(m.group(1)); secs[cur] = []; continue
        if cur is None:
            continue
        m = STEP_RE.match(line)
        if m:
            secs[cur].append((m.group(2), m.group(3), int(m.group(4)), int(m.group(5))))
    return secs


def forced(p):
    a_safe, a_mine = set(), set()
    for i in range(p.n * p.n):
        if p.state[i] != bs.SAFE:
            continue
        flags, unknown = 0, []
        for j in bs.neighbors(p.n, i):
            if p.state[j] == bs.MINE:
                flags += 1
            elif p.state[j] == bs.UNKNOWN:
                unknown.append(j)
        if not unknown:
            continue
        if p.counts[i] == flags:
            a_safe.update(unknown)
        elif p.counts[i] == flags + len(unknown):
            a_mine.update(unknown)
    b_safe, b_mine = set(), set()
    if p.lv["showRuns"]:
        for is_row in (True, False):
            for k in range(p.n):
                idx = [k * p.n + t for t in range(p.n)] if is_row else [t * p.n + k for t in range(p.n)]
                runs = p.lv["rowRuns"][k] if is_row else p.lv["colRuns"][k]
                known = [None if p.state[i] == bs.UNKNOWN else (1 if p.state[i] == bs.MINE else 0) for i in idx]
                placements, _ = bs.line_placements(p.n, runs, known)
                for t in range(p.n):
                    vals = {pl[t] for pl in placements}
                    if vals == {1}:
                        b_mine.add(idx[t])
                    elif vals == {0}:
                        b_safe.add(idx[t])
    return a_safe, a_mine, b_safe, b_mine


rep = parse_report()
for lid, watch in ((5, 12), (7, 15)):
    lv = levels[lid - 1]
    n = lv["size"]
    mines = {r * n + c for r, c in lv["mines"]}
    counts = [sum(1 for j in bs.neighbors(n, i) if j in mines) for i in range(n * n)]
    p = bs.Player(lv, counts, use_runs=True)
    p.reveal(lv["opening"][0] * n + lv["opening"][1], "opening")
    seq = rep[lid]
    print("=" * 76)
    print("第 %d 关：报告步序共 %d 步；检查第 %d 步" % (lid, len(seq), watch))
    for k, (rule, kind, r, c) in enumerate(seq, 1):
        i = (r - 1) * n + (c - 1)
        a_safe, a_mine, b_safe, b_mine = forced(p)
        if k == watch:
            print("  第 %d 步声明： [%s] %s (%d,%d) → 索引 %d" % (k, rule, kind, r, c, i))
            print("    该步前状态 = %s ；该格在真值里是雷? %s" % (
                "未知" if p.state[i] == bs.UNKNOWN else ("已翻开" if p.state[i] == bs.SAFE else "已知雷"),
                i in mines))
            print("    (a)邻域 强制安全=%d 个，含该格? %s" % (len(a_safe), i in a_safe))
            print("    (b)连续块 强制安全=%d 个，含该格? %s" % (len(b_safe), i in b_safe))
            print("    另一类规则能推出? %s" % (i in (a_safe if rule == "连续块" else b_safe)))
        if kind == "判定雷":
            p.flag_deduced([i], "probe")
        else:
            p.reveal_deduced([i], "probe")
    # 报告顺序 vs b_solver 合法顺序
    sol = [(a["rule"], "mine" if a["kind"] == "mine" else "safe", a["r"] + 1, a["c"] + 1)
           for a in B[lid]["a_plus_b"]["solve_actions"]]
    rep_norm = [("a" if x[0] == "邻域" else "b", "mine" if x[1] == "判定雷" else "safe", x[2], x[3]) for x in seq]
    print("  报告顺序 == b_solver 合法顺序 ? %s" % (rep_norm == sol))
    for k in range(max(len(rep_norm), len(sol))):
        r1 = rep_norm[k] if k < len(rep_norm) else None
        r2 = sol[k] if k < len(sol) else None
        if r1 != r2:
            print("    首个分歧在第 %d 步：报告=%s ｜ b_solver=%s" % (k + 1, r1, r2))
            break