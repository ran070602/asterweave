# -*- coding: utf-8 -*-
"""
T8 独立复核 · B 附加：核对 tools/report.md 自述的「推理序列」是不是一条合法可玩的路线。

手法：按报告给出的顺序逐步重放，每一步检查「在当时的已知状态下，该步声明的规则
（邻域 / 连续块）是否真的能推出该结论」。任何一步用到了当前信息推不出的结论 = 报告夸大。

用法：
    python verification/b3_replay_report.py
输出：
    stdout + verification/out_b3.json
"""
import json
import os
import re
import sys
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parent.parent
REPORT = Path(os.environ.get("T8_REPORT", ROOT / "tools" / "report.md"))
LEVELS_JSON = Path(os.environ.get("T8_LEVELS", ROOT / "tools" / "levels.json"))

# 复用我自己（T8）写的求解器原语：合法，因为它不是 tools/generate_levels.py 的代码
spec = importlib.util.spec_from_file_location("b_solver", ROOT / "verification" / "b_solver.py")
bs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bs)

STEP_RE = re.compile(r"^\s*-\s*(\d+)\.\s*\[(邻域|连续块)\]\s*(判定雷|探开安全格)\s*\((\d+),(\d+)\)\s*$")
SEC_RE = re.compile(r"^###\s*第\s*(\d+)\s*关")


def parse_report(text):
    cur, secs = None, {}
    for line in text.splitlines():
        m = SEC_RE.match(line)
        if m:
            cur = int(m.group(1))
            secs[cur] = []
            continue
        if cur is None:
            continue
        m = STEP_RE.match(line)
        if m:
            secs[cur].append({"n": int(m.group(1)), "rule": m.group(2), "kind": m.group(3),
                              "r": int(m.group(4)), "c": int(m.group(5))})
    return secs


def forced_sets(p):
    """返回 (a_safe, a_mine, b_safe, b_mine)：当前状态下两类规则各自能强制推出的格。"""
    n = p.n
    a_safe, a_mine = set(), set()
    for i in range(n * n):
        if p.state[i] != bs.SAFE:
            continue
        flags, unknown = 0, []
        for j in bs.neighbors(n, i):
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
            for k in range(n):
                idx = [k * n + t for t in range(n)] if is_row else [t * n + k for t in range(n)]
                runs = p.lv["rowRuns"][k] if is_row else p.lv["colRuns"][k]
                known = [None if p.state[i] == bs.UNKNOWN else (1 if p.state[i] == bs.MINE else 0)
                         for i in idx]
                placements, _ = bs.line_placements(n, runs, known)
                for t in range(n):
                    vals = {pl[t] for pl in placements}
                    if vals == {1}:
                        b_mine.add(idx[t])
                    elif vals == {0}:
                        b_safe.add(idx[t])
    return a_safe, a_mine, b_safe, b_mine


def main():
    rep = parse_report(REPORT.read_text(encoding="utf-8"))
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    out = {"levels": []}
    all_ok = True
    for lv in levels:
        lid = lv["id"]
        n = lv["size"]
        total = n * n
        true_mines = {r * n + c for r, c in lv["mines"]}
        counts = [0] * total
        for i in range(total):
            counts[i] = sum(1 for j in bs.neighbors(n, i) if j in true_mines)
        p = bs.Player(lv, counts, use_runs=True)
        p.reveal(lv["opening"][0] * n + lv["opening"][1], "opening")

        bad = []
        for st in rep.get(lid, []):
            i = (st["r"] - 1) * n + (st["c"] - 1)
            a_safe, a_mine, b_safe, b_mine = forced_sets(p)
            if st["kind"] == "判定雷":
                ok_declared = (i in a_mine) if st["rule"] == "邻域" else (i in b_mine)
                ok_other = (i in b_mine) if st["rule"] == "邻域" else (i in a_mine)
            else:
                ok_declared = (i in a_safe) if st["rule"] == "邻域" else (i in b_safe)
                ok_other = (i in b_safe) if st["rule"] == "邻域" else (i in a_safe)
            if not ok_declared:
                bad.append({"step": st["n"], "rule": st["rule"], "kind": st["kind"],
                            "rc": [st["r"], st["c"]],
                            "state": "已翻开" if p.state[i] == bs.SAFE else
                                     ("已知雷" if p.state[i] == bs.MINE else "未知"),
                            "other_rule_justifies": bool(ok_other),
                            "verdict": "另一类规则能推出（归属/顺序标注问题）" if ok_other
                                       else "两类规则都推不出（按此顺序会卡住）"})
            # 应用该步（按报告声明的方式）
            if st["kind"] == "判定雷":
                p.flag_deduced([i], "report")
            else:
                p.reveal_deduced([i], "report")
        deduced = {i for i, s in enumerate(p.state) if s == bs.MINE}
        complete = all(s != bs.UNKNOWN for s in p.state)
        rec = {"id": lid, "steps": len(rep.get(lid, [])), "illegal_steps": bad,
               "complete_after_replay": complete,
               "mines_equal_truth": deduced == true_mines}
        out["levels"].append(rec)
        print("=" * 70)
        print("第 %d 关：报告序列 %d 步" % (lid, len(rep.get(lid, []))))
        print("  按报告顺序重放：全部步骤都能被声明的规则推出 = %s" % (not bad))
        if bad:
            print("  ★非法/推不出的步骤： %s" % bad[:5])
        print("  重放后是否推完全盘 = %s ；判定出的雷与真值一致 = %s" % (complete, rec["mines_equal_truth"]))
        all_ok &= (not bad) and complete and rec["mines_equal_truth"]
    (ROOT / "verification" / "out_b3.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("B3 附加判定：报告推理序列%s（10 关逐关核对）" % (
        "全部合法可玩，未发现夸大" if all_ok else "存在推不出的步骤（见上）"))
    print("JSON -> verification/out_b3.json")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())