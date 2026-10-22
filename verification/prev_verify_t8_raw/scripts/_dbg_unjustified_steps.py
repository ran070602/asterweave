# -*- coding: utf-8 -*-
"""
诊断：报告序列里推不出的两步（第 5 关 step12、第 7 关 step15）是否只有在
“额外引入全局雷数约束”（报告未声明使用）时才成立？

做法：重放到该步之前的状态，然后
  (1) 只用报告声明的 (a)/(b) -> 是否强制（已知结论：否）
  (2) 行枚举 + 列线索前缀 + 全局雷数约束 + 当前已翻开格数字 -> 是否强制
"""
import importlib.util
import itertools
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEV = Path(os.environ.get("T8_LEVELS", ROOT / "verification" / "frozen10" / "levels_10levels.json"))
REP = Path(os.environ.get("T8_REPORT", ROOT / "verification" / "frozen10" / "report_10levels.md"))

spec = importlib.util.spec_from_file_location("b_solver", ROOT / "verification" / "b_solver.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

import re
STEP_RE = re.compile(r"^\s*-\s*(\d+)\.\s*\[(邻域|连续块)\]\s*(判定雷|探开安全格)\s*\((\d+),(\d+)\)\s*$")
SEC_RE = re.compile(r"^###\s*第\s*(\d+)\s*关")


def parse_report(text):
    cur, secs = None, {}
    for line in text.splitlines():
        m = SEC_RE.match(line)
        if m:
            cur = int(m.group(1)); secs[cur] = []; continue
        if cur is None:
            continue
        m = STEP_RE.match(line)
        if m:
            secs[cur].append({"n": int(m.group(1)), "rule": m.group(2), "kind": m.group(3),
                              "r": int(m.group(4)), "c": int(m.group(5))})
    return secs


def global_forced(lv, state, counts, targets, cap=30_000_000):
    n = lv["size"]
    rows = []
    for r in range(n):
        known = []
        for c in range(n):
            s = state[r * n + c]
            known.append(None if s == bs.UNKNOWN else (1 if s == bs.MINE else 0))
        opts, _ = bs.line_placements(n, lv["rowRuns"][r], known)
        rows.append(opts)
    prod = 1
    for o in rows:
        prod *= len(o)
    if prod > cap:
        return None, prod
    col_runs = [list(x) for x in lv["colRuns"]]
    decl = len(lv["mines"])
    forced = {t: {"mine": True, "safe": True} for t in targets}
    nsol = 0
    for combo in itertools.product(*rows):
        if sum(sum(p) for p in combo) != decl:
            continue
        if any(bs.runs_of([combo[r][c] for r in range(n)]) != col_runs[c] for c in range(n)):
            continue
        ok = True
        for i in range(n * n):
            if state[i] == bs.SAFE:
                if sum(1 for j in bs.neighbors(n, i) if combo[j // n][j % n]) != counts[i]:
                    ok = False; break
        if not ok:
            continue
        nsol += 1
        for t in targets:
            v = combo[t // n][t % n]
            if v == 1:
                forced[t]["safe"] = False
            else:
                forced[t]["mine"] = False
    return {"solutions": nsol, "forced": forced}, prod


def main():
    rep = parse_report(REP.read_text(encoding="utf-8"))
    levels = json.loads(LEV.read_text(encoding="utf-8"))
    by_id = {l["id"]: l for l in levels}
    for lid, step_no in ((5, 12), (7, 15)):
        lv = by_id[lid]
        n = lv["size"]
        true_mines = {r * n + c for r, c in lv["mines"]}
        counts = [sum(1 for j in bs.neighbors(n, i) if j in true_mines) for i in range(n * n)]
        p = bs.Player(lv, counts, use_runs=True)
        p.reveal(lv["opening"][0] * n + lv["opening"][1], "opening")
        target = None
        for st in rep[lid]:
            i = (st["r"] - 1) * n + (st["c"] - 1)
            if st["n"] == step_no:
                target = i
                break
            if st["kind"] == "判定雷":
                p.flag_deduced([i], "report")
            else:
                p.reveal_deduced([i], "report")
        print("=" * 70)
        print("第 %d 关 step %d：目标格 (1-based %d,%d)" % (lid, step_no, target // n + 1, target % n + 1))
        print("  该步声明规则 = %s ；当前状态 = %s" % (
            [s for s in rep[lid] if s["n"] == step_no][0]["rule"],
            "未知" if p.state[target] == bs.UNKNOWN else "其他"))
        res, prod = global_forced(lv, p.state, counts, [target])
        if res is None:
            print("  全局约束枚举规模 %d 超上限，未执行" % prod)
        else:
            print("  引入全局雷数约束后：相容方案数=%d ；目标格在所有方案中都是安全=%s ；都是雷=%s"
                  % (res["solutions"], res["forced"][target]["safe"], res["forced"][target]["mine"]))


if __name__ == "__main__":
    main()