# -*- coding: utf-8 -*-
"""
T8 独立复核 · C 部分：静态唯一性（独立穷举）。

统计「开局可见信息（opening flood fill 翻开的格 + 其上的数字）+ 行列连续块线索
（只有第 2/3 关显示）+ 雷总数」下所有相容的完整布雷方案数。

两个相互独立的实现互相交叉验证：
  方法1 DFS：按行候选模式 + 列线索前缀剪枝 + 数字即时剪枝 + 雷总数上下界
  方法2 暴力：method1 的行模式做 itertools.product 全展开，直接校验列线索/数字/总数
            （仅当展开规模可承受时执行）

独立性声明：完全自写，不 import、不复制 tools/generate_levels.py。

用法：
    python verification/c_uniqueness.py            # 每关 120s 预算
输出：
    stdout 日志 + verification/out_c.json
"""
import itertools
import json
import os
import sys
import time
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEVELS_JSON = Path(os.environ.get("T8_LEVELS", ROOT / "tools" / "levels.json"))
BUDGET_S = 120.0
MAX_SOLUTIONS = 500000


def neighbors_list(n):
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


def row_patterns_exact(n, runs, known_safe):
    """长度 n、块序列恰为 runs、且 known_safe 列不能是雷的全部 0/1 行模式。"""
    out = []
    row = [0] * n

    def rec(bi, start):
        if bi == len(runs):
            for p in range(start, n):
                row[p] = 0            # 尾部必须全是安全格
            out.append(tuple(row))
            return
        L = runs[bi]
        rest = runs[bi + 1:]
        need = sum(rest) + len(rest)
        for s in range(start, n - L - need + 1):
            if any(p in known_safe for p in range(s, s + L)):
                continue
            for p in range(start, s):
                row[p] = 0            # 本块前的空隙
            for p in range(s, s + L):
                row[p] = 1
            if rest:
                if s + L >= n:
                    continue
                row[s + L] = 0        # 块间至少要有一个安全格
                rec(bi + 1, s + L + 1)
            else:
                rec(bi + 1, s + L)    # 最后一块之后不跳过任何格

    rec(0, 0)
    return out


def row_patterns_free(n, known_safe):
    allowed = [c for c in range(n) if c not in known_safe]
    out = []
    for mask in range(1 << len(allowed)):
        row = [0] * n
        for k, c in enumerate(allowed):
            if mask >> k & 1:
                row[c] = 1
        out.append(tuple(row))
    return out


class Ctx:
    def __init__(self, level):
        self.lv = level
        self.n = n = level["size"]
        self.total = n * n
        self.true_mines = {r * n + c for r, c in level["mines"]}
        self.nbrs = neighbors_list(n)
        self.counts = [sum(1 for j in self.nbrs[i] if j in self.true_mines) for i in range(self.total)]
        self.declared_total = len(level["mines"])
        # 开局可见：opening + flood fill
        op = level["opening"]
        rev = set()
        st = [op[0] * n + op[1]]
        while st:
            i = st.pop()
            if i in rev:
                continue
            rev.add(i)
            if self.counts[i] == 0:
                for j in self.nbrs[i]:
                    if j not in rev:
                        st.append(j)
        self.revealed = rev
        self.row_opts = []
        for r in range(n):
            forb = {c for c in range(n) if (r * n + c) in rev}
            if level["showRuns"]:
                self.row_opts.append(row_patterns_exact(n, level["rowRuns"][r], forb))
            else:
                self.row_opts.append(row_patterns_free(n, forb))


