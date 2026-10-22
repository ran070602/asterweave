# -*- coding: utf-8 -*-
"""v13 B：独立零猜测求解器。

自写规则集合（不 import / 不复制 tools/ 下任何生成器代码）：
  R1 邻域计数传播：对每个已翻开数字格，把"未翻开邻居数 == 剩余雷数"的全部判为雷 /
     把"剩余雷数为 0"的判为安全。（可选 R1b 子集规则，默认关闭）
  R2 数织行列枚举：对每一行/列枚举所有与"已知雷 / 已知安全格"相容的连续块摆法，
     在所有摆法中都为雷 → 雷；在所有摆法中都未被覆盖 → 安全。仅 showRuns=true 的关启用。
  R3 flood fill：翻开的 0 格把 8 邻域连锁翻开（与 SPEC 语义一致，已插旗格挡 flood，
     但本求解器只对"已证明是雷"的格插旗，故不影响）。
三种规则交替到不动点；每一步都必须有可证明的格子，绝不猜测。
"""
import json, os, sys

ROOT = r"D:\AI-Native casual game"
LV = os.path.join(ROOT, "tools", "levels.json")

def nbrs_of(i, n):
    r, c = divmod(i, n)
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0: continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n: out.append(rr * n + cc)
    return out

def line_placements(cells, runs, km, ks, cap=400000):
    """枚举该行/列所有与已知雷/已知安全相容的摆法，返回 [set(cells)]。"""
    L = len(cells)
    if not runs:
        cov = set()
        return [cov] if not (km & set(cells)) else []
    out = []
    def rec(k, start, chosen):
        if len(out) > cap: return
        if k == len(runs):
            cov = set()
            for s, ln in chosen:
                for t in range(s, s + ln): cov.add(cells[t])
            if km <= cov and not (cov & ks): out.append(cov)
            return
        need = sum(runs[k:]) + (len(runs) - k - 1)
        last = L - need
        for s in range(start, last + 1):
            rec(k + 1, s + runs[k] + 1, chosen + [(s, runs[k])])
    rec(0, 0, [])
    return out

def solve(L, use_runs=True, use_subset=False, record_actions=False):
    n = L["size"]
    total = n * n
    mine = {r * n + c for r, c in L["mines"]}
    counts = [sum(1 for j in nbrs_of(i, n) if j in mine) for i in range(total)]
    rowRuns = [list(x) for x in L["rowRuns"]]
    colRuns = [list(x) for x in L["colRuns"]]
    show = bool(L.get("showRuns", True)) and use_runs

    revealed = set()      # 已翻开的安全格
    flags = set()         # 已标记的雷
    actions = []          # (mode, i) 播放序列

    def reveal_closure(seed, is_action=True):
        # 只有 seed 是"玩家主动探格"这一次动作；flood 连锁展开是自动的，不计入探格次数
        if seed in revealed: return
        if is_action and record_actions: actions.append(["dig", seed])
        stack = [seed]
        while stack:
            i = stack.pop()
            if i in revealed or i in mine: continue
            revealed.add(i)
            if counts[i] == 0:
                stack.extend(j for j in nbrs_of(i, n) if j not in mine and j not in flags)

    def do_flag(i):
        if i in flags: return
        flags.add(i)
        if record_actions: actions.append(["flag", i])

    # 开局赠送：opening 是 0 格，自动 flood fill（不是玩家动作）
    oi = L["opening"][0] * n + L["opening"][1]
    reveal_closure(oi, is_action=False)

    rounds = 0
    steps = 0
    used_r2 = False
    stuck_reason = ""
    while True:
        rounds += 1
        new_mines, new_safe = set(), set()

        # --- R1 邻域计数 ---
        for i in revealed:
            un = [j for j in nbrs_of(i, n) if j not in revealed]
            fl = [j for j in un if j in flags]
            free = [j for j in un if j not in flags]
            rem = counts[i] - len(fl)
            if rem < 0 or rem > len(free) + 0: 
                pass
            if rem == 0:
                new_safe.update(free)
            elif rem == len(free) and rem > 0:
                new_mines.update(free)

        # --- R1b 子集规则（两个已翻开格的邻域差集），默认关闭 ---
        if use_subset and not new_mines and not new_safe:
            consts = [i for i in revealed]
            for a in consts:
                ua = {j for j in nbrs_of(a, n) if j not in revealed}
                ra = counts[a] - len([j for j in ua if j in flags])
                fa = {j for j in ua if j not in flags}
                for b in consts:
                    if a == b: continue
                    ub = {j for j in nbrs_of(b, n) if j not in revealed}
                    if not fa or not (fa < ub): continue
                    fb = {j for j in ub if j not in flags} - fa
                    rb = counts[b] - len([j for j in ub if j in flags])
                    diff = rb - ra
                    if diff == len(fb) and diff > 0: new_mines.update(fb)
                    elif diff == 0: new_safe.update(fb)

        # --- R2 数织行列枚举 ---
        if show:
            for by_row in (True, False):
                for k in range(n):
                    cells = [k * n + t for t in range(n)] if by_row else [t * n + k for t in range(n)]
                    km = {c for c in cells if c in flags}
                    ks = {c for c in cells if c in revealed}
                    if km & ks: continue
                    pl = line_placements(cells, rowRuns[k] if by_row else colRuns[k], km, ks)
                    if not pl: continue
                    for c in cells:
                        if c in revealed or c in flags: continue
                        inall = all(c in p for p in pl)
                        inany = any(c in p for p in pl)
                        if inall: new_mines.add(c)
                        elif not inany: new_safe.add(c)
                    if any((c not in revealed and c not in flags) for c in cells) and pl:
                        pass

        new_mines -= flags
        new_mines -= revealed
        new_safe -= revealed
        new_safe -= flags
        if not new_mines and not new_safe:
            done = (len(revealed) == total - len(mine)) and (mine <= flags)
            if done: return dict(ok=True, rounds=rounds, actions=actions, used_r2=used_r2, digs=sum(1 for a in actions if a[0] == "dig"))
            stuck_reason = "第 %d 轮不动点：已翻开 %d/%d 安全格，已标 %d/%d 雷" % (
                rounds, len(revealed), total - len(mine), len(flags & mine), len(mine))
            return dict(ok=False, rounds=rounds, actions=actions, used_r2=used_r2, why=stuck_reason)
        if new_mines:
            used_r2 = used_r2 or show
        for i in sorted(new_mines):
            if i in mine: do_flag(i)
            else: return dict(ok=False, why="求解器误判雷 @%d 第%d关" % (i, L["id"]))
        # 探格顺序：优先探 0 格（一次 flood 带出一片），已被连带翻开的格子不再重复动作
        for i in sorted(new_safe, key=lambda x: (counts[x] != 0, x)):
            if i in revealed: continue
            if i in mine: return dict(ok=False, why="求解器误判安全 @%d 第%d关" % (i, L["id"]))
            reveal_closure(i)

