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
            if not (2 <= on.runs_cells <= 8):
                continue                                  # 数织要真的参与
            if on.reveal_actions < 6:
                continue                                  # 开局要展开得够多
            mines = [[r, c] for (r, c) in sorted(p.mines)]
            if isolated_count(mines, N) > 2:
                continue
            dens = len(mines) / (N * N)
            if not (0.15 <= dens <= 0.25):
                continue
            if not (8 <= on.reveal_actions <= 18):
                continue                                  # 太简单（几乎已解开）也不要
            runs_all = [list(x) for x in p.row_runs] + [list(x) for x in p.col_runs]
            # 真正的“连续块”线索：某条线的线索里有 >=2 的长度（注意 [1,1] 是两块单星，不算块）
            block_lines = [rr for rr in runs_all if any(v >= 2 for v in rr)]
            if len(block_lines) < 2:
                continue                                  # 至少两条线有连续块，才教得起来
            max_block = max([v for rr in block_lines for v in rr if v >= 2] or [0])
            out.append({"m": m, "puzzle": p, "mines": mines, "on": on,
                        "reveal": on.reveal_actions, "runs_cells": on.runs_cells,
                        "runs_all": runs_all, "block_lines": len(block_lines),
                        "max_block": max_block})
        # 每个雷数各留最好的若干
    # 优先：块更长 → 块线索更多 → 数织参与更少（更轻）→ 展开更多（更友好）
    out.sort(key=lambda c: (-c["max_block"], -c["block_lines"], c["runs_cells"], -c["reveal"]))
    return out


def attach(cand):
    """把南十字座吸附到候选盘面的雷上，返回完整关卡 dict。"""
    pts = [(x, y) for (_zh, _en, (x, y), _mag) in fm.CRUX]
    p = cand["puzzle"]
    chosen = None
    # 遍历 8 种旋转/翻转 × 多个缩放（snap 只处理“已变换”的星位）
    for oriented in gm.transforms(pts):
        for scale in (0.95, 0.85, 0.75, 0.65, 0.55, 0.45):
            try:
                chosen = gm.snap(oriented, p.mines, N, scale)
            except Exception:
                chosen = None
            if chosen:
                break
        if chosen:
            break
    if chosen:
        for _scale in (0,):
            base = gl.to_level_json(p, 1, "第 1 关 · 南十字座", TEACH, TECHNIQUE)
            d = {"id": 1, "name": base["name"], "size": base["size"], "mines": base["mines"],
                 "noise": [], "showRuns": True, "opening": base["opening"], "lives": base["lives"],
                 "teach": base["teach"], "technique": base["technique"],
                 "rowRuns": base["rowRuns"], "colRuns": base["colRuns"], "theme": None}
            d2 = gm.attach_theme(d, "Crux", fm.CRUX, fm.CRUX_L, chosen, N, "南十字座")
            if not d2:
                continue
            ok, _probs, info = gl.check_level(d2, static=False)
            if not ok:
                continue
            if info.get("nb_only_ok") is not False:
                continue                                  # 必须“不用数织会卡住”
            if not (2 <= (info.get("runs_cells") or 0) <= 8):
                continue
            rc = [tuple(x["rc"]) for x in d2["theme"]["stars"]]
            rows = [r for (r, _c) in rc]; cols = [c for (_r, c) in rc]
            has_row_pair = any(rows.count(r) >= 2 for r in set(rows))
            has_col_pair = any(cols.count(c) >= 2 for c in set(cols))
            if not (has_row_pair and has_col_pair):
                continue                                  # 星形要“一横一竖”，像十字
            # 更严：揭晓会画的两段（CRUX_L）必须一段横、一段竖，否则画出来是“两条平行线”
            seg = []
            for (a, b) in fm.CRUX_L:
                (r1, c1), (r2, c2) = rc[a], rc[b]
                seg.append('H' if r1 == r2 else ('V' if c1 == c2 else 'D'))
            if 'H' not in seg or 'V' not in seg:
                continue
            star_cells = set(rc)
            runs_ok = False
            for i, rr in enumerate(d2["rowRuns"]):
                if any(v >= 2 for v in rr) and any(r == i for (r, _c) in star_cells):
                    runs_ok = True
            for j, cc in enumerate(d2["colRuns"]):
                if any(v >= 2 for v in cc) and any(c == j for (_r, c) in star_cells):
                    runs_ok = True
            if not runs_ok:
                continue                                  # 连续块线索要落在有星的线上（教学相关）
            return d2
    return None


def main():
    write = "--write" in sys.argv
    cands = search()
    print("候选盘面 %d 个（按开局展开格数排序）" % len(cands))
    picked = None
    for c in cands[:400]:
        d = attach(c)
        if not d:
            continue
        stars = d["theme"]["stars"]
        star_rows = {}
        for s in stars:
            star_rows.setdefault(s["rc"][0], 0)
            star_rows[s["rc"][0]] += 1
        print("  雷%d 展开%d格 数织需%d格 块%d条/最长%d 行%s 列%s 星%s" % (
            len(d["mines"]), c["reveal"], c["runs_cells"], c["block_lines"], c["max_block"],
            d["rowRuns"], d["colRuns"], [tuple(s["rc"]) for s in stars]))
        if picked is None:
            picked = d
            break                                   # 取第一个“线索合格且能贴上星座”的盘面
    if not picked:
        print("!! 没有找到候选"); sys.exit(1)

    print()
    print("==== 选定第 1 关 ====")
    print("  雷=%s" % picked["mines"])
    print("  行线索=%s" % picked["rowRuns"])
    print("  列线索=%s" % picked["colRuns"])
    print("  opening=%s showRuns=%s teach=%s" % (picked["opening"], picked["showRuns"], picked["teach"]))
    print("  星=%s 杂星=%s" % ([s["rc"] for s in picked["theme"]["stars"]], picked["noise"]))

    # 验收复算（权威判据）
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
