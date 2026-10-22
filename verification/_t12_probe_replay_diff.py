# -*- coding: utf-8 -*-
"""T12 第二轮诊断：为什么报告第 5 关第 16 步 / 第 7 关第 15 步回放不通？

方法：用复核方自己的实现（b_solver）把报告序列重放到「该步之前」，
然后对同一状态、同一批行列线索，分别用
  ① b_solver.line_placements（复核实现）
  ② tools.generate_levels.line_patterns（作者实现，**仅用于诊断对照，不进入复核结论的独立性链**）
算「该行/列在所有相容摆放中都是安全/都是雷」的格集合，逐行比较差异。

若两者一致 → 说明不是枚举模型差异，而是「打印顺序 ≠ 真实应用顺序」；
若不一致 → 定位到具体行/列与具体原因。
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

UNK, SAFE, MINE = gen.UNKNOWN, gen.SAFE, gen.MINE
print("generator constants: UNKNOWN=%r SAFE=%r MINE=%r" % (UNK, SAFE, MINE))
print("b_solver constants:  UNKNOWN=%r SAFE=%r MINE=%r" % (bs.UNKNOWN, bs.SAFE, bs.MINE))

levels = json.loads((ROOT / "tools/levels.json").read_text(encoding="utf-8"))
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


def gen_forced(n, runs, fixed):
    """作者实现的单行/列强制集。"""
    pats = gen.line_patterns(n, runs, fixed)
    if not pats:
        return set(), set(), 0
    mine = set(pats[0])
    safe = set(range(n)) - set(pats[0])
    for p in pats[1:]:
        mine &= p
        safe &= (set(range(n)) - p)
    return mine, safe, len(pats)


def bs_forced(n, runs, known):
    """复核实现的单行/列强制集。"""
    placements, contra = bs.line_placements(n, runs, known)
    if contra:
        return set(), set(), 0
    mine, safe = set(), set()
    for t in range(n):
        vals = {p[t] for p in placements}
        if vals == {1}:
            mine.add(t)
        elif vals == {0}:
            safe.add(t)
    return mine, safe, len(placements)


for lid, watch in ((5, 16), (7, 15)):
    lv = levels[lid - 1]
    n = lv["size"]
    mines = {r * n + c for r, c in lv["mines"]}
    counts = [sum(1 for j in bs.neighbors(n, i) if j in mines) for i in range(n * n)]
    p = bs.Player(lv, counts, use_runs=True)
    p.reveal(lv["opening"][0] * n + lv["opening"][1], "opening")
    for (no, rule, kind, r, c) in rep[lid]:
        if no == watch:
            break
        i = (r - 1) * n + (c - 1)
        if kind == "判定雷":
            p.flag_deduced([i], "replay")
        else:
            p.reveal_deduced([i], "replay")
    print("=" * 80)
    print("第 %d 关：已重放 %d 步，检查第 %d 步（%s %s (%d,%d)）" % (lid, watch - 1, watch, rule, kind, r, c))
    target = (r - 1) * n + (c - 1)
    st_now = p.state
    print("  该步目标格索引 %d ；目标格状态=%s ；真值是雷? %s" % (
        target, {bs.UNKNOWN: "未知", bs.SAFE: "已翻开", bs.MINE: "已知雷"}[st_now[target]], target in mines))
    print("  该状态：已翻开 %d 格，已知雷 %d 个，未判定 %d 格" % (
        sum(1 for s in st_now if s == bs.SAFE), sum(1 for s in st_now if s == bs.MINE),
        sum(1 for s in st_now if s == bs.UNKNOWN)))
    diffs = 0
    for axis in (0, 1):
        for k in range(n):
            idx = [k * n + t for t in range(n)] if axis == 0 else [t * n + k for t in range(n)]
            runs = lv["rowRuns"][k] if axis == 0 else lv["colRuns"][k]
            fixed = [st_now[i] for i in idx]                      # 作者的编码
            known = [None if st_now[i] == bs.UNKNOWN else (1 if st_now[i] == bs.MINE else 0) for i in idx]
            gm, gs, gp = gen_forced(n, runs, fixed)
            bm, bsq, bp = bs_forced(n, runs, known)
            if gm != bm or gs != bsq:
                diffs += 1
                print("  ★差异 %s%d 线索=%s ｜ 作者: 摆放数=%d 强制雷=%s 强制安全=%s ｜ 复核: 摆放数=%d 强制雷=%s 强制安全=%s" % (
                    "行" if axis == 0 else "列", k + 1, runs, gp, sorted(gm), sorted(gs), bp, sorted(bm), sorted(bsq)))
    print("  行列枚举差异行数 = %d" % diffs)
    # 该步是否在任一实现里被强制
    all_g_safe, all_b_safe = set(), set()
    for axis in (0, 1):
        for k in range(n):
            idx = [k * n + t for t in range(n)] if axis == 0 else [t * n + k for t in range(n)]
            runs = lv["rowRuns"][k] if axis == 0 else lv["colRuns"][k]
            fixed = [st_now[i] for i in idx]
            known = [None if st_now[i] == bs.UNKNOWN else (1 if st_now[i] == bs.MINE else 0) for i in idx]
            gm, gs, _ = gen_forced(n, runs, fixed)
            bm, bsq, _ = bs_forced(n, runs, known)
            all_g_safe |= {idx[t] for t in gs}
            all_b_safe |= {idx[t] for t in bsq}
    print("  作者枚举的强制安全集合含目标格? %s ｜ 复核枚举含目标格? %s" % (
        target in all_g_safe, target in all_b_safe))
    # 附：该步目标格是否被「（a）邻域」强制
    a_safe, a_mine = set(), set()
    for i in range(n * n):
        if st_now[i] != bs.SAFE:
            continue
        flags, unknown = 0, []
        for j in bs.neighbors(n, i):
            if st_now[j] == bs.MINE:
                flags += 1
            elif st_now[j] == bs.UNKNOWN:
                unknown.append(j)
        if not unknown:
            continue
        if counts[i] == flags:
            a_safe.update(unknown)
        elif counts[i] == flags + len(unknown):
            a_mine.update(unknown)
    print("  (a)邻域强制安全集合含目标格? %s" % (target in a_safe))
    print("  目标格在该行/列的**作者摆放集合**里是否为安全格（逐个 pattern 检查）:")
    for axis in (0, 1):
        kk = (target // n) if axis == 0 else (target % n)
        idx = [kk * n + t for t in range(n)] if axis == 0 else [t * n + kk for t in range(n)]
        runs = lv["rowRuns"][kk] if axis == 0 else lv["colRuns"][kk]
        fixed = [st_now[i] for i in idx]
        pats = gen.line_patterns(n, runs, fixed)
        tpos = idx.index(target)
        vals = sorted({(1 if tpos in pl else 0) for pl in pats})
        print("    %s%d：摆放数=%d，目标格取值集合=%s" % ("行" if axis == 0 else "列", kk + 1, len(pats), vals))