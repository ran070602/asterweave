# -*- coding: utf-8 -*-
"""T12 第二轮诊断（细化）：把同一行线索交给两套实现，逐个摆放对照。"""
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


def show(lid, watch, axis_sel, k_sel):
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
        (p.flag_deduced if kind == "判定雷" else p.reveal_deduced)([i], "replay")
    st = p.state
    idx = [k_sel * n + t for t in range(n)] if axis_sel == 0 else [t * n + k_sel for t in range(n)]
    runs = lv["rowRuns"][k_sel] if axis_sel == 0 else lv["colRuns"][k_sel]
    fixed = [st[i] for i in idx]
    known = [None if st[i] == bs.UNKNOWN else (1 if st[i] == bs.MINE else 0) for i in idx]
    truth = [1 if i in mines else 0 for i in idx]
    name = {0: "?", 1: "安全", 2: "雷"}
    print("=" * 76)
    print("第 %d 关 · %s%d · n=%d · 线索 runs=%s" % (lid, "行" if axis_sel == 0 else "列", k_sel + 1, n, runs))
    print("  该行已知状态 fixed(0未知/1安全/2雷) = %s" % [name[v] for v in fixed])
    print("  复核 known(None/? ,0安全,1雷)       = %s" % known)
    print("  真值                                 = %s" % ["雷" if v else "安全" for v in truth])
    ap = gen.line_patterns(n, runs, fixed)
    rp, contra = bs.line_placements(n, runs, known)
    print("  作者 line_patterns 摆放数=%d（contra=%s）:" % (len(ap), not ap))
    for m in ap:
        print("     %s   (雷位=%s)" % ("".join("X" if c in m else "." for c in range(n)), sorted(m)))
    print("  复核 line_placements 摆放数=%d（contra=%s）:" % (len(rp), contra))
    for t in rp:
        print("     %s   (雷位=%s)" % ("".join("X" if v else "." for v in t), [i for i, v in enumerate(t) if v]))
    sa = set(range(n)) - set(ap[0]) if ap else set()
    for m in ap[1:]:
        sa &= set(range(n)) - m
    ma = set(ap[0]) if ap else set()
    for m in ap[1:]:
        ma &= m
    sr = {t for t in range(n) if all(pl[t] == 0 for pl in rp)} if rp else set()
    mr = {t for t in range(n) if all(pl[t] == 1 for pl in rp)} if rp else set()
    print("  作者强制: 雷=%s 安全=%s" % (sorted(ma), sorted(sa)))
    print("  复核强制: 雷=%s 安全=%s" % (sorted(mr), sorted(sr)))
    print("  该行真实雷位 = %s ；作者摆放里是否为唯一真值 = %s" % (
        [i for i, v in enumerate(truth) if v], [i for i, v in enumerate(truth) if v] in [sorted(m) for m in ap]))


show(5, 16, 0, 3)
show(7, 15, 0, 6)