def main():
    lv = json.load(open(LV, encoding="utf-8"))
    res = {}
    bad = []
    r1_only_ok = 0
    for L in lv:
        r = solve(L, use_runs=True, record_actions=True)
        r1 = solve(L, use_runs=False)
        res[L["id"]] = dict(ok=r["ok"], digs=r.get("digs"), rounds=r["rounds"],
                            r1_only=r1["ok"], why=r.get("why", ""),
                            showRuns=L.get("showRuns"))
        if r1["ok"]: r1_only_ok += 1
        if not r["ok"]: bad.append((L["id"], L["theme"]["name"], r.get("why")))
    print("=== B 零猜测可解性（逐关）===")
    print("可解：%d/50　不可解：%d" % (50 - len(bad), len(bad)))
    for b in bad: print("  FAIL 第%d关 %s：%s" % b)
    print("第 1 关 showRuns=%s，仅邻域推理可解=%s（第1关禁 R2）" % (
        lv[0].get("showRuns"), res[1]["ok"]))
    print("仅靠邻域计数（不用数织线索）即可通关的关数：%d/50 → 需要数织线索的关数：%d/50" % (r1_only_ok, 50 - r1_only_ok))
    print("%-3s %-8s %-4s %-6s %-8s %s" % ("关", "星座", "探格", "轮数", "仅邻域解", "数织贡献"))
    for L in lv:
        r = res[L["id"]]
        contrib = "不需要" if r["r1_only"] else "需要"
        print("%-3d %-8s %-4s %-6d %-8s %s" % (L["id"], L["theme"]["name"], r["digs"], r["rounds"],
                                               "是" if r["r1_only"] else "否", contrib))
    seq = {str(L["id"]): solve(L, record_actions=True)["actions"] for L in lv}
    json.dump(seq, open(os.path.join(ROOT, "verification", "v13_play.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(res, open(os.path.join(ROOT, "verification", "v13_out_b.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    digs = [res[L["id"]]["digs"] for L in lv]
    print("探格次数（本求解器口径）范围 %d–%d" % (min(digs), max(digs)))

if __name__ == "__main__":
    main()
