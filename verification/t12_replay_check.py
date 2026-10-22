# -*- coding: utf-8 -*-
"""T12 第二轮更正性诊断：报告推理序列到底能不能逐步复现？

背景：b3_replay_report.py 报「第 5 关第 16 步、第 7 关第 15 步两类规则都推不出」。
本脚本用**干净实现**（暴力枚举全部 2^n 个子集，按 runs 与已知雷/安全格过滤）替代
b_solver.line_placements，重放 tools/report.md 的全部打印序列，并顺带在重放过程中
把「同一状态、同一行/列」交给三套枚举器比对：

  A. cleanroom  ：本脚本的暴力枚举（显然正确、与生成器/复核器都无代码关系）
  B. generator  ：tools/generate_levels.line_patterns（**仅用于诊断对照**）
  C. reviewer   ：verification/b_solver.line_placements（前一版复核实现）

输出：逐关重放结论 + 三个枚举器在全流程中的不一致次数与首个反例。
"""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(r"D:\AI-Native casual game")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


bs = load("b_solver", ROOT / "verification/b_solver.py")
gen = load("generate_levels", ROOT / "tools/generate_levels.py")

UNK, SAFE, MINE = 0, 1, 2


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


def cleanroom_patterns(n, runs, known):
    """known: [None | 0 安全 | 1 雷]；返回 {frozenset(雷位)}。暴力枚举，无剪枝。"""
    out = set()
    for mask in range(1 << n):
        bits = [(mask >> c) & 1 for c in range(n)]
        if runs_of(bits) != list(runs):
            continue
        ok = True
        for c in range(n):
            if known[c] == 1 and not bits[c]:
                ok = False; break
            if known[c] == 0 and bits[c]:
                ok = False; break
        if ok:
            out.add(frozenset(c for c in range(n) if bits[c]))
    return out


def forced_from_patterns(n, pats):
    if not pats:
        return set(), set()
    mine = set.intersection(*[set(p) for p in pats])
    safe = set.intersection(*[set(range(n)) - set(p) for p in pats])
    return mine, safe


def forced_a(n, state, counts):
    a_safe, a_mine = set(), set()
    for i in range(n * n):
        if state[i] != SAFE:
            continue
        flags, unknown = 0, []
        for j in bs.neighbors(n, i):
            if state[j] == MINE:
                flags += 1
            elif state[j] == UNK:
                unknown.append(j)
        if not unknown:
            continue
        if counts[i] == flags:
            a_safe.update(unknown)
        elif counts[i] == flags + len(unknown):
            a_mine.update(unknown)
    return a_safe, a_mine


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
            secs[cur].append((int(m.group(1)), m.group(2), m.group(3), int(m.group(4)), int(m.group(5))))
    return secs


rep = parse_report()
levels = json.loads((ROOT / "tools/levels.json").read_text(encoding="utf-8"))

mismatch_A_B = []   # cleanroom vs generator
mismatch_A_C = []   # cleanroom vs reviewer(b_solver)
mismatch_B_C = []
total_steps = 0
all_levels_ok = True

for lv in levels:
    lid = lv["id"]; n = lv["size"]
    mines = {r * n + c for r, c in lv["mines"]}
    counts = [sum(1 for j in bs.neighbors(n, i) if j in mines) for i in range(n * n)]
    # 复核状态机（只用 b_solver 的 Player 做「翻开+flood fill」的状态推进，枚举规则由本脚本提供）
    p = bs.Player(lv, counts, use_runs=True)
    p.reveal(lv["opening"][0] * n + lv["opening"][1], "opening")
    steps = rep.get(lid, [])
    total_steps += len(steps)
    bad = []
    for (no, rule, kind, r, c) in steps:
        i = (r - 1) * n + (c - 1)
        state = p.state
        a_safe, a_mine = forced_a(n, state, counts)
        cr_mine, cr_safe = set(), set()
        for axis in (0, 1):
            for k in range(n):
                idx = [k * n + t for t in range(n)] if axis == 0 else [t * n + k for t in range(n)]
                runs = lv["rowRuns"][k] if axis == 0 else lv["colRuns"][k]
                known = [None if state[x] == UNK else (1 if state[x] == MINE else 0) for x in idx]
                if not lv["showRuns"]:
                    continue
                A = cleanroom_patterns(n, runs, known)
                B = {frozenset(m) for m in gen.line_patterns(n, runs, [state[x] for x in idx])}
                C, contra = bs.line_placements(n, runs, known)
                C = set() if contra else {frozenset(t for t in range(n) if tup[t]) for tup in C}
                if A != B:
                    mismatch_A_B.append((lid, no, axis, k, sorted(map(sorted, A)), sorted(map(sorted, B))))
                if A != C:
                    mismatch_A_C.append((lid, no, axis, k, sorted(map(sorted, A)), sorted(map(sorted, C))))
                if B != C:
                    mismatch_B_C.append((lid, no, axis, k, sorted(map(sorted, B)), sorted(map(sorted, C))))
                am, asf = forced_from_patterns(n, A)
                cr_mine |= {idx[t] for t in am}
                cr_safe |= {idx[t] for t in asf}
        if kind == "判定雷":
            ok = i in (a_mine if rule == "邻域" else cr_mine)
        else:
            ok = i in (a_safe if rule == "邻域" else cr_safe)
        if not ok:
            other = i in (cr_safe if rule == "邻域" else a_safe) or i in (cr_mine if rule == "邻域" else a_mine)
            bad.append({"step": no, "rule": rule, "kind": kind, "rc": [r, c],
                        "state": {UNK: "未知", SAFE: "已翻开", MINE: "已知雷"}[state[i]],
                        "other_rule_justifies": bool(other)})
        if kind == "判定雷":
            p.flag_deduced([i], "replay")
        else:
            p.reveal_deduced([i], "replay")
    complete = all(s != UNK for s in p.state)
    deduced = {x for x, s in enumerate(p.state) if s == MINE}
    print("第 %2d 关：%2d 步 ｜ 干净枚举重放全部可推出 = %s ｜ 推完全盘 = %s ｜ 雷位与真值一致 = %s" % (
        lid, len(steps), (not bad), complete, deduced == mines))
    if bad:
        all_levels_ok = False
        print("        ★仍推不出：%s" % bad)
    if not (complete and deduced == mines):
        all_levels_ok = False

print()
print("== 三套行/列枚举器在全流程（全部关卡 × 每一步 × 每一行/列）中的一致性 ==")
print("  参与比对的「状态×行/列」样本数 = 见下；总计报告步数 = %d" % total_steps)
print("  cleanroom vs generator(line_patterns) 不一致次数 = %d" % len(mismatch_A_B))
print("  cleanroom vs reviewer(line_placements) 不一致次数 = %d" % len(mismatch_A_C))
print("  generator vs reviewer 不一致次数 = %d" % len(mismatch_B_C))
for label, arr in (("cleanroom!=generator", mismatch_A_B), ("cleanroom!=reviewer", mismatch_A_C)):
    if arr:
        lid, no, axis, k, A, C = arr[0]
        print("  首个反例 [%s]：第 %d 关 第 %d 步 %s%d" % (label, lid, no, "行" if axis == 0 else "列", k + 1))
        print("     cleanroom = %s" % A)
        print("     对照实现  = %s" % C)
print()
print("结论：报告全部打印序列在干净枚举手底下 %s（%d 步，10 关）" % (
    "全部逐步可复现" if all_levels_ok else "仍有不可复现步骤", total_steps))