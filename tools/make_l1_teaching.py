#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「教学型第 1 关」：盘面优先（必须用数织）+ 贴上南十字座。

背景：第 1~20 关原本走 fit_constellation_levels.py 的「星座优先」流程，星点均匀铺开，
导致第 1 关的行/列线索全是 [1]，数织线索一格都用不上（实测 runs_cells=0）。本脚本改用
21 关之后的「盘面优先 + 星座吸附」思路重做第 1 关：

  1. 搜 6×6 小盘面：零猜测可解（用数织）、**不用数织会卡住**（必须用数织）、
     开局展开格数 ≥6（友好）、孤立雷 ≤2、密度 15~25%、至少一条长度 ≥2 的连续块线索；
  2. 把南十字座四颗星吸附到最近的雷上（positions 保持十字形状）；
  3. 只替换 tools/levels.json 的第 1 关，并把同样的教学意图写回 fitter 的 PLAN[0]。

用法：python tools/make_l1_teaching.py [--write]
不加 --write 只做搜索并打印候选，不落盘。
"""
import importlib.util, io, json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m


gl = load("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
fm = load("f", os.path.join(ROOT, "tools", "fit_constellation_levels.py"))
gm = load("gdf", os.path.join(ROOT, "tools", "gen_difficulty_first.py"))

N = 6
TEACH = ("黑格是夜空里的星。数字 = 它周围 8 格里有几颗星（扫雷规则）；"
         "左边/上面的数字 = 这一行 / 这一列里「连续几颗星」（数织规则）。两条线索一起用，就能推出全部星位。")
TECHNIQUE = "扫雷 + 数织 双线索入门"


def isolated_count(mines, n):
    ms = set(map(tuple, mines))
    k = 0
    for (r, c) in ms:
        if not any((r + dr, c + dc) in ms
                   for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)):
            k += 1
    return k


def search(limit=200000):
    """返回按“友好度”排序的候选列表。"""
    rng = random.Random(20261026)
    out = []
    for m in (6, 7, 8):
        tried = 0
        while tried < limit // 3:
            tried += 1
            p = gl.make_puzzle(N, m, True, rng)
            if p is None:
                continue
            on = gl.solve(p, True)
            if not on.ok:
                continue
            off = gl.solve(p, False)
            if off.ok:
                continue                                  # 不用数织也能解 → 不教数织
            if not (1 <= on.runs_cells <= 6):
                continue                                  # 数织必需，但别太重
            if on.reveal_actions < 6:
                continue                                  # 开局要展开得够多
            mines = [[r, c] for (r, c) in sorted(p.mines)]
            if isolated_count(mines, N) > 2:
                continue
            dens = len(mines) / (N * N)
            if not (0.15 <= dens <= 0.25):
                continue
            runs_all = [list(x) for x in p.row_runs] + [list(x) for x in p.col_runs]
            if not any(any(v >= 2 for v in rr) for rr in runs_all):
                continue                                  # 必须有真正的“连续块”线索可教
            out.append({"m": m, "puzzle": p, "mines": mines, "on": on,
                        "reveal": on.reveal_actions, "runs_cells": on.runs_cells,
                        "runs_all": runs_all})
        # 每个雷数各留最好的若干
    out.sort(key=lambda c: (-c["reveal"], c["runs_cells"]))
    return out


def attach(cand):
    """把南十字座吸附到候选盘面的雷上，返回完整关卡 dict。"""
    pts = [(x, y) for (_zh, _en, (x, y), _mag) in fm.CRUX]
    p = cand["puzzle"]
    for scale in (0.95, 0.85, 0.75, 0.65, 0.55, 0.45):
        try:
            chosen = gm.snap(pts, p.mines, N, scale)
        except Exception:
            chosen = None
        if not chosen:
            continue
        base = gl.to_level_json(p, 1, "第 1 关 · 南十字座", TEACH, TECHNIQUE)
        d = {"id": 1, "name": base["name"], "size": base["size"], "mines": base["mines"],
             "noise": [], "showRuns": True, "opening": base["opening"], "lives": base["lives"],
             "teach": base["teach"], "technique": base["technique"],
             "rowRuns": base["rowRuns"], "colRuns": base["colRuns"], "theme": None}
        d2 = gm.attach_theme(d, "Crux", fm.CRUX, fm.CRUX_L, chosen, N, "南十字座")
        if d2:
            return d2
    return None


def main():
    write = "--write" in sys.argv
    cands = search()
    print("候选盘面 %d 个（按开局展开格数排序）" % len(cands))
    picked = None
    for c in cands[:12]:
        d = attach(c)
        if not d:
            continue
        stars = d["theme"]["stars"]
        star_rows = {}
        for s in stars:
            star_rows.setdefault(s["rc"][0], 0)
            star_rows[s["rc"][0]] += 1
        print("  雷%d 展开%d格 数织需%d格 孤立%d 行线索%s 列线索%s 星形%s" % (
            len(d["mines"]), c["reveal"], c["runs_cells"], isolated_count(d["mines"], N),
            d["rowRuns"], d["colRuns"], [tuple(s["rc"]) for s in stars]))
        if picked is None:
            picked = d
    if not picked:
        print("!! 没有找到候选"); sys.exit(1)

    print()
    print("==== 选定第 1 关 ====")
    print(json.dumps(picked, ensure_ascii=False, indent=2)[:900])

    # 验收复算
    check = gl.check_level(picked, static=False)
    print("\ncheck_level(static=False): ok=%s problems=%s" % (check[0], check[1]))
    info = check[2] if len(check) > 2 else {}
    print("  开局展开=%s 数织必需=%s（nb_only_ok 应为 False） 数织格数=%s" % (
        info.get("opening_reveal"), info.get("nb_only_ok"), info.get("runs_cells")))

    if not write:
        print("\n（未加 --write，未落盘）")
        return

    lp = os.path.join(ROOT, "tools", "levels.json")
    lv = json.load(io.open(lp, encoding="utf-8"))
    old = lv[0]
    lv[0] = picked
    io.open(lp, "w", encoding="utf-8").write(
        json.dumps(lv, ensure_ascii=False, indent=2) + "\n")
    print("\n✅ 已写入 tools/levels.json 第 1 关")
    print("   旧: 雷%d 行线索%s" % (len(old["mines"]), old["rowRuns"]))
    print("   新: 雷%d 行线索%s" % (len(picked["mines"]), picked["rowRuns"]))


if __name__ == "__main__":
    main()
