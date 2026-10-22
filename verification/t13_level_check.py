#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T13 独立复核 · 关卡层（A 数据自洽 / B 零猜测可解与教学带 / C 开局相容方案数）
- 完全自写：不 import、不复制 tools/generate_levels.py；
- 数据源默认 tools/levels.json + dist/冉政-游戏本体/index.html 内嵌 LEVELS；
- 用法：
    python verification/t13_level_check.py a
    python verification/t13_level_check.py b
    python verification/t13_level_check.py c
    python verification/t13_level_check.py all
- 输出：stdout 日志 + verification/t13_out_a.json / t13_out_b.json / t13_out_c.json
        B 另写出 verification/t13_play_sequences.json（供 D 的 DOM 桩使用）
"""
import itertools
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS_JSON = Path(os.environ.get("T13_LEVELS", ROOT / "tools" / "levels.json"))
DIST_HTML = Path(os.environ.get("T13_DIST", ROOT / "dist" / "冉政-游戏本体" / "index.html"))
GAME_HTML = Path(os.environ.get("T13_GAME", ROOT / "game" / "index.html"))
OUTDIR = ROOT / "verification"


def load_levels():
    return json.loads(LEVELS_JSON.read_text(encoding="utf-8"))


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


def bits_of_mask(mask, n):
    return [(mask >> i) & 1 for i in range(n)]


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
        # 开局 flood fill
        self.revealed = set()
        self._flood(self.lv["opening"][0] * n + self.lv["opening"][1])

    def _flood(self, start):
        if start in self.mines or start in self.revealed:
            return
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

    def rowruns_expected(self):
        return [runs_of([(r, c) in {(x // self.n, x % self.n) for x in self.mines}
                         for c in range(self.n)]) for r in range(self.n)]


def expected_row_runs(lv):
    n = lv["size"]
    ms = {(r, c) for r, c in lv["mines"]}
    return [runs_of([(r, c) in ms for c in range(n)]) for r in range(n)]


def expected_col_runs(lv):
    n = lv["size"]
    ms = {(r, c) for r, c in lv["mines"]}
    return [runs_of([(r, c) in ms for r in range(n)]) for c in range(n)]


# ---------------------------------------------------------------- A. 数据自洽
def part_a():
    levels = load_levels()
    recs, fails = [], []
    if len(levels) != 10:
        fails.append("关卡数=%d（期望 10）" % len(levels))
    ids = [lv.get("id") for lv in levels]
    if ids != list(range(1, len(levels) + 1)):
        fails.append("id 序列不是 1..N：%s" % ids)
    for lv in levels:
        n = lv["size"]
        ms = {(r, c) for r, c in lv["mines"]}
        r = {"id": lv["id"], "size": n, "mines": len(ms), "showRuns": lv["showRuns"],
             "teach_nonempty": bool(lv.get("teach")), "errors": []}
        if len(ms) != len(lv["mines"]):
            r["errors"].append("mines 有重复坐标")
        if any(not (0 <= x < n and 0 <= y < n) for x, y in ms):
            r["errors"].append("mines 越界")
        er, ec = expected_row_runs(lv), expected_col_runs(lv)
        if [list(x) for x in lv["rowRuns"]] != er:
            r["errors"].append("rowRuns 与 mines 不一致：声明=%s 实测=%s" % (lv["rowRuns"], er))
        if [list(x) for x in lv["colRuns"]] != ec:
            r["errors"].append("colRuns 与 mines 不一致：声明=%s 实测=%s" % (lv["colRuns"], ec))
        # 线索数字和 == 雷数（逐行/逐列分别成立 => 全盘和成立）
        if sum(sum(x) for x in lv["rowRuns"]) != len(ms):
            r["errors"].append("rowRuns 数字和 != 雷数")
        if sum(sum(x) for x in lv["colRuns"]) != len(ms):
            r["errors"].append("colRuns 数字和 != 雷数")
        op = tuple(lv["opening"])
        if op in ms:
            r["errors"].append("opening 是雷")
        ctx = Ctx(lv)
        if ctx.counts[op[0] * n + op[1]] != 0:
            r["errors"].append("opening 邻域雷数=%d != 0" % ctx.counts[op[0] * n + op[1]])
        r["opening_flood_size"] = len(ctx.revealed)
        if len(ctx.revealed) < 5:
            r["errors"].append("开局展开 %d 格 < 5（SPEC §5 生成器交付标准）" % len(ctx.revealed))
        if lv.get("lives") != 3:
            r["errors"].append("lives=%r != 3" % lv.get("lives"))
        want_runs = lv["id"] >= 2
        if bool(lv["showRuns"]) != want_runs:
            r["errors"].append("showRuns=%r；按 v0.3 要求第 1 关 false、第 2-10 关 true" % lv["showRuns"])
        if r["errors"]:
            fails.extend("第%d关: %s" % (lv["id"], e) for e in r["errors"])
        recs.append(r)

    # 内嵌 LEVELS == levels.json
    html = DIST_HTML.read_text(encoding="utf-8")
    m = re.search(r"/\*\s*LEVELS_INJECT_START\s*\*/\s*const LEVELS\s*=\s*(\[.*?\]);\s*/\*\s*LEVELS_INJECT_END\s*\*/", html, re.S)
    embedded_equal = False
    embedded_count = None
    if not m:
        fails.append("dist HTML 中找不到 LEVELS_INJECT 块")
    else:
        try:
            emb = json.loads(m.group(1))
            embedded_count = len(emb)
            embedded_equal = (emb == levels)
            if not embedded_equal:
                fails.append("内嵌 LEVELS 与 tools/levels.json 不相等")
        except Exception as e:  # noqa
            fails.append("内嵌 LEVELS JSON 解析失败：%r" % (e,))

    # game 外壳 + 注入 == dist（构建可复现性）
    pat = re.compile(r"/\*\s*LEVELS_INJECT_START\s*\*/.*?/\*\s*LEVELS_INJECT_END\s*\*/", re.S)
    shell_src = GAME_HTML.read_text(encoding="utf-8")
    shell_dist = pat.sub("@@LEVELS@@", html, count=1)
    shell_game = pat.sub("@@LEVELS@@", shell_src, count=1)
    shell_equal = (shell_game == shell_dist)
    if not shell_equal:
        fails.append("game/index.html 外壳（去掉 LEVELS 块后）与 dist HTML 不相等：构建可能未基于当前外壳")

    out = {"levels_file": str(LEVELS_JSON), "level_count": len(levels),
           "embedded_levels_count": embedded_count, "embedded_levels_equal": embedded_equal,
           "shell_equal_modulo_levels": shell_equal,
           "per_level": recs, "fails": fails,
           "verdict": "PASS" if not fails else "FAIL"}
    print("== A. 关卡数据自洽 ==")
    print("数据源: %s" % LEVELS_JSON)
    print("关卡数=%d ｜ 内嵌 LEVELS==levels.json: %s ｜ game 外壳==dist 外壳: %s" % (
        len(levels), embedded_equal, shell_equal))
    for r in recs:
        print("  第%2d关 %dx%d 雷%2d showRuns=%-5s 开局展开%2d 格 teach=%s %s" % (
            r["id"], r["size"], r["size"], r["mines"], r["showRuns"],
            r["opening_flood_size"], "有" if r["teach_nonempty"] else "无",
            "OK" if not r["errors"] else "FAIL:" + "; ".join(r["errors"])))
    print("A 判定: %s（失败项 %d）" % (out["verdict"], len(fails)))
    (OUTDIR / "t13_out_a.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


# ---------------------------------------------------------------- B. 求解器
class Solver:
    """模拟零猜测玩家：邻域计数传播 (A) + 数织行/列全枚举 (B)。每步只落实一条推理。"""

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
        if start in self.mines or start in self.revealed:
            return
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
        """返回 (kind, idx)；kind in {'mine','safe'}；A 规则：数字 == 已标雷 + 未知 => 未知全雷；数字 == 已标雷 => 未知全安全。"""
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
        """暴力枚举整行/列 2^n 种摆放（显然正确），过滤线索与已知状态。"""
        n = len(cells)
        pats = []
        for mask in range(1 << n):
            bits = bits_of_mask(mask, n)
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
        lines = []
        for r in range(self.n):
            lines.append([r * self.n + c for c in range(self.n)])
        for c in range(self.n):
            lines.append([r * self.n + c for r in range(self.n)])
        clues = [list(x) for x in self.lv["rowRuns"]] + [list(x) for x in self.lv["colRuns"]]
        for cells, clue in zip(lines, clues):
            pats = self.line_patterns(cells, clue)
            if not pats:
                self.contradiction = "线索 %s 在已知状态下无任何相容摆放" % (clue,)
                return None
            for pos, idx in enumerate(cells):
                vals = [p[pos] for p in pats]
                if idx in self.revealed or idx in self.known:
                    continue
                if all(vals):
                    return ("mine", idx)
                if not any(vals):
                    return ("safe", idx)
        return None

    def apply(self, kind, idx, tag):
        if kind == "mine":
            if idx in self.revealed:
                self.contradiction = "试图把已翻开的安全格标成雷 #%d" % idx
                return False
            self.known.add(idx)
        else:
            if idx in self.known:
                self.contradiction = "试图探开已标为雷的格 #%d" % idx
                return False
            self._flood(idx)
            self.probes += 1
        self.steps.append({"tag": tag, "act": kind, "r": idx // self.n, "c": idx % self.n})
        return True

    def run(self, max_steps=20000):
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
        return {
            "solved": self.solved() and not self.contradiction,
            "stalled": self.stall,
            "contradiction": self.contradiction,
            "a_steps": sum(1 for s in self.steps if s["tag"] == "A"),
            "b_steps": sum(1 for s in self.steps if s["tag"] == "B"),
            "probes": self.probes,
            "steps_total": len(self.steps),
            "revealed_at_end": len(self.revealed),
            "known_mines_at_end": len(self.known),
            "remaining": self.total - len(self.revealed) - len(self.known),
            "b_mines": sum(1 for s in self.steps if s["tag"] == "B" and s["act"] == "mine"),
            "b_digs": sum(1 for s in self.steps if s["tag"] == "B" and s["act"] == "safe"),
            "steps": self.steps,
        }


def part_b():
    levels = load_levels()
    out = {"levels": [], "fails": []}
    seqs = {}
    print("== B. 零猜测可解性 + 教学带意图 ==")
    print("求解器：A=邻域计数传播；B=行/列连续块全枚举（2^n 暴力，显然正确）；每步落实一条推理。")
    for lv in levels:
        a_only = Solver(lv, use_runs=False).run()
        full = Solver(lv, use_runs=True).run()
        n = lv["size"]
        rec = {"id": lv["id"], "showRuns": lv["showRuns"],
               "a_only_solved": a_only["solved"], "a_only_stalled": a_only["stalled"],
               "a_only_remaining": a_only["remaining"],
               "full_solved": full["solved"], "full_stalled": full["stalled"],
               "contradiction": full["contradiction"],
               "b_steps": full["b_steps"], "a_steps": full["a_steps"], "probes": full["probes"],
               "b_mines": full["b_mines"], "b_digs": full["b_digs"],
               "full_steps_total": full["steps_total"]}
        # 教学带意图
        if lv["id"] == 1:
            rec["intent_ok"] = bool(a_only["solved"]) and full["b_steps"] == 0 and a_only["b_steps"] == 0
        else:
            rec["intent_ok"] = (not a_only["solved"]) and full["solved"] and full["b_steps"] > 0
        rec["b_contribution_ge_5"] = (full["b_steps"] >= 5)
        if not rec["intent_ok"]:
            out["fails"].append("第%d关教学带意图不满足：a_only_solved=%s full_solved=%s b_steps=%d" % (
                lv["id"], a_only["solved"], full["solved"], full["b_steps"]))
        if lv["id"] == 2 and not rec["b_contribution_ge_5"]:
            out["fails"].append("第2关数织贡献=%d < 5" % full["b_steps"])
        # D 用序列：mine -> flag, safe -> dig（需从未翻开格开始；dig 已翻开格时 UI 会忽略，序列仍安全）
        seqs[str(lv["id"])] = [{"act": s["act"], "r": s["r"], "c": s["c"]} for s in full["steps"]]
        out["levels"].append(rec)
        print("  第%2d关 %dx%d showRuns=%-5s 仅邻域:%-6s 全推理:%-5s | A步%2d B步%2d(雷%2d/探%2d) 探格%2d 总步%2d | 意图:%s" % (
            lv["id"], n, n, lv["showRuns"],
            "通关" if a_only["solved"] else "卡住",
            "通关" if full["solved"] else "卡住",
            full["a_steps"], full["b_steps"], full["b_mines"], full["b_digs"],
            full["probes"], full["steps_total"], "OK" if rec["intent_ok"] else "FAIL"))
        if a_only["solved"] is False:
            print("      仅邻域卡住时：已翻开 %d、已标雷 %d、剩余 %d 格" % (
                a_only["revealed_at_end"], a_only["known_mines_at_end"], a_only["remaining"]))
    out["verdict"] = "PASS" if not out["fails"] else "FAIL"
    print("B 判定: %s（失败项 %d）" % (out["verdict"], len(out["fails"])))
    (OUTDIR / "t13_out_b.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTDIR / "t13_play_sequences.json").write_text(json.dumps(seqs, ensure_ascii=False, indent=2), encoding="utf-8")
    print("动作序列 -> verification/t13_play_sequences.json")
    return out


# ---------------------------------------------------------------- C. 相容方案数
def row_options_for(ctx, lv, r):
    """第 r 行所有与 rowRuns 相容、且开局已翻开格不能是雷的行模式。"""
    n = ctx.n
    opts = []
    for mask in range(1 << n):
        bits = bits_of_mask(mask, n)
        if runs_of(bits) != list(lv["rowRuns"][r]):
            continue
        if any(bits[c] and (r * n + c) in ctx.revealed for c in range(n)):
            continue
        opts.append(mask)
    return opts


def count_compatible(level, budget_s=120.0):
    """开局可见线索（开局翻开格的数字 + 雷总数 + showRuns 时的行列连续块）下的完整布雷方案数。
    方法：逐行 DFS；列线索用“允许列模式前缀”剪枝；可见格数字在邻域行全部落定后即时校验。
    """
    t0 = time.monotonic()
    n = level["size"]
    total = n * n
    ctx = Ctx(level)               # ctx.revealed = opening flood 区域
    visible = ctx.revealed
    true_mines = ctx.mines
    counts = ctx.counts
    nbrs = ctx.nbrs
    M = len(true_mines)
    runs_on = bool(level["showRuns"])

    if not runs_on:
        # 与旧实现一致：未知格自由组合 + 可见数字校验（显然正确）
        unknown = [i for i in range(total) if i not in visible]
        cnt = 0
        nodes = 0
        for combo in itertools.combinations(unknown, M):
            nodes += 1
            if time.monotonic() - t0 > budget_s:
                return {"solutions": cnt, "timeout": True, "nodes": nodes,
                        "elapsed_s": round(time.monotonic() - t0, 2), "method": "comb"}
            ms = set(combo)
            ok = True
            for v in visible:
                if sum(1 for j in nbrs[v] if j in ms) != counts[v]:
                    ok = False
                    break
            if ok:
                cnt += 1
        return {"solutions": cnt, "timeout": False, "nodes": nodes,
                "elapsed_s": round(time.monotonic() - t0, 2), "method": "comb"}

    row_opts = [row_options_for(ctx, level, r) for r in range(n)]
    if any(not o for o in row_opts):
        return {"solutions": 0, "timeout": False, "nodes": 0,
                "elapsed_s": 0, "method": "rowdfs", "note": "某行无相容模式"}
    # 列允许模式 + 前缀集合
    col_pats = []
    for c in range(n):
        pats = []
        for mask in range(1 << n):
            bits = bits_of_mask(mask, n)
            if runs_of(bits) != list(level["colRuns"][c]):
                continue
            if any(bits[r] and (r * n + c) in visible for r in range(n)):
                continue
            pats.append(mask)
        col_pats.append(pats)
    # prefixes[c][d] = 前 d 行构成的掩码集合（用于剪枝）
    prefixes = []
    for c in range(n):
        ps = [set() for _ in range(n + 1)]
        for mask in col_pats[c]:
            pref = 0
            ps[0].add(0)
            for d in range(1, n + 1):
                if (mask >> (d - 1)) & 1:
                    pref |= (1 << (d - 1))
                ps[d].add(pref)
        prefixes.append(ps)

    colbits = [0] * n
    nodes = [0]
    cnt = [0]
    timed_out = [False]

    # 可见格按“最晚需要的行”分组：当 r+1 > max(vr)+1？ 邻域行 max = min(vr+1, n-1)；需全部行落定即 <= r
    checks_after_row = [[] for _ in range(n)]
    for v in visible:
        vr, vc = divmod(v, n)
        last = min(vr + 1, n - 1)
        checks_after_row[last].append(v)

    def numbers_upto(r):
        for idx in checks_after_row[r]:
            m = 0
            for j in nbrs[idx]:
                jr = j // n
                if jr <= r and (colbits[j % n] >> jr) & 1:
                    m += 1
            if m != counts[idx]:
                return False
        return True

    def dfs(r):
        if timed_out[0]:
            return
        if time.monotonic() - t0 > budget_s:
            timed_out[0] = True
            return
        if r == n:
            # 最终再核一遍所有可见格数字（防御性）
            for v in visible:
                if sum(1 for j in nbrs[v] if (colbits[j % n] >> (j // n)) & 1) != counts[v]:
                    return
            cnt[0] += 1
            return
        for mask in row_opts[r]:
            nodes[0] += 1
            if nodes[0] % 4096 == 0 and time.monotonic() - t0 > budget_s:
                timed_out[0] = True
                return
            ok = True
            for c in range(n):
                colbits[c] |= ((mask >> c) & 1) << r
            for c in range(n):
                if colbits[c] not in prefixes[c][r + 1]:
                    ok = False
                    break
            if ok and numbers_upto(r):
                dfs(r + 1)
            for c in range(n):
                colbits[c] &= ~(1 << r)
            if timed_out[0]:
                return

    dfs(0)
    return {"solutions": cnt[0], "timeout": timed_out[0], "nodes": nodes[0],
            "elapsed_s": round(time.monotonic() - t0, 2), "method": "rowdfs"}


def part_c(budget=120.0):
    levels = load_levels()
    out = {"budget_s": budget, "levels": [], "fails": []}
    print("== C. 开局相容方案数（可见数字 + 雷总数 [+ 行列连续块]）==")
    for lv in levels:
        res = count_compatible(lv, budget)
        # 真布局自检：真实 mines 必须满足全部约束（否则枚举/剪枝有漏解 bug）
        ctx = Ctx(lv)
        true_ok = all(sum(1 for j in ctx.nbrs[v] if j in ctx.mines) == ctx.counts[v]
                      for v in ctx.revealed)
        rec = {"id": lv["id"], "showRuns": lv["showRuns"], "revealed_at_start": len(ctx.revealed),
               "true_layout_valid": true_ok, **res}
        if not true_ok:
            out["fails"].append("第%d关真实布局不满足开局可见数字约束（枚举不可信）" % lv["id"])
        if res.get("timeout"):
            out["fails"].append("第%d关计数超预算（未判定）" % lv["id"])
        if res.get("solutions") is not None and res.get("solutions") < 1:
            out["fails"].append("第%d关解数 <1（不合理）" % lv["id"])
        out["levels"].append(rec)
        print("  第%2d关 showRuns=%-5s 开局可见%2d格 ｜ 解数=%s%s 节点=%s 用时=%ss 真布局合法=%s" % (
            lv["id"], lv["showRuns"], len(ctx.revealed),
            res.get("solutions"), "（未判定/超时）" if res.get("timeout") else "",
            res.get("nodes"), res.get("elapsed_s"), true_ok))
    out["verdict"] = "PASS" if not out["fails"] else "FAIL"
    print("C 判定: %s（失败项 %d）" % (out["verdict"], len(out["fails"])))
    (OUTDIR / "t13_out_c.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode in ("a", "all"):
        part_a()
    if mode in ("b", "all"):
        part_b()
    if mode in ("c", "all"):
        part_c(float(os.environ.get("T13_C_BUDGET", "120")))


if __name__ == "__main__":
    main()