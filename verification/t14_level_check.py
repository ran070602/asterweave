#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T14 独立复核 · v0.7 关卡层：
  A 数据自洽（mines = theme.stars ∪ noise、线索一致、opening=0 格、内嵌==文件）
  B 逐关零猜测可解（自写：邻域计数传播 + 数织行/列全枚举 + flood fill，交替到不动点）
  D 难度指标（开局展开占比、0 格占比/安全格、探格次数 vs fit_constellation_levels.py 的目标带）
  S 供 UI 运行时使用的逐步动作序列（verification/t14_play_sequences.json）
不 import / 不复制 tools/generate_levels.py 与 tools/fit_constellation_levels.py。
用法：python verification/t14_level_check.py
输出：stdout + verification/t14_out_ab.json + verification/t14_play_sequences.json
"""
import itertools
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS_JSON = Path(os.environ.get("T14_LEVELS", ROOT / "tools" / "levels.json"))
DIST_HTML = Path(os.environ.get("T14_DIST", ROOT / "dist" / "星织-游戏本体" / "index.html"))
GAME_HTML = Path(os.environ.get("T14_GAME", ROOT / "game" / "index.html"))
FIT_PY = ROOT / "tools" / "fit_constellation_levels.py"


def runs_of(bits):
    out, cur = [], 0
    for b in bits:
        if b:
            cur += 1
        else:
            if cur:
                out.append(cur)
                cur = 0
    if cur:
        out.append(cur)
    return out


def nbrs_list(n):
    out = []
    for r in range(n):
        for c in range(n):
            lst = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < n and 0 <= cc < n:
                        lst.append(rr * n + cc)
            out.append(lst)
    return out


class Ctx:
    def __init__(self, lv):
        self.lv = lv
        self.n = n = lv["size"]
        self.total = n * n
        self.mines = {r * n + c for r, c in lv["mines"]}
        self.nbrs = nbrs_list(n)
        self.counts = [sum(1 for j in self.nbrs[i] if j in self.mines) for i in range(self.total)]
        self.revealed = set()
        self._flood(lv["opening"][0] * n + lv["opening"][1])

    def _flood(self, start):
        st = [start]
        while st:
            i = st.pop()
            if i in self.revealed or i in self.mines:
                continue
            self.revealed.add(i)
            if self.counts[i] == 0:
                for j in self.nbrs[i]:
                    if j not in self.revealed and j not in self.mines:
                        st.append(j)


def expected_runs(lv, by_row):
    n = lv["size"]
    ms = {tuple(x) for x in lv["mines"]}
    if by_row:
        return [runs_of([(r, c) in ms for c in range(n)]) for r in range(n)]
    return [runs_of([(r, c) in ms for r in range(n)]) for c in range(n)]


# ---------------------------------------------------------------- A. 数据自洽
def part_a():
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    fails, recs = [], []
    if len(levels) != 10:
        fails.append("关卡数=%d（期望 10）" % len(levels))
    if [lv.get("id") for lv in levels] != list(range(1, len(levels) + 1)):
        fails.append("id 不是 1..N：%s" % [lv.get("id") for lv in levels])
    seen_theme = set()
    for lv in levels:
        n = lv["size"]
        stars = lv.get("theme", {}).get("stars") or []
        lines = lv.get("theme", {}).get("lines") or []
        noise = lv.get("noise") or []
        star_rc = [tuple(s["rc"]) for s in stars]
        noise_rc = [tuple(x) for x in noise]
        mines = {tuple(x) for x in lv["mines"]}
        errs = []
        # mines = stars ∪ noise（逐项）
        if len(mines) != len(lv["mines"]):
            errs.append("mines 有重复坐标")
        if len(set(star_rc)) != len(star_rc):
            errs.append("theme.stars 有重复坐标")
        if len(set(noise_rc)) != len(noise_rc):
            errs.append("noise 有重复坐标")
        inter = set(star_rc) & set(noise_rc)
        if inter:
            errs.append("noise 与 theme.stars 重叠：%s" % sorted(inter))
        if set(star_rc) | set(noise_rc) != mines:
            errs.append("mines != theme.stars ∪ noise（星星∪杂星=%d，mines=%d，差集 mine-(s∪n)=%s, (s∪n)-mine=%s）" % (
                len(set(star_rc) | set(noise_rc)), len(mines),
                sorted(mines - (set(star_rc) | set(noise_rc)))[:6],
                sorted((set(star_rc) | set(noise_rc)) - mines)[:6]))
        for rc in star_rc + noise_rc:
            if not (0 <= rc[0] < n and 0 <= rc[1] < n):
                errs.append("坐标越界 %s" % (rc,))
        # 线索
        er, ec = expected_runs(lv, True), expected_runs(lv, False)
        if [list(x) for x in lv["rowRuns"]] != er:
            errs.append("rowRuns 与 mines 不一致")
        if [list(x) for x in lv["colRuns"]] != ec:
            errs.append("colRuns 与 mines 不一致")
        if sum(sum(x) for x in lv["rowRuns"]) != len(mines):
            errs.append("rowRuns 数字和 != 雷数")
        if sum(sum(x) for x in lv["colRuns"]) != len(mines):
            errs.append("colRuns 数字和 != 雷数")
        # opening
        op = tuple(lv["opening"])
        ctx = Ctx(lv)
        if op in mines:
            errs.append("opening 是雷")
        elif ctx.counts[op[0] * n + op[1]] != 0:
            errs.append("opening 邻域雷数 != 0")
        # 关卡参数
        if lv.get("lives") != 3:
            errs.append("lives != 3")
        want_runs = lv["id"] >= 2
        if bool(lv["showRuns"]) != want_runs:
            errs.append("showRuns=%r（要求 L1 false、L2-10 true）" % lv["showRuns"])
        # theme 完整性
        th = lv.get("theme") or {}
        for k in ("id", "name", "nameEn", "fact"):
            if not isinstance(th.get(k), str) or not th.get(k).strip():
                errs.append("theme.%s 缺失/空" % k)
        if th.get("id") in seen_theme:
            errs.append("theme.id 重复：%r" % th.get("id"))
        seen_theme.add(th.get("id"))
        if not stars:
            errs.append("theme.stars 为空")
        for i, s in enumerate(stars):
            for k in ("name", "en"):
                if not isinstance(s.get(k), str) or not s.get(k).strip():
                    errs.append("stars[%d].%s 缺失/空" % (i, k))
            if not isinstance(s.get("mag"), (int, float)):
                errs.append("stars[%d].mag 非数字" % i)
        bad_lines = [seg for seg in lines
                     if not (isinstance(seg, list) and len(seg) == 2
                             and all(isinstance(x, int) and 0 <= x < len(stars) for x in seg))]
        if bad_lines:
            errs.append("theme.lines 引用越界：%s" % bad_lines[:4])
        if len(lines) != max(0, len(stars) - 1) and lines:
            # 连线数通常为「星数-1」或形成闭环；仅提示，不算错
            pass
        if lv.get("technique") != "constellation":
            errs.append("technique=%r（v0.7 期望 constellation）" % lv.get("technique"))
        recs.append({"id": lv["id"], "name": lv["name"], "size": n, "mines": len(mines),
                     "stars": len(stars), "lines": len(lines), "noise": len(noise),
                     "showRuns": lv["showRuns"], "opening": list(op),
                     "opening_flood": len(ctx.revealed), "teach_nonempty": bool(lv.get("teach")),
                     "theme": th.get("nameEn"), "errors": errs})
        fails.extend("第%d关: %s" % (lv["id"], e) for e in errs)

    # 内嵌 LEVELS == levels.json
    html = DIST_HTML.read_text(encoding="utf-8")
    m = re.search(r"/\*\s*LEVELS_INJECT_START\s*\*/\s*const LEVELS\s*=\s*(\[.*?\]);\s*/\*\s*LEVELS_INJECT_END\s*\*/", html, re.S)
    embedded_equal, emb_count = False, None
    if not m:
        fails.append("dist HTML 找不到 LEVELS_INJECT 块")
    else:
        emb = json.loads(m.group(1))
        emb_count = len(emb)
        embedded_equal = emb == levels
        if not embedded_equal:
            fails.append("内嵌 LEVELS != tools/levels.json")
    # 外壳可复现
    pat = re.compile(r"/\*\s*LEVELS_INJECT_START\s*\*/.*?/\*\s*LEVELS_INJECT_END\s*\*/", re.S)
    shell_same = False
    if GAME_HTML.is_file():
        shell_dist = pat.sub("@@LEVELS@@", html, count=1)
        shell_game = pat.sub("@@LEVELS@@", GAME_HTML.read_text(encoding="utf-8"), count=1)
        shell_same = shell_game == shell_dist
        if not shell_same:
            fails.append("game/index.html 外壳（去 LEVELS 块）与 dist 外壳不相等")
    out = {"levels_file": str(LEVELS_JSON), "dist": str(DIST_HTML),
           "level_count": len(levels), "embedded_count": emb_count,
           "embedded_equal": embedded_equal, "shell_same": shell_same,
           "per_level": recs, "fails": fails,
           "verdict": "PASS" if not fails else "FAIL"}
    print("== A. 数据自洽（v0.7：mines = theme.stars ∪ noise） ==")
    print("关卡数=%d ｜ 内嵌 LEVELS==文件: %s ｜ game 外壳==dist 外壳: %s" % (
        len(levels), embedded_equal, shell_same))
    for r in recs:
        print("  第%2d关 %s %2dx%2d 星%2d+杂%2d=雷%2d 线%2d showRuns=%-5s 开局展开%2d teach=%s %s" % (
            r["id"], r["theme"], r["size"], r["size"], r["stars"], r["noise"], r["mines"],
            r["lines"], r["showRuns"], r["opening_flood"], "有" if r["teach_nonempty"] else "无",
            "OK" if not r["errors"] else "FAIL:" + "; ".join(r["errors"])))
    print("A 判定: %s（失败项 %d）" % (out["verdict"], len(fails)))
    (ROOT / "verification" / "t14_out_a.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------- B. 求解器
class Solver:
    def __init__(self, lv, use_runs):
        self.lv = lv
        self.n = n = lv["size"]
        self.total = n * n
        self.mines = {r * n + c for r, c in lv["mines"]}
        self.nbrs = nbrs_list(n)
        self.counts = [sum(1 for j in self.nbrs[i] if j in self.mines) for i in range(self.total)]
        self.use_runs = use_runs and bool(lv.get("showRuns"))
        self.revealed = set()
        self.known = set()
        self.steps = []
        self.probes = 0
        self.stall = False
        self.contradiction = None
        self._flood(lv["opening"][0] * n + lv["opening"][1])

    def _flood(self, start):
        st = [start]
        while st:
            i = st.pop()
            if i in self.revealed or i in self.mines:
                continue
            self.revealed.add(i)
            if self.counts[i] == 0:
                for j in self.nbrs[i]:
                    if j not in self.revealed and j not in self.mines:
                        st.append(j)

    def solved(self):
        return len(self.revealed) + len(self.known) == self.total

    def step_a(self):
        for i in sorted(self.revealed):
            unknown = [j for j in self.nbrs[i] if j not in self.revealed and j not in self.known]
            if not unknown:
                continue
            k = sum(1 for j in self.nbrs[i] if j in self.known)
            c = self.counts[i]
            if c == k:
                return ("safe", unknown[0])
            if c - k == len(unknown):
                return ("mine", unknown[0])
        return None

    def line_patterns(self, cells, clue):
        n = len(cells)
        pats = []
        for mask in range(1 << n):
            bits = [(mask >> i) & 1 for i in range(n)]
            if runs_of(bits) != list(clue):
                continue
            ok = True
            for pos, idx in enumerate(cells):
                b = bits[pos]
                if idx in self.revealed and b:
                    ok = False
                    break
                if idx in self.known and not b:
                    ok = False
                    break
            if ok:
                pats.append(bits)
        return pats

    def step_b(self):
        lines, clues = [], []
        for r in range(self.n):
            lines.append([r * self.n + c for c in range(self.n)])
            clues.append(list(self.lv["rowRuns"][r]))
        for c in range(self.n):
            lines.append([r * self.n + c for r in range(self.n)])
            clues.append(list(self.lv["colRuns"][c]))
        for cells, clue in zip(lines, clues):
            pats = self.line_patterns(cells, clue)
            if not pats:
                self.contradiction = "线索 %s 无相容摆放" % (clue,)
                return None
            for pos, idx in enumerate(cells):
                if idx in self.revealed or idx in self.known:
                    continue
                vals = [p[pos] for p in pats]
                if all(vals):
                    return ("mine", idx)
                if not any(vals):
                    return ("safe", idx)
        return None

    def apply(self, kind, idx, tag):
        if kind == "mine":
            if idx in self.revealed:
                self.contradiction = "把已翻开格标成雷 #%d" % idx
                return False
            self.known.add(idx)
        else:
            if idx in self.known:
                self.contradiction = "探开已标雷格 #%d" % idx
                return False
            self._flood(idx)
            self.probes += 1
        self.steps.append({"tag": tag, "act": kind, "r": idx // self.n, "c": idx % self.n})
        return True

    def run(self, max_steps=50000):
        while not self.solved():
            if len(self.steps) >= max_steps:
                self.stall = True
                break
            act = self.step_a()
            tag = "A"
            if act is None and self.use_runs:
                act = self.step_b()
                tag = "B"
            if act is None:
                self.stall = True
                break
            if not self.apply(act[0], act[1], tag):
                break
        return {"solved": self.solved() and not self.contradiction,
                "stalled": self.stall, "contradiction": self.contradiction,
                "a_steps": sum(1 for s in self.steps if s["tag"] == "A"),
                "b_steps": sum(1 for s in self.steps if s["tag"] == "B"),
                "probes": self.probes, "steps_total": len(self.steps),
                "revealed_at_end": len(self.revealed), "known_mines_at_end": len(self.known),
                "remaining": self.total - len(self.revealed) - len(self.known),
                "steps": self.steps}


def parse_targets():
    """从 fit_constellation_levels.py 的 PLAN 里读目标 board / probes 带（只读解析，不 copy 代码）。"""
    text = FIT_PY.read_text(encoding="utf-8")
    out = {}
    for m in re.finditer(r"dict\(\s*lid=(\d+),\s*zh=\"([^\"]+)\",\s*en=\"([^\"]+)\",[^)]*?board=(\d+),\s*probes=\((\d+),\s*(\d+)\)", text, re.S):
        out[int(m.group(1))] = {"zh": m.group(2), "en": m.group(3), "board": int(m.group(4)),
                                "probe_lo": int(m.group(5)), "probe_hi": int(m.group(6))}
    return out


def part_bd():
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    targets = parse_targets()
    out = {"levels": [], "fails": [], "targets": targets}
    seqs = {}
    print("== B/D. 零猜测可解性 + 难度指标（开局展开占比 / 0 格占比 / 探格 vs 目标带） ==")
    print("求解器：A=邻域计数传播；B=行/列连续块 2^n 全枚举；每步落实一条推理；flood fill 同 UI。")
    for lv in levels:
        lid, n = lv["id"], lv["size"]
        ctx = Ctx(lv)
        total = n * n
        mines = ctx.mines
        zeros = sum(1 for i in range(total) if i not in mines and ctx.counts[i] == 0)
        safe = total - len(mines)
        open_ratio = len(ctx.revealed) / total
        zero_ratio = zeros / safe if safe else 1.0
        a_only = Solver(lv, use_runs=False).run()
        full = Solver(lv, use_runs=True).run()
        tgt = targets.get(lid)
        probes = full["probes"]
        band_ok = bool(tgt and tgt["probe_lo"] <= probes <= tgt["probe_hi"])
        rec = {
            "id": lid, "size": n, "mines": len(mines), "stars": len(lv["theme"]["stars"]),
            "lines": len(lv["theme"]["lines"]), "noise": len(lv["noise"]),
            "opening_flood": len(ctx.revealed), "opening_ratio": round(open_ratio, 4),
            "zero_cells": zeros, "zero_ratio_safe": round(zero_ratio, 4),
            "probes": probes, "target_band": [tgt["probe_lo"], tgt["probe_hi"]] if tgt else None,
            "probes_in_band": band_ok,
            "a_only_solved": a_only["solved"], "a_only_stalled": a_only["stalled"],
            "full_solved": full["solved"], "contradiction": full["contradiction"],
            "a_steps": full["a_steps"], "b_steps": full["b_steps"],
            "steps_total": full["steps_total"],
        }
        issues = []
        if not full["solved"]:
            issues.append("全推理未能通关")
        if not a_only["solved"] and lid == 1:
            issues.append("第1关仅邻域推理未能通关（教学意图要求可通）")
        if open_ratio > 0.38:
            issues.append("开局展开占比 %.1f%% > 38%%" % (open_ratio * 100))
        if zero_ratio > 0.36:
            issues.append("0 格占安全格 %.1f%% 偏大" % (zero_ratio * 100))
        rec["issues"] = issues
        out["fails"].extend("第%d关: %s" % (lid, x) for x in issues)
        seqs[str(lid)] = [{"act": s["act"], "r": s["r"], "c": s["c"]} for s in full["steps"]]
        out["levels"].append(rec)
        print("  第%2d关 %2dx%2d 雷%2d(星%2d+杂%2d) ｜ 仅邻域:%-6s 全推理:%-5s(A%2d/B%2d) ｜ "
              "开局展开%2d/%2d=%4.1f%% 0格%2d/%2d=%4.1f%% 探格%2d 目标%s %s %s" % (
                  lid, n, n, len(mines), len(lv["theme"]["stars"]), len(lv["noise"]),
                  "通关" if a_only["solved"] else "卡住", "通关" if full["solved"] else "卡住",
                  full["a_steps"], full["b_steps"], len(ctx.revealed), total, open_ratio * 100,
                  zeros, safe, zero_ratio * 100, probes,
                  "%s-%s" % (tgt["probe_lo"], tgt["probe_hi"]) if tgt else "?",
                  "✓" if band_ok else "✗", "" if not issues else "ISSUE:" + ";".join(issues)))
    out["verdict"] = "PASS" if not out["fails"] else "FAIL"
    print("B/D 判定: %s（问题项 %d）" % (out["verdict"], len(out["fails"])))
    (ROOT / "verification" / "t14_out_bd.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "verification" / "t14_play_sequences.json").write_text(
        json.dumps(seqs, ensure_ascii=False, indent=2), encoding="utf-8")
    print("动作序列 -> verification/t14_play_sequences.json")
    return out


if __name__ == "__main__":
    a = part_a()
    bd = part_bd()
    sys.exit(0 if (a["verdict"] == "PASS" and bd["verdict"] == "PASS") else 1)