def method_dfs(ctx, use_numbers, deadline):
    n, total = ctx.n, ctx.total
    use_runs = bool(ctx.lv["showRuns"])
    if not use_runs and not use_numbers:
        u = total - len(ctx.revealed)
        return {"solutions": comb(u, ctx.declared_total) if u >= ctx.declared_total else 0,
                "nodes": 0, "timeout": False, "sols_sample": [],
                "note": "组合数捷径 C(%d,%d)" % (u, ctx.declared_total)}
    for r, opts in enumerate(ctx.row_opts):
        if not opts:
            return {"solutions": 0, "nodes": 0, "timeout": False, "sols_sample": [],
                    "note": "第 %d 行无任何相容模式" % (r + 1)}

    col_runs = [list(x) for x in ctx.lv["colRuns"]]
    suf_min = [0] * (n + 1)
    suf_max = [0] * (n + 1)
    for r in range(n - 1, -1, -1):
        suf_min[r] = suf_min[r + 1] + min(sum(p) for p in ctx.row_opts[r])
        suf_max[r] = suf_max[r + 1] + max(sum(p) for p in ctx.row_opts[r])

    stats = {"nodes": 0, "solutions": 0, "sols_sample": [], "timeout": False}
    col_comp = [tuple() for _ in range(n)]
    col_cur = [0] * n
    cols_state = [0] * total
    chosen = []

    def numbers_ok(r):
        if not use_numbers:
            return True
        for i in ctx.revealed:
            if i // n > r + 1:
                continue
            m = und = 0
            for j in ctx.nbrs[i]:
                if j // n <= r:
                    if cols_state[j]:
                        m += 1
                else:
                    und += 1
            if m > ctx.counts[i] or m + und < ctx.counts[i]:
                return False
            if und == 0 and m != ctx.counts[i]:
                return False
        return True

    def col_prune(r):
        if not use_runs:
            return True
        remaining = n - 1 - r
        for c in range(n):
            comp = col_comp[c]
            if len(comp) > len(col_runs[c]) or comp != tuple(col_runs[c][:len(comp)]):
                return False
            if col_cur[c] > 0:
                if len(comp) >= len(col_runs[c]) or col_cur[c] > col_runs[c][len(comp)]:
                    return False
            runs_left = col_runs[c][len(comp):]
            if col_cur[c] > 0:
                rem = list(runs_left)
                rem[0] -= col_cur[c]
                need = sum(rem) + (len(rem) - 1 if rem else 0)
            else:
                need = (sum(runs_left) + len(runs_left) - 1) if runs_left else 0
            if need > remaining:
                return False
        return True

    def dfs(r, mines_so_far):
        stats["nodes"] += 1
        if stats["nodes"] % 100000 == 0 and time.monotonic() > deadline:
            stats["timeout"] = True
            return
        if mines_so_far + suf_min[r] > ctx.declared_total or mines_so_far + suf_max[r] < ctx.declared_total:
            return
        if r == n:
            if mines_so_far == ctx.declared_total:
                stats["solutions"] += 1
                if len(stats["sols_sample"]) < 6:
                    stats["sols_sample"].append(
                        ["".join("X" if p[c] else "." for c in range(n)) for p in chosen])
            return
        for pat in ctx.row_opts[r]:
            k = sum(pat)
            if mines_so_far + k > ctx.declared_total:
                continue
            saved_comp = list(col_comp)
            saved_cur = list(col_cur)
            for c in range(n):
                cols_state[r * n + c] = pat[c]
                if pat[c]:
                    col_cur[c] += 1
                elif col_cur[c] > 0:
                    col_comp[c] = col_comp[c] + (col_cur[c],)
                    col_cur[c] = 0
            chosen.append(pat)
            if col_prune(r) and numbers_ok(r):
                dfs(r + 1, mines_so_far + k)
            chosen.pop()
            if stats["timeout"]:
                return
            for c in range(n):
                col_comp[c] = saved_comp[c]
                col_cur[c] = saved_cur[c]
                cols_state[r * n + c] = 0

    dfs(0, 0)
    return {"solutions": stats["solutions"], "nodes": stats["nodes"],
            "timeout": stats["timeout"], "sols_sample": stats["sols_sample"]}


