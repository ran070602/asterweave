# -*- coding: utf-8 -*-
"""
T8 独立复核 · B 部分：玩法可解性。

实现一个「只会做可靠推理的玩家」：
  (a) 邻域计数传播（扫雷）
  (b) 数织行/列枚举（取交集得强制雷 / 强制安全格）
交替迭代到不动点；每判定一个安全格就翻开并触发 flood fill。

独立性声明：本文件完全自写，不 import、不复制 tools/generate_levels.py 的任何代码。

用法：
    python verification/b_solver.py            # 每关 60s 上限
输出：
    stdout 日志 + verification/out_b.json（含 D 部分驱动所需的动作序列）
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS_JSON = Path(os.environ.get("T8_LEVELS", ROOT / "tools" / "levels.json"))

UNKNOWN, SAFE, MINE = 0, 1, 2
TIME_LIMIT = 60.0  # 每关


# ---------------------------------------------------------------- 基础工具
def neighbors(n, i):
    r, c = divmod(i, n)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n:
                yield rr * n + cc


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


def line_placements(n, runs, known):
    """枚举长度为 n 的一行/一列中所有与 runs 及 known 相容的布雷方案。
    known[k] ∈ {None 未知, 0 已知安全, 1 已知雷}
    返回 (placements, contradictory)
    """
    out = []
    arr = [0] * n
    k = len(runs)

    def rec(bi, start):
        if bi == k:
            for p in range(start, n):          # 尾部必须全是安全格
                if known[p] == 1:
                    return
            for p in range(start, n):
                arr[p] = 0
            out.append(tuple(arr))
            return
        L = runs[bi]
        rest = runs[bi + 1:]
        need = sum(rest) + len(rest)           # 本块之后还需要的最少格数
        s_max = n - L - need
        for s in range(start, s_max + 1):
            bad = False
            for p in range(start, s):          # 本块之前的空隙必须安全
                if known[p] == 1:
                    bad = True
                    break
            if bad:
                break                          # known mine 固定 → 更大的 s 只会更糟
            for p in range(s, s + L):
                if known[p] == 0:
                    bad = True
                    break
            if bad:
                continue
            for p in range(start, s):
                arr[p] = 0
            for p in range(s, s + L):
                arr[p] = 1
            if rest:
                gap = s + L                    # 块后必须有一个安全格做分隔
                if gap >= n or known[gap] == 1:
                    continue
                arr[gap] = 0
            rec(bi + 1, s + L + 1)
        return

    rec(0, 0)
    return out, (len(out) == 0)


# ---------------------------------------------------------------- 求解器
class Player:
    """只会可靠推理的玩家。不使用真实雷位置（除 counts 外），只使用 counts/线索/自身判定。"""

    def __init__(self, level, counts, use_runs):
        self.lv = level
        self.n = level["size"]
        self.counts = counts
        self.use_runs = use_runs
        self.state = [UNKNOWN] * (self.n * self.n)   # 0 未知 / 1 已翻开安全 / 2 已知雷
        self.steps = []                              # (rule, kind, i)
        self.explicit_safe = 0                       # 显式「探格」次数
        self.log_note = []
        self.contradiction = None

    # ---- 翻开 + flood fill ----
    def reveal(self, i, rule):
        if self.state[i] == SAFE:
            return False
        st = [i]
        while st:
            cur = st.pop()
            if self.state[cur] == SAFE or self.state[cur] == MINE:
                continue
            if self.contradiction:
                return False
            self.state[cur] = SAFE
            if self.counts[cur] == 0:
                for j in neighbors(self.n, cur):
                    if self.state[j] == UNKNOWN:
                        st.append(j)
        return True

    def reveal_deduced(self, cells, rule):
        # 注意：只有真正把 UNKNOWN 变成 SAFE 才算「有推进」，否则不动点判定会死循环。
        changed = False
        for i in cells:
            if self.state[i] != UNKNOWN:
                continue
            self.steps.append((rule, "safe", i))
            self.explicit_safe += 1
            self.reveal(i, rule)
            changed = True
        return changed

    def flag_deduced(self, cells, rule):
        n_new = 0
        for i in cells:
            if self.state[i] == MINE:
                continue
            if self.state[i] == SAFE:
                self.contradiction = "rule %s 把已翻开的安全格 %s 判成雷" % (rule, self.coord(i))
                return True
            self.state[i] = MINE
            self.steps.append((rule, "mine", i))
            n_new += 1
        return n_new > 0

    def coord(self, i):
        r, c = divmod(i, self.n)
        return "(%d,%d)" % (r + 1, c + 1)

    # ---- (a) 邻域计数传播 ----
    def apply_a(self):
        forced_safe, forced_mine = [], []
        for i in range(self.n * self.n):
            if self.state[i] != SAFE:
                continue
            flags = 0
            unknown = []
            for j in neighbors(self.n, i):
                if self.state[j] == MINE:
                    flags += 1
                elif self.state[j] == UNKNOWN:
                    unknown.append(j)
            if not unknown:
                continue
            if self.counts[i] == flags:
                forced_safe.extend(unknown)
            elif self.counts[i] == flags + len(unknown):
                forced_mine.extend(unknown)
        changed = False
        if forced_mine:
            changed = self.flag_deduced(forced_mine, "a") or changed
        if forced_safe:
            changed = self.reveal_deduced(forced_safe, "a") or changed
        return changed

    # ---- (b) 数织行/列枚举 ----
    def apply_b(self):
        n = self.n
        forced_safe, forced_mine = set(), set()
        for is_row in (True, False):
            for k in range(n):
                if is_row:
                    idx = [k * n + t for t in range(n)]
                    runs = self.lv["rowRuns"][k]
                else:
                    idx = [t * n + k for t in range(n)]
                    runs = self.lv["colRuns"][k]
                known = []
                for i in idx:
                    known.append(None if self.state[i] == UNKNOWN else (1 if self.state[i] == MINE else 0))
                placements, contra = line_placements(n, runs, known)
                if contra:
                    self.contradiction = "第 %s %d 的连续块线索与已知状态矛盾（无任何相容摆放）" % (
                        "行" if is_row else "列", k + 1)
                    return False
                for t in range(n):
                    vals = {p[t] for p in placements}
                    if vals == {1}:
                        forced_mine.add(idx[t])
                    elif vals == {0}:
                        forced_safe.add(idx[t])
        changed = False
        if forced_mine:
            changed = self.flag_deduced(sorted(forced_mine), "b") or changed
        if forced_safe:
            changed = self.reveal_deduced(sorted(forced_safe), "b") or changed
        return changed

    # ---- 主循环 ----
    def run(self, deadline):
        op = self.lv["opening"]
        oi = op[0] * self.n + op[1]
        self.reveal(oi, "opening")
        timeout = False
        rounds = 0
        while True:
            if time.monotonic() > deadline:
                timeout = True
                break
            rounds += 1
            progressed = False
            while True:
                c1 = self.apply_a()
                c2 = self.apply_b() if (self.use_runs and self.lv["showRuns"]) else False
                if c1 or c2:
                    progressed = True
                else:
                    break
                if time.monotonic() > deadline:
                    timeout = True
                    break
            if timeout:
                break
            if not progressed:
                break
            if all(s != UNKNOWN for s in self.state):
                break
        complete = all(s != UNKNOWN for s in self.state)
        return {
            "complete": complete and not timeout and not self.contradiction,
            "timeout": timeout,
            "contradiction": self.contradiction,
            "rounds": rounds,
        }


def main():
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    out = {"time_limit_s": TIME_LIMIT, "levels": []}

    for lv in levels:
        n = lv["size"]
        total = n * n
        true_mines = {r * n + c for r, c in lv["mines"]}
        counts = [0] * total
        for i in range(total):
            counts[i] = sum(1 for j in neighbors(n, i) if j in true_mines)

        print("=" * 78)
        print("第 %d 关 %dx%d 雷=%d showRuns=%s opening=%s" % (
            lv["id"], n, n, len(true_mines), lv["showRuns"], lv["opening"]))
        rec = {"id": lv["id"], "size": n, "mines_true": sorted(true_mines)}

        for tag, use_runs in (("a_only", False), ("a_plus_b", True)):
            t0 = time.monotonic()
            p = Player(lv, counts, use_runs)
            res = p.run(t0 + TIME_LIMIT)
            dt = time.monotonic() - t0
            deduced_mines = {i for i, s in enumerate(p.state) if s == MINE}
            revealed = {i for i, s in enumerate(p.state) if s == SAFE}
            unknown_cells = [i for i, s in enumerate(p.state) if s == UNKNOWN]
            # 正确性：判定结果必须与真实布雷一致（求解器不使用真实位置，这里只是复核）
            mine_correct = deduced_mines == true_mines
            safe_correct = revealed.isdisjoint(true_mines)
            n_a = sum(1 for r, k, _ in p.steps if r == "a")
            n_b = sum(1 for r, k, _ in p.steps if r == "b")
            n_a_safe = sum(1 for r, k, _ in p.steps if r == "a" and k == "safe")
            n_a_mine = sum(1 for r, k, _ in p.steps if r == "a" and k == "mine")
            n_b_safe = sum(1 for r, k, _ in p.steps if r == "b" and k == "safe")
            n_b_mine = sum(1 for r, k, _ in p.steps if r == "b" and k == "mine")
            r = {
                "mode": tag, "use_runs": use_runs,
                "complete": res["complete"], "timeout": res["timeout"],
                "contradiction": res["contradiction"],
                "elapsed_s": round(dt, 4),
                "steps_total": len(p.steps),
                "steps_a": n_a, "steps_b": n_b,
                "a_safe": n_a_safe, "a_mine": n_a_mine,
                "b_safe": n_b_safe, "b_mine": n_b_mine,
                "explicit_reveals": p.explicit_safe,
                "revealed_total": len(revealed),
                "deduced_mines": len(deduced_mines),
                "unknown_left": len(unknown_cells),
                "deduced_mines_equal_truth": mine_correct,
                "revealed_all_safe_true": safe_correct,
                "unknown_cells_1based": ["(%d,%d)" % (i // n + 1, i % n + 1) for i in unknown_cells[:40]],
                "steps_seq": [{"rule": a, "kind": b,
                               "rc": [i // n + 1, i % n + 1]} for a, b, i in p.steps],
                "solve_actions": [{"rule": a, "kind": b, "r": i // n, "c": i % n}
                                  for a, b, i in p.steps],
            }
            rec[tag] = r
            print("  [%s] 完成=%s 超时=%s 矛盾=%s 用时=%.4fs 步数=%d (a:%d b:%d) "
                  "显式探格=%d 已翻开=%d/%d 判定雷=%d/%d 剩余未判定=%d 判定与真值一致=%s" % (
                      tag, r["complete"], r["timeout"], r["contradiction"], dt, r["steps_total"],
                      n_a, n_b, p.explicit_safe, len(revealed), total - len(true_mines),
                      len(deduced_mines), len(true_mines), len(unknown_cells), mine_correct))
            if not res["complete"]:
                print("       卡住时剩余未判定格(1-based, 前40): %s" % r["unknown_cells_1based"])
            if res["contradiction"]:
                print("       矛盾: %s" % res["contradiction"])
            if tag == "a_plus_b" and res["complete"]:
                print("       完整推理序列:")
                for i, s in enumerate(p.steps, 1):
                    print("        %2d. [%s] %s %s" % (
                        i, "邻域" if s[0] == "a" else "连续块",
                        "判定雷  " if s[1] == "mine" else "探开安全格", p.coord(s[2])))

        a = rec["a_only"]
        b = rec["a_plus_b"]
        rec["verdict"] = {
            "a_only_solves": a["complete"],
            "a_plus_b_solves": b["complete"],
            "b_needed": (not a["complete"]) and b["complete"],
            "b_contribution_cells": b["steps_b"],
        }
        out["levels"].append(rec)

    (ROOT / "verification" / "out_b.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 78)
    print("== B 部分断言（10 关教学带：1–3 关纯(a)；4–10 关必须用(b)）==")
    ok_all = True
    for rec in out["levels"]:
        lid = rec["id"]
        v = rec["verdict"]
        ap = rec["a_plus_b"]
        if lid <= 3:
            pass_n = v["a_only_solves"] and ap["steps_b"] == 0
            print("第 %d 关[教学带:纯(a)]: 只用(a)通关=%s ; (b)贡献格数=%d ; => %s" % (
                lid, v["a_only_solves"], ap["steps_b"], "通过" if pass_n else "不通过"))
        else:
            pass_n = (not v["a_only_solves"]) and v["a_plus_b_solves"] and ap["steps_b"] > 0
            print("第 %d 关[教学带:需(b)]: 只用(a)通关=%s ; 加(b)通关=%s ; (b)贡献格数=%d ; => %s" % (
                lid, v["a_only_solves"], v["a_plus_b_solves"], ap["steps_b"],
                "通过" if pass_n else "不通过"))
        ok_all &= pass_n
        # 通用正确性：推完就必须推对
        ok_all &= ap["deduced_mines_equal_truth"] and ap["revealed_all_safe_true"]
    print("B 部分总判定: %s" % ("10 关教学带意图全部满足" if ok_all else "存在不满足教学带意图的关卡"))
    print("JSON -> verification/out_b.json")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())