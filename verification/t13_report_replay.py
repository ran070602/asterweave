#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T13 独立复核 · 报告推理序列逐步重放（对应 tools/report.md §1 每关的逐步序列）。
思路同 report_t11.md §13 的教训：用「暴力全枚举」这一显然正确的实现重放，
而不是复用任何求解器剪枝实现；每条打印步骤都必须能由它自己声明的那类规则推出。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "tools" / "report.md"
LEVELS = ROOT / "tools" / "levels.json"


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


class Replay:
    def __init__(self, lv):
        self.lv = lv
        self.n = n = lv["size"]
        self.total = n * n
        self.mines = {r * n + c for r, c in lv["mines"]}
        self.nbrs = nbrs_list(n)
        self.counts = [sum(1 for j in self.nbrs[i] if j in self.mines) for i in range(self.total)]
        self.revealed = set()
        self.known = set()
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

    def forced_by_neighbor(self, idx):
        """在“某一条邻域数字规则”下 idx 是否被强制为雷/安全。"""
        for i in sorted(self.revealed):
            unknown = [j for j in self.nbrs[i] if j not in self.revealed and j not in self.known]
            if idx not in unknown:
                continue
            k = sum(1 for j in self.nbrs[i] if j in self.known)
            c = self.counts[i]
            if c - k == len(unknown):
                return "mine"
            if c == k:
                return "safe"
        return None

    def forced_by_runs(self, idx):
        n = self.n
        lines, clues = [], []
        for r in range(n):
            lines.append([r * n + c for c in range(n)])
            clues.append(list(self.lv["rowRuns"][r]))
        for c in range(n):
            lines.append([r * n + c for r in range(n)])
            clues.append(list(self.lv["colRuns"][c]))
        for cells, clue in zip(lines, clues):
            if idx not in cells:
                continue
            pos = cells.index(idx)
            pats = []
            for mask in range(1 << n):
                bits = [(mask >> t) & 1 for t in range(n)]
                if runs_of(bits) != clue:
                    continue
                ok = True
                for t, j in enumerate(cells):
                    if j in self.revealed and bits[t]:
                        ok = False
                        break
                    if j in self.known and not bits[t]:
                        ok = False
                        break
                if ok:
                    pats.append(bits)
            vals = [p[pos] for p in pats]
            if vals and all(vals):
                return "mine"
            if vals and not any(vals):
                return "safe"
        return None

    def apply(self, idx, kind):
        if kind == "mine":
            if idx in self.revealed:
                return False
            self.known.add(idx)
        else:
            if idx in self.known or idx in self.mines:
                return False
            self._flood(idx)
        return True


STEP_RE = re.compile(r"^\s*-\s*(\d+)\.\s*\[(邻域|连续块)\]\s*(判定雷|探开安全格)\s*\((\d+),(\d+)\)\s*$")


def parse_sequences():
    text = REPORT.read_text(encoding="utf-8")
    secs = re.split(r"\n### 第 (\d+) 关", text)
    out = {}
    for i in range(1, len(secs), 2):
        lid = int(secs[i])
        body = secs[i + 1]
        steps = []
        for line in body.splitlines():
            m = STEP_RE.match(line)
            if m:
                steps.append({"no": int(m.group(1)), "tag": m.group(2),
                              "act": "mine" if m.group(3) == "判定雷" else "safe",
                              "r": int(m.group(4)) - 1, "c": int(m.group(5)) - 1})
        out[lid] = steps
    return out


def main():
    levels = json.loads(LEVELS.read_text(encoding="utf-8"))
    seqs = parse_sequences()
    fails = []
    print("== 重放 tools/report.md 的逐关推理序列（干净暴力枚举，逐步验证“声明的规则确实强制该格”） ==")
    for lv in levels:
        lid = lv["id"]
        steps = seqs.get(lid) or []
        rp = Replay(lv)
        bad = None
        wrong_rule = []
        for st in steps:
            idx = st["r"] * lv["size"] + st["c"]
            if st["tag"] == "邻域":
                f = rp.forced_by_neighbor(idx)
                other = rp.forced_by_runs(idx)
            else:
                f = rp.forced_by_runs(idx)
                other = rp.forced_by_neighbor(idx)
            if f != st["act"]:
                bad = {"step": st["no"], "why": "声明的%s规则并未强制 (%d,%d) 为 %s（该规则结果=%s）" % (
                    st["tag"], st["r"] + 1, st["c"] + 1, st["act"], f)}
                break
            if not rp.apply(idx, st["act"]):
                bad = {"step": st["no"], "why": "动作无法落实（矛盾）"}
                break
        complete = len(rp.revealed) + len(rp.known) == rp.total
        mines_ok = rp.known == rp.mines
        ok = (bad is None) and complete and mines_ok and len(steps) > 0
        print("  第%2d关 报告步数=%3d ｜ 逐步可复现=%-5s 推完全盘=%-5s 雷位与真值一致=%-5s %s" % (
            lid, len(steps), "是" if bad is None else "否", "是" if complete else "否",
            "是" if mines_ok else "否", "" if ok else "FAIL: " + json.dumps(bad, ensure_ascii=False)))
        if not ok:
            fails.append({"id": lid, "bad": bad, "complete": complete, "mines_ok": mines_ok,
                          "steps": len(steps)})
        # 与本轮自写求解器的序列比对（顺序是否一致）
        mine = json.loads((ROOT / "verification" / "t13_play_sequences.json").read_text(encoding="utf-8"))[str(lid)]
        same_order = len(mine) == len(steps) and all(
            a["act"] == b["act"] and a["r"] == b["r"] and a["c"] == b["c"]
            for a, b in zip(mine, steps))
        print("      与本轮求解器序列逐步同序=%s（本实现 %d 步 vs 报告 %d 步）" % (
            "是" if same_order else "否", len(mine), len(steps)))

    print()
    print("重放判定：%s（失败关数 %d）" % ("PASS" if not fails else "FAIL", len(fails)))
    out = {"levels": len(levels), "fails": fails, "verdict": "PASS" if not fails else "FAIL"}
    (ROOT / "verification" / "t13_out_report_replay.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())