def method_bruteforce(ctx, deadline, cap=3_000_000):
    """方法2：把行模式做笛卡尔积全展开，直接校验（独立于方法1的剪枝）。"""
    n = ctx.n
    sizes = [len(o) for o in ctx.row_opts]
    prod = 1
    for s in sizes:
        prod *= s
    if prod > cap:
        return {"available": False, "product_rows": prod, "solutions": None,
                "note": "行模式全展开规模 %d 超过上限 %d，未执行" % (prod, cap)}
    t0 = time.monotonic()
    sols = 0
    sample = []
    col_runs = [list(x) for x in ctx.lv["colRuns"]]
    showed = ctx.lv["showRuns"]
    for combo in itertools.product(*ctx.row_opts):
        if time.monotonic() - t0 > deadline:
            return {"available": True, "product_rows": prod, "solutions": sols,
                    "timeout": True, "elapsed_s": round(time.monotonic() - t0, 2)}
        if sum(sum(p) for p in combo) != ctx.declared_total:
            continue
        if showed:
            bad = False
            for c in range(n):
                if runs_of([combo[r][c] for r in range(n)]) != col_runs[c]:
                    bad = True
                    break
            if bad:
                continue
        ok = True
        for i in ctx.revealed:
            m = sum(1 for j in ctx.nbrs[i] if combo[j // n][j % n])
            if m != ctx.counts[i]:
                ok = False
                break
        if not ok:
            continue
        sols += 1
        if len(sample) < 3:
            sample.append(["".join("X" if p[c] else "." for c in range(n)) for p in combo])
    return {"available": True, "product_rows": prod, "solutions": sols, "timeout": False,
            "elapsed_s": round(time.monotonic() - t0, 2), "sols_sample": sample}


def method_comb(ctx, deadline):
    """方法3（无 run 线索时）：对未知格集合直接做组合枚举，逐个校验可见数字。"""
    unknown = [i for i in range(ctx.total) if i not in ctx.revealed]
    if len(unknown) > 30:
        return {"available": False, "note": "未知格 %d 个，组合枚举放弃" % len(unknown)}
    t0 = time.monotonic()
    cnt = 0
    sample = []
    for combo in itertools.combinations(unknown, ctx.declared_total):
        if time.monotonic() - t0 > deadline:
            return {"available": True, "solutions": cnt, "timeout": True,
                    "elapsed_s": round(time.monotonic() - t0, 2)}
        ms = set(combo)
        ok = True
        for i in ctx.revealed:
            if sum(1 for j in ctx.nbrs[i] if j in ms) != ctx.counts[i]:
                ok = False
                break
        if ok:
            cnt += 1
            if len(sample) < 3:
                sample.append(tuple(sorted(combo)))
    return {"available": True, "solutions": cnt, "timeout": False,
            "elapsed_s": round(time.monotonic() - t0, 2), "sols_sample": sample}


def true_layout_is_valid(ctx):
    """自检：真实布雷本身必须满足全部约束（否则说明枚举/剪枝有 bug 会导致漏解）。"""
    n = ctx.n
    ms = ctx.true_mines
    # 已翻开格数字
    for i in ctx.revealed:
        if sum(1 for j in ctx.nbrs[i] if j in ms) != ctx.counts[i]:
            return False, "真实布局不满足已翻开格 #%d 的数字" % i
    if len(ms) != ctx.declared_total:
        return False, "真实布局雷数 %d != 声明 %d" % (len(ms), ctx.declared_total)
    for r in range(n):
        if runs_of([1 if (r * n + c) in ms else 0 for c in range(n)]) != list(ctx.lv["rowRuns"][r]):
            return False, "真实布局第 %d 行线索不符" % (r + 1)
    for c in range(n):
        if runs_of([1 if (r * n + c) in ms else 0 for r in range(n)]) != list(ctx.lv["colRuns"][c]):
            return False, "真实布局第 %d 列线索不符" % (c + 1)
    return True, "真实布局满足全部约束"


def main():
    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    out = {"budget_s": BUDGET_S, "levels": []}
    for lv in levels:
        print("=" * 78)
        print("第 %d 关 %dx%d showRuns=%s" % (lv["id"], lv["size"], lv["size"], lv["showRuns"]))
        ctx = Ctx(lv)
        print("  开局可见格数=%d ；行候选模式数=%s ；行模式笛卡尔积=%d" % (
            len(ctx.revealed), [len(o) for o in ctx.row_opts],
            __import__("functools").reduce(lambda a, b: a * b, [len(o) for o in ctx.row_opts], 1)))
        rec = {"id": lv["id"], "revealed_at_start": len(ctx.revealed),
               "row_option_counts": [len(o) for o in ctx.row_opts]}
        tv, tmsg = true_layout_is_valid(ctx)
        rec["true_layout_valid"] = tv
        print("  自检：%s" % tmsg)
        modes = [("full", True)]
        if not lv["showRuns"]:
            modes.append(("no_numbers", False))   # 诊断模式只对无连续块的关卡做（含块的关卡组合空间过大）
        for tag, use_nums in modes:
            t0 = time.monotonic()
            res = method_dfs(ctx, use_nums, t0 + BUDGET_S)
            res["elapsed_s"] = round(time.monotonic() - t0, 3)
            rec[tag] = res
            print("  [DFS %s] %s 解数=%s 节点=%s 用时=%.3fs %s" % (
                tag, "未判定(超预算)" if res.get("timeout") else "已判定",
                res["solutions"], res["nodes"], res["elapsed_s"],
                "note=%s" % res["note"] if res.get("note") else ""))
            for si, sol in enumerate(res.get("sols_sample", [])[:3], 1):
                print("        解%d: %s" % (si, " | ".join(sol)))
            if res.get("timeout"):
                print("        瓶颈：预算 %.0fs 未穷尽；已搜索节点 %d，暂见解数 %d（不完整）" % (
                    BUDGET_S, res["nodes"], res["solutions"]))
        # 交叉验证（方法2 / 方法3，彼此独立于方法1的剪枝逻辑）
        bf = method_bruteforce(ctx, time.monotonic() + BUDGET_S)
        rec["bruteforce"] = bf
        xcheck = None
        if bf["available"]:
            print("  [暴力交叉验证·行模式全展开] 展开=%d 解数=%s 用时=%ss 超时=%s %s" % (
                bf["product_rows"], bf["solutions"], bf.get("elapsed_s", "-"),
                bf.get("timeout"), bf.get("note", "")))
            if not bf.get("timeout"):
                xcheck = bf["solutions"]
        else:
            print("  [暴力交叉验证·行模式全展开] 未执行：%s" % bf["note"])
        if not ctx.lv["showRuns"]:
            cb = method_comb(ctx, time.monotonic() + BUDGET_S)
            rec["comb_bruteforce"] = cb
            if cb["available"]:
                print("  [暴力交叉验证·组合枚举] 解数=%s 用时=%ss 超时=%s" % (
                    cb["solutions"], cb.get("elapsed_s"), cb.get("timeout")))
                if not cb.get("timeout"):
                    xcheck = cb["solutions"] if xcheck is None else xcheck
            else:
                print("  [暴力交叉验证·组合枚举] 未执行：%s" % cb["note"])
        rec["cross_check_solutions"] = xcheck
        rec["cross_check_agree"] = (xcheck == rec["full"]["solutions"]) if xcheck is not None else None
        # 自检：精确解数必须 >=1，且真实布局必须合法（否则枚举有漏解 bug）
        if not rec["full"].get("timeout") and tv:
            rec["solution_count_sane"] = rec["full"]["solutions"] >= 1
        print("        交叉验证解数=%s ｜ 与方法1(full)一致=%s" % (xcheck, rec["cross_check_agree"]))
        out["levels"].append(rec)

    (ROOT / "verification" / "out_c.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("== C 部分小结（解数=1 才算唯一；'未判定' 不算通过）==")
    for rec in out["levels"]:
        f = rec["full"]
        if f.get("timeout"):
            verdict = "未判定"
        elif f["solutions"] == 1:
            verdict = "唯一（通过）"
        else:
            verdict = "不唯一（解数=%d，不通过）" % f["solutions"]
        print("第 %d 关: %s ｜ 节点 %d ｜ 用时 %ss ｜ 交叉验证=%s ｜ 忽略数字时解数=%s" % (
            rec["id"], verdict, f["nodes"], f["elapsed_s"], rec.get("cross_check_agree"),
            rec["no_numbers"]["solutions"] if "no_numbers" in rec else "（含连续块，未做）"))
    print("JSON -> verification/out_c.json")


if __name__ == "__main__":
    sys.exit(main())