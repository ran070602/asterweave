#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《星织 Asterweave》**无尽模式专用题库**：88 个星座 × 2 块盘面 = 176 题。

设计（用户 2026-10-26 拍板）：
  * 尺寸配额：6×6 22 题、7×7 22 题、8×8 22 题、9×9 22 题、10×10 22 题、11×11 66 题；
  * 覆盖 tools/constellations88.json 的全部 88 个星座，**每个星座恰好 2 题**
    （一题小盘 6–9，一题大盘 10–11），两题尺寸必然不同；
  * 雷密度（按尺寸给设计值，允许 ±0.01）：
    6×6 0.22、7×7 0.23、8×8 0.24、9×9 0.25、10×10 0.26、11×11 0.27。

流程（沿用 tools/gen_levels_51_88.py 的「盘面优先 + 真实星座形状保真」做法）：
  1. gm.gen_layout() 造盘面 → 空行/空列 = 0、孤立雷 ≤ 2、雷数 = round(dens·n²)
     （= 设计密度 ±0.01）、与**同星座 campaign 盘面**矿点不重复；
  2. gm.build_level() 定 opening（开局展开最多且 ≤38% 盘的 0 格）；
  3. gl.check_level(d, static=False) 权威验收：ok、**nb_only_ok 必须为 False**
     （必须用数织）、runs_cells ≥ 3；
  4. 星座贴到雷上：真实 ra/dec 做 gnomonic 球面投影 → 归一化 pts_norm，
     枚举 4 种坐标映射 × 8 种旋转/翻转（gm.transforms）× 4 档 scale 的全部合法吸附，
     用「带标签距离矩阵 + 手性罚分」评分挑最像真实天图的贴法；**手性必须与真实天图一致
     （mirror == 0，不允许镜像）**，同尺寸下再跨盘面取 dist_err 最小者；
  5. gm.attach_theme() 生成 theme（stars[].rc = 盘面格坐标、lines 来自 constellations88
     的下标对），星必须落在雷上且互不重复，noise = mines − stars。

尺寸分配是**数据驱动**的：先让全部 88 个星座都去试 6×6（实测可行性），
把其中 22 个最好的留给 6×6；剩下的再去试 7×7，取 22 个；依此类推 → 严格满足配额
（某星座凑不出就换盘面重试并在报告里说明；以尺寸配额优先）。
大盘 10×10 的 22 个名额按「形状紧凑度排名 % 4 == 3」分配，其余 44 + 22 = 66 走 11×11。

产物（只写这三个文件）：
  tools/endless_bank_full.json      176 条题库（schema 与 tools/levels.json 同构，不含 timeK）
  docs/无尽题库形状核对.png          176 格星座形状核对图（浅底深线）

用法：
  python tools/gen_endless_bank.py                 # 生成 + 写 JSON + 画核对图
  python tools/gen_endless_bank.py --verify        # 只复核已有 JSON（权威验收 + 统计，不写产物）
  python tools/gen_endless_bank.py --png           # 只按已有 JSON 重画核对图
  python tools/gen_endless_bank.py --debug 6 --limit 6   # 调试：只跑 6×6 的前 6 个星座，不写产物
  python tools/gen_endless_bank.py --seed 20261026 --scale 1.0   # 预算整体缩放
"""
import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


gl = load("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
f = load("f", os.path.join(ROOT, "tools", "fit_constellation_levels.py"))
gm = load("gm", os.path.join(ROOT, "tools", "gen_difficulty_first.py"))

CONST_JSON = os.path.join(ROOT, "tools", "constellations88.json")
LEVELS_JSON = os.path.join(ROOT, "tools", "levels.json")
OUT_JSON = os.path.join(ROOT, "tools", "endless_bank_full.json")
OUT_PNG = os.path.join(ROOT, "docs", "无尽题库形状核对.png")

# ---------------------------------------------------------------- 设计参数
DENS = {6: 0.22, 7: 0.23, 8: 0.24, 9: 0.25, 10: 0.26, 11: 0.27}
QUOTA = {6: 22, 7: 22, 8: 22, 9: 22, 10: 22, 11: 66}
SMALL = (6, 7, 8, 9)
LARGE = (10, 11)
# 每题搜索预算（秒，按尺寸）：先到 STOP_DIST 就收手，否则用满预算取其中最好的一个
SIZE_BUDGET = {6: 1.4, 7: 1.3, 8: 1.3, 9: 1.3, 10: 1.3, 11: 1.5}
STOP_DIST = {6: 0.16, 7: 0.125, 8: 0.10, 9: 0.085, 10: 0.075, 11: 0.07}
MAX_ATTEMPTS = 40000
FIELDS = ["id", "name", "size", "mines", "noise", "showRuns", "opening", "lives",
          "teach", "technique", "rowRuns", "colRuns", "theme"]
TECHNIQUE = "endless-bank"

# ---------------------------------------------------------------- 形状保真
SCALES = (0.62, 0.72, 0.82, 0.92)   # 4 档缩放（与 51–88 一致）
MIRROR_PEN = 0.35       # 与真实天区手性相反时的固定罚分
DUP_PEN = 0.05          # 两条下标不同的连线画成同一段几何线时的罚分
OFF_PEN = 0.04          # 图形偏离盘面中心的罚分（除以 n）
SCALE_BONUS = 0.03      # 同等形状下偏向更大的图（更好认）
FULL_CHIRAL = 1         # 手性必须一致（不允许镜像）——硬性


def unit_vec(ra_h, dec_deg):
    ra, de = math.radians(ra_h * 15.0), math.radians(dec_deg)
    return (math.cos(de) * math.cos(ra), math.cos(de) * math.sin(ra), math.sin(de))


def chirality(XY):
    m = len(XY)
    gx = sum(p[0] for p in XY) / m
    gy = sum(p[1] for p in XY) / m
    s = 0.0
    for i in range(m):
        a, b = XY[i], XY[(i + 1) % m]
        s += (a[0] - gx) * (b[1] - gy) - (a[1] - gy) * (b[0] - gx)
    return 1 if s > 0 else (-1 if s < 0 else 0)


def canonical_shape(stars):
    """真实 ra/dec → 屏幕坐标 (X 右正, Y 下正) 的归一化形状（gnomonic 球面投影）。

    X = -east（天图上东在左），Y = -north（屏幕 Y 向下）；再平移 + 等比缩放到 [0,1]
    （保长宽比）。返回 (归一化点列, 手性符号)，手性 = 按星表顺序求
    Σ cross(P_i - 质心, P_{i+1} - 质心) 的符号（旋转不变、镜像反号）。
    与 tools/gen_levels_51_88.py 的 canonical_shape 逐行一致。
    """
    us = [unit_vec(s["raH"], s["decDeg"]) for s in stars]
    m = len(us)
    cx = sum(u[0] for u in us) / m
    cy = sum(u[1] for u in us) / m
    cz = sum(u[2] for u in us) / m
    nrm = math.sqrt(cx * cx + cy * cy + cz * cz) or 1.0
    c = (cx / nrm, cy / nrm, cz / nrm)
    ra0 = math.atan2(c[1], c[0])
    east = (-math.sin(ra0), math.cos(ra0), 0.0)
    north = (c[1] * east[2] - c[2] * east[1],
             c[2] * east[0] - c[0] * east[2],
             c[0] * east[1] - c[1] * east[0])
    dec0 = math.degrees(math.asin(max(-1.0, min(1.0, c[2]))))
    pts = []
    fallback = False
    for u in us:
        cosc = sum(a * b for a, b in zip(u, c))
        if cosc < 0.05:                      # 跨度过大，投影退化 → 等距圆柱兜底
            fallback = True
            break
        pts.append((sum(a * b for a, b in zip(u, east)) / cosc,
                    sum(a * b for a, b in zip(u, north)) / cosc))
    if fallback:
        pts = []
        for s in stars:
            dl = (s["raH"] * 15.0 - math.degrees(ra0) + 180.0) % 360.0 - 180.0
            pts.append((dl * math.cos(math.radians(dec0)), s["decDeg"] - dec0))
    XY = [(-p[0], -p[1]) for p in pts]
    xs = [p[0] for p in XY]
    ys = [p[1] for p in XY]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    XY = [((p[0] - min(xs)) / span, (p[1] - min(ys)) / span) for p in XY]
    return XY, chirality(XY)


def compactness(const):
    """形状紧凑度 = 归一化后短边/长边（1 = 方正、越小越细长）。用于大盘名额分配。"""
    canon, _ = canonical_shape(const["stars"])
    xs = [p[0] for p in canon]
    ys = [p[1] for p in canon]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    return (min(w, h) / max(w, h)) if max(w, h) > 0 else 0.0


def variants(canon):
    """canon（屏幕坐标 X,Y）→ 4 种「喂给 snap 的 (行向坐标, 列向坐标)」映射。

    snap 读 pts[0] 当行、pts[1] 当列（gm.snap 内部把两者写反了，这里按正确语义实现）：
      direct   ：(行, 列) = (Y, X)     direct_ra ：赤经镜像 (Y, 1-X)
      swap     ：(行, 列) = (X, Y)     swap_ra   ：换轴 + 赤经镜像 (1-X, Y)
    换轴/镜像的 8 种朝向在 transforms() 下会互相重复，调用方按键去重。
    """
    X = [p[0] for p in canon]
    Y = [p[1] for p in canon]
    Xm = [1.0 - x for x in X]
    return [
        ("direct", [(Y[i], X[i]) for i in range(len(X))]),
        ("direct_ra", [(Y[i], Xm[i]) for i in range(len(X))]),
        ("swap", [(X[i], Y[i]) for i in range(len(X))]),
        ("swap_ra", [(Xm[i], Y[i]) for i in range(len(X))]),
    ]


def greedy_snap(pts, anchor, mines, n, scale):
    """按 snap 规则从**指定锚点雷**出发的贪心吸附（pts 的 (行, 列) 语义同 variants）。

    每颗星吸到 1.6 格内最近的未占用雷；锚点 = 第一颗星所在的雷。
    返回 (吸附结果[按星序], 吸附代价) 或 (None, None)。snap_all 与 identify_fast
    共用这一份实现，保证「生成」与「反查」判据完全一致。
    """
    span = (n - 1) * scale
    px0, py0 = pts[0][1], pts[0][0]          # px=列, py=行
    mr, mc = anchor
    dy = mr - py0 * span
    dx = mc - px0 * span
    if abs(dy - round(dy)) > 0.34 or abs(dx - round(dx)) > 0.34:
        return None, None
    used, chosen, cost = set(), [], 0.0
    for (a, b) in pts:                        # a=行向, b=列向
        tr, tc = a * span + dy, b * span + dx
        cand, cd = None, 99.0
        for rc in mines:
            if rc in used:
                continue
            d2 = (rc[0] - tr) ** 2 + (rc[1] - tc) ** 2
            if d2 < cd:
                cd, cand = d2, rc
        if cand is None or cd > 2.6:          # 允许 ~1.6 格误差（与 gm.snap 一致）
            return None, None
        used.add(cand)
        chosen.append(cand)
        cost += cd
    rows = [p[0] for p in chosen]
    cols = [p[1] for p in chosen]
    if max(rows) - min(rows) < 1 or max(cols) - min(cols) < 1:
        return None, None                      # 退化成一团
    return chosen, cost


def snap_all(pts, mines, n, scale):
    """枚举所有合法贴法：以每颗雷为锚点各试一次，返回 [(chosen, cost), ...]（按 chosen 去重）。"""
    ms = list(mines)
    out, seen = [], set()
    for anchor in ms:
        chosen, cost = greedy_snap(pts, anchor, ms, n, scale)
        if not chosen:
            continue
        key = tuple(sorted(chosen))
        if key in seen:
            continue
        seen.add(key)
        out.append((chosen, cost))
    return out


def shape_score(rc, canon, line_set, scale, cost, n):
    """形状保真评分（越小越像）。

    判据 = 逐对距离一致度：贴好后 rc 的两两距离矩阵 vs 真实投影归一化的两两距离矩阵，
    各自除以自身均值后按权重求均方根差 dist_err（旋转/镜像/缩放无关，纯粹度量吸附扭曲；
    连线上的星对权重 ×2，因为玩家只看见线）。再叠加手性罚分、同段重复罚分、偏心罚分、
    偏向大图的微小奖励。返回 (total, mirror, dist_err, dup, off, scale)。
    """
    m = len(rc)
    if m < 2:
        return (9.9, 1, 9.9, 0, 1.0, scale)
    pr, sq = [], []
    for i in range(m):
        for j in range(i + 1, m):
            w = 2.0 if (i, j) in line_set else 1.0
            pr.append((math.hypot(rc[i][0] - rc[j][0], rc[i][1] - rc[j][1]), w))
            sq.append((math.hypot(canon[i][0] - canon[j][0], canon[i][1] - canon[j][1]), w))
    mr = sum(d for d, _ in pr) / len(pr)
    mt = sum(d for d, _ in sq) / len(sq)
    if mr <= 0 or mt <= 0:
        return (9.9, 1, 9.9, 0, 1.0, scale)
    num = sum(w * ((d / mr) - (d2 / mt)) ** 2 for (d, w), (d2, _) in zip(pr, sq))
    den = sum(w for _, w in pr)
    err = math.sqrt(num / den)
    # 手性：候选贴法的 (列, 行) = 屏幕 (X, Y)
    mir = 0 if chirality([(p[1], p[0]) for p in rc]) == chirality(canon) else 1
    segs = set()
    for (i, j) in line_set:
        segs.add(tuple(sorted((rc[i], rc[j]))))
    dup = max(0, len(line_set) - len(segs))
    cxs = sum(p[1] for p in rc) / m
    cys = sum(p[0] for p in rc) / m
    off = (abs(cxs - (n - 1) / 2) + abs(cys - (n - 1) / 2)) / n
    total = (err + MIRROR_PEN * mir + DUP_PEN * dup + OFF_PEN * off
             - SCALE_BONUS * scale + 0.0005 * cost)
    return (round(total, 5), mir, round(err, 5), dup, round(off, 4), scale)


def best_theme_strict(d, const, n, stop_dist):
    """在盘面的雷里找「最像真实形状且手性一致」的贴法。

    返回 ((total, mirror, dist_err, dup, off, scale), 带 theme 的 dict, meta) 或 None。
    与 51–88 的 best_theme 的差别：mirror != 0 的贴法直接丢弃（硬性禁止镜像），
    并且一旦 dist_err ≤ stop_dist（该尺寸的「足够好」标准）就立刻收手。
    """
    mines = [tuple(x) for x in d["mines"]]
    canon, _ = canonical_shape(const["stars"])
    line_set = {tuple(sorted(p)) for p in const["lines"]}
    combos, seen = [], set()
    for vname, pts in variants(canon):
        for oi, tp in enumerate(gm.transforms(pts)):
            key = tuple((round(a, 6), round(b, 6)) for a, b in tp)
            if key in seen:
                continue
            seen.add(key)
            combos.append((vname, oi, tp))
    best = None
    for vname, oi, tp in combos:
        for scale in SCALES:
            for chosen, cost in snap_all(tp, mines, n, scale):
                sc = shape_score(chosen, canon, line_set, scale, cost, n)
                if sc[1] != 0:                 # 手性必须与真实天图一致
                    continue
                if best is None or sc < best[0]:
                    best = (sc, chosen, {"variant": vname, "orient": oi, "scale": scale,
                                         "cost": round(cost, 3), "mirror": sc[1],
                                         "dist_err": sc[2], "dup": sc[3]})
                    if sc[2] <= stop_dist:
                        break
            if best is not None and best[0][2] <= stop_dist:
                break
        if best is not None and best[0][2] <= stop_dist:
            break
    if best is None:
        return None
    sc, chosen, meta = best
    d2 = gm.attach_theme(d, const["en"], const["stars_game"], const["lines"], chosen, n, const["zh"])
    if not d2:
        return None
    return sc, d2, meta


# ---------------------------------------------------------------- 盘面工具
def filled(ms, n):
    return (all(any((r, c) in ms for c in range(n)) for r in range(n)) and
            all(any((r, c) in ms for r in range(n)) for c in range(n)))


def isolated(ms, n):
    return f.isolated_mines({"mines": [list(x) for x in ms]}, n)


# ---------------------------------------------------------------- 生成单题
def make_question(const, n, rng, budget, stop_dist, camp_mines, tag=""):
    """造一道题：盘面优先 + 形状保真。返回 (level, meta, info, stats) 或 (None, ..., reasons)。"""
    k = int(round(DENS[n] * n * n))
    pl = {"lid": 0, "zh": const["zh"], "size": n, "teach": ""}
    t0 = time.time()
    attempts = boards = 0
    best = None
    reasons = {"filled": 0, "iso": 0, "camp": 0, "build": 0, "check": 0, "theme": 0}
    while time.time() - t0 < budget and attempts < MAX_ATTEMPTS:
        attempts += 1
        ms = gm.gen_layout(n, k, rng)
        if not filled(ms, n):
            reasons["filled"] += 1
            continue
        if isolated(ms, n) > 2:
            reasons["iso"] += 1
            continue
        if camp_mines and frozenset(ms) == camp_mines:
            reasons["camp"] += 1
            continue
        d = gm.build_level(pl, ms, const["en"], const["stars_game"], const["lines"], n)
        if d is None:
            reasons["build"] += 1
            continue
        ok, _probs, info = gl.check_level(d, static=False)
        if not ok or info["nb_only_ok"] is not False or info["runs_cells"] < 3:
            reasons["check"] += 1
            continue
        boards += 1
        got = best_theme_strict(d, const, n, stop_dist)
        if not got:
            reasons["theme"] += 1
            continue
        sc, d2, meta = got
        if best is None or sc < best[0]:
            best = (sc, d2, meta, info)
        if sc[2] <= stop_dist:
            break
    stats = {"attempts": attempts, "boards": boards, "seconds": round(time.time() - t0, 2),
             "reasons": reasons, "k": k}
    if best is None:
        return None, None, None, stats
    sc, d2, meta, info = best
    meta["attempts"] = attempts
    meta["boards"] = boards
    meta["seconds"] = stats["seconds"]
    meta["camp_mines"] = len(camp_mines) if camp_mines else 0
    return d2, meta, info, stats


def size_budget(n, args):
    """该尺寸的每题搜索预算：--budget>0 时统一覆盖，否则用 SIZE_BUDGET 表 × --scale。"""
    base = args.budget if args.budget > 0 else SIZE_BUDGET[n]
    return base * args.scale


def build_const(consts, cid):
    c = [x for x in consts if x["id"] == cid][0]
    f.FACTS.setdefault(c["en"], c["fact"])
    gm.f.FACTS.setdefault(c["en"], c["fact"])   # gm 内部另有一份 fit 模块实例
    return {"id": c["id"], "zh": c["zh"], "en": c["en"], "stars": c["stars"],
            "lines": c["lines"],
            "stars_game": [(s["zh"], s["en"], (0.0, 0.0), s["mag"]) for s in c["stars"]]}


def campaign_mines():
    levels = json.load(open(LEVELS_JSON, encoding="utf-8"))
    return {x["theme"]["id"]: frozenset(tuple(m) for m in x["mines"]) for x in levels}


# ---------------------------------------------------------------- 主生成
def main_generate(args):
    consts = json.load(open(CONST_JSON, encoding="utf-8"))
    order = [c["id"] for c in consts]
    const_by_id = {c["id"]: c for c in consts}
    camp = campaign_mines()
    rngs = {n: random.Random(args.seed + n * 1000) for n in sorted(DENS)}
    picked = {}          # size -> {cid: (level, meta, info)}
    remaining = list(order)
    t_all = time.time()

    if args.debug:
        # 调试：只跑指定尺寸的前 N 个星座，不写产物
        n = args.debug
        for cid in order[:args.limit]:
            const = build_const(consts, cid)
            got = make_question(const, n, rngs[n], size_budget(n, args),
                                STOP_DIST[n], camp.get(cid), cid)
            if got[0] is None:
                print("  ! %s n=%d 未生成 %s" % (const["zh"], n, got[3]), flush=True)
            else:
                _d, meta, info, st = got
                print("  %s n=%d dist=%.3f %s/%d/%.2f runs=%d 探格=%d 盘面=%d 尝试=%d %.2fs"
                      % (const["zh"], n, meta["dist_err"], meta["variant"], meta["orient"],
                         meta["scale"], info["runs_cells"], info["reveal_actions"],
                         st["boards"], st["attempts"], st["seconds"]), flush=True)
        return 0

    # --- 小盘 6–9：逐级分配（每级让**全部**剩余星座都试一次，再按 dist_err 挑最好的 22 个）---
    for n in SMALL:
        quota = QUOTA[n]
        budget = size_budget(n, args)
        got = {}
        rounds = 0
        while len(got) < quota and rounds < args.rounds:
            rounds += 1
            t0 = time.time()
            for cid in remaining:
                if cid in got:
                    continue
                const = build_const(consts, cid)
                res = make_question(const, n, rngs[n], budget, STOP_DIST[n], camp.get(cid), cid)
                if res[0] is not None:
                    got[cid] = res
            print("  [%d×%d] 第 %d 轮：候选 %d/%d，用时 %.1fs（预算 %.2fs/题）"
                  % (n, n, rounds, len(got), quota, time.time() - t0, budget), flush=True)
            if len(got) >= quota:
                break
            budget *= 1.6
        if len(got) < quota:
            print("!! [%d×%d] 只凑出 %d 题（需要 %d）——配额优先，报错退出" % (n, n, len(got), quota),
                  flush=True)
            return 1
        ranked = sorted(got.items(), key=lambda kv: (kv[1][1]["dist_err"], order.index(kv[0])))
        picked[n] = {cid: res for cid, res in ranked[:quota]}
        remaining = [cid for cid in remaining if cid not in picked[n]]
        print("  [%d×%d] 定档 %d 题，dist_err %.3f–%.3f；剩余星座 %d"
              % (n, n, quota, ranked[0][1][1]["dist_err"], ranked[quota - 1][1][1]["dist_err"],
                 len(remaining)), flush=True)

    # --- 大盘 10/11：每颗星座都要有第二题；10×10 的 22 个名额给「紧凑度排名 % 4 == 3」的星座 ---
    rank = {cid: i for i, cid in enumerate(
        sorted(order, key=lambda cid: (-compactness(const_by_id[cid]), order.index(cid))))}
    big10 = {cid for cid in order if rank[cid] % 4 == 3}
    assert len(big10) == QUOTA[10], len(big10)
    for n in LARGE:
        want = [cid for cid in order if (cid in big10) == (n == 10)]
        budget = size_budget(n, args)
        got = {}
        rounds = 0
        while len(got) < len(want) and rounds < args.rounds:
            rounds += 1
            t0 = time.time()
            for cid in want:
                if cid in got:
                    continue
                const = build_const(consts, cid)
                res = make_question(const, n, rngs[n], budget, STOP_DIST[n], camp.get(cid), cid)
                if res[0] is not None:
                    got[cid] = res
            print("  [%d×%d] 第 %d 轮：%d/%d，用时 %.1fs（预算 %.2fs/题）"
                  % (n, n, rounds, len(got), len(want), time.time() - t0, budget), flush=True)
            if len(got) >= len(want):
                break
            budget *= 1.6
        if len(got) < len(want):
            miss = [cid for cid in want if cid not in got]
            print("!! [%d×%d] 缺 %d 题：%s —— 配额优先，报错退出"
                  % (n, n, len(miss), miss), flush=True)
            return 1
        picked[n] = got

    # --- 覆盖率自检：每个星座必须正好一题小盘 + 一题大盘 ---
    got_small = {cid for n in SMALL for cid in picked[n]}
    got_large = {cid for n in LARGE for cid in picked[n]}
    if got_small != set(order) or got_large != set(order):
        print("!! 覆盖不全：缺小盘 %s；缺大盘 %s"
              % (sorted(set(order) - got_small), sorted(set(order) - got_large)), flush=True)
        return 1

    # --- 组装：按尺寸 6→11、尺寸内按 constellations88 顺序编号 1..176 ---
    levels, metas, infos = [], {}, {}
    lid = 0
    for n in sorted(DENS):
        for cid in order:
            res = picked[n].get(cid)
            if not res:
                continue
            d2, meta, info, _st = res
            lid += 1
            d2["id"] = lid
            d2["name"] = "%s · %d×%d" % (d2["theme"]["name"], n, n)
            d2["technique"] = TECHNIQUE
            d2["showRuns"] = True
            d2["lives"] = 3
            d2["teach"] = ""
            out = {key: d2[key] for key in FIELDS}
            levels.append(out)
            metas[lid] = meta
            infos[lid] = info
            print("题 %3d %-6s %2d×%-2d dist=%.3f %-9s 朝向%d scale=%.2f | 雷%2d 探格%2d 数织%2d "
                  "孤立%d | 盘面%d 尝试%d %.2fs"
                  % (lid, out["theme"]["name"], n, n, meta["dist_err"], meta["variant"],
                     meta["orient"], meta["scale"], len(out["mines"]), info["reveal_actions"],
                     info["runs_cells"], isolated(out["mines"], n), meta["boards"],
                     meta["attempts"], meta["seconds"]), flush=True)

    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(levels, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\n已写出 %s（%d 题，%d 字节，总用时 %.1fs）"
          % (OUT_JSON, len(levels), os.path.getsize(OUT_JSON), time.time() - t_all), flush=True)
    render_png(levels, OUT_PNG)
    return 0


# ---------------------------------------------------------------- 复核
def identify_fast(rc, mines, const, n):
    """反查 rc 是哪些（映射 × 朝向 × 缩放）的合法吸附结果。

    合法吸附的 chosen[0] 必然等于锚点雷（snap_all 的平移把它精确送到锚点，
    其它雷距离 ≥ 0.66 格），所以只需对 anchor = rc[0] 复算一次贪心吸附，
    不必枚举全部锚点 —— 结果与 snap_all 完全一致，只是快 k 倍。
    """
    want = tuple(sorted(tuple(p) for p in rc))
    anchor = tuple(rc[0])
    canon, _ = canonical_shape(const["stars"])
    hits = []
    for vname, pts in variants(canon):
        for oi, tp in enumerate(gm.transforms(pts)):
            for scale in SCALES:
                chosen, _cost = greedy_snap(tp, anchor, mines, n, scale)
                if chosen and tuple(sorted(chosen)) == want:
                    hits.append((vname, oi, scale))
    return hits


def check_theme(d, const):
    probs = []
    st = d["theme"]["stars"]
    ms = {tuple(x) for x in d["mines"]}
    if [list(p) for p in d["theme"]["lines"]] != [list(p) for p in const["lines"]]:
        probs.append("theme.lines 与 constellations88 不一致")
    if d["theme"]["id"] != const["id"]:
        probs.append("theme.id %s != %s" % (d["theme"]["id"], const["id"]))
    if d["theme"]["name"] != const["zh"]:
        probs.append("theme.name 不是 %s" % const["zh"])
    if d["theme"]["nameEn"] != const["en"]:
        probs.append("theme.nameEn 不是 %s" % const["en"])
    if not d["theme"].get("fact"):
        probs.append("theme.fact 为空")
    if len(st) != len(const["stars"]):
        probs.append("星数 %d != %d" % (len(st), len(const["stars"])))
    rcs = [tuple(s["rc"]) for s in st]
    if len(set(rcs)) != len(rcs):
        probs.append("星位重复")
    for s in st:
        if tuple(s["rc"]) not in ms:
            probs.append("星 %s 不在雷上" % s["name"])
    for i, s in enumerate(st):
        if i < len(const["stars"]) and (s["name"] != const["stars"][i]["zh"]
                                        or s["en"] != const["stars"][i]["en"]):
            probs.append("第 %d 颗星与 constellations88 不符" % i)
    want_noise = sorted(ms - set(rcs))
    if sorted(tuple(x) for x in d["noise"]) != want_noise:
        probs.append("noise != mines - stars")
    for (a, b) in d["theme"]["lines"]:
        if not (0 <= a < len(st) and 0 <= b < len(st)) or a == b:
            probs.append("lines 下标越界/自环 %s" % ((a, b),))
    return probs


def png_size(path):
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def main_verify(args):
    consts = json.load(open(CONST_JSON, encoding="utf-8"))
    byid = {c["id"]: c for c in consts}
    order = [c["id"] for c in consts]
    camp = campaign_mines()
    bank = json.load(open(OUT_JSON, encoding="utf-8"))
    hard = []
    per_size = {n: {"n": 0, "dens": [], "runs": [], "iso": [], "dist": [], "rev": [], "hit": 0,
                    "nb_true": 0} for n in DENS}
    per_const = {}
    variants, orients, scales = {}, {}, {}
    chir_ok = 0
    camp_dup = bank_dup = 0
    mine_sets = {}
    print("%4s %-6s %-14s %4s %6s %6s %5s %4s %4s %6s %5s %-10s"
          % ("题号", "星座", "name", "size", "雷/密度", "探格", "runs", "孤立", "镜像", "dist", "手性", "贴法"))
    print("-" * 108)
    for d in bank:
        lid = d["id"]
        n = d["size"]
        tid = d["theme"]["id"]
        const = byid.get(tid)
        if const is None:
            hard.append("题 %d theme.id=%s 不在 constellations88" % (lid, tid))
            continue
        ms = {tuple(x) for x in d["mines"]}
        dens = len(ms) / (n * n)
        ok, probs, info = gl.check_level(d, static=False)
        iso = isolated(d["mines"], n)
        empty_r = sum(1 for r in range(n) if not any((r, c) in ms for c in range(n)))
        empty_c = sum(1 for c in range(n) if not any((r, c) in ms for r in range(n)))
        # --- 形状（从产物独立复算）---
        canon, canon_ch = canonical_shape(const["stars"])
        line_set = {tuple(sorted(p)) for p in const["lines"]}
        rc = [tuple(s["rc"]) for s in d["theme"]["stars"]]
        sc = shape_score(rc, canon, line_set, 1.0, 0.0, n)
        screen_ch = chirality([(p[1], p[0]) for p in rc])
        hits = identify_fast(rc, [tuple(x) for x in d["mines"]], const, n)
        for (v, o, s) in hits:
            variants[v] = variants.get(v, 0) + 1
            orients[o] = orients.get(o, 0) + 1
            scales[s] = scales.get(s, 0) + 1
        if screen_ch == canon_ch and sc[1] == 0:
            chir_ok += 1
        # --- 硬性验收 ---
        if sorted(d.keys()) != sorted(FIELDS):
            hard.append("题 %d 字段集不符：%s" % (lid, sorted(d.keys())))
        if d["name"] != "%s · %d×%d" % (const["zh"], n, n):
            hard.append("题 %d name=%r 不符" % (lid, d["name"]))
        if not ok:
            hard.append("题 %d check_level 失败：%s" % (lid, probs))
        if info["nb_only_ok"] is not False:
            hard.append("题 %d nb_only_ok=%s（不是必须用数织）" % (lid, info["nb_only_ok"]))
        if info["runs_cells"] < 3:
            hard.append("题 %d runs_cells=%d < 3" % (lid, info["runs_cells"]))
        if iso > 2:
            hard.append("题 %d 孤立雷 %d > 2" % (lid, iso))
        if empty_r or empty_c:
            hard.append("题 %d 空行 %d / 空列 %d" % (lid, empty_r, empty_c))
        if abs(dens - DENS[n]) > 0.01:
            hard.append("题 %d 密度 %.4f 偏离设计 %.2f 超 ±0.01" % (lid, dens, DENS[n]))
        if (d["showRuns"] is not True or d["lives"] != 3 or d["technique"] != TECHNIQUE
                or d["teach"] != "" or "timeK" in d):
            hard.append("题 %d showRuns/lives/technique/teach/timeK 不符" % lid)
        if sc[1] != 0:
            hard.append("题 %d 手性与真实天图相反（镜像）" % lid)
        if not hits:
            hard.append("题 %d 贴法反查不到（rc 不是任何一种映射/朝向/缩放的合法吸附）" % lid)
        for pr in check_theme(d, const):
            hard.append("题 %d %s" % (lid, pr))
        if frozenset(ms) == camp.get(tid):
            camp_dup += 1
            hard.append("题 %d 与 campaign 同星座盘面矿点完全相同" % lid)
        if frozenset(ms) in mine_sets:
            bank_dup += 1
            hard.append("题 %d 与题 %d 盘面完全相同" % (lid, mine_sets[frozenset(ms)]))
        mine_sets[frozenset(ms)] = lid
        per_size[n]["n"] += 1
        per_size[n]["dens"].append(dens)
        per_size[n]["runs"].append(info["runs_cells"])
        per_size[n]["iso"].append(iso)
        per_size[n]["dist"].append(sc[2])
        per_size[n]["rev"].append(info["reveal_actions"])
        per_size[n]["hit"] += 1 if hits else 0
        per_size[n]["nb_true"] += 1 if info["nb_only_ok"] is not False else 0
        per_const.setdefault(tid, []).append((lid, n, sc[2], frozenset(ms), len(ms)))
        print("%4d %-6s %-14s %4d %3d/%.3f %6d %5d %4d %4d %6.3f %5s %-10s"
              % (lid, const["zh"], d["name"], n, len(ms), dens, info["reveal_actions"],
                 info["runs_cells"], iso, sc[1], sc[2], {0: "一致", 1: "相反"}.get(sc[1], "?"),
                 (hits[0][0] if hits else "-")))
    print("-" * 108)
    # --- 配额 / 覆盖 ---
    print("逐尺寸统计（配额 / 实际 / 密度设计→实测 / runs_cells / 孤立雷 / dist_err / 探格 / 反查贴法）：")
    for n in sorted(DENS):
        s = per_size[n]
        if not s["n"]:
            continue
        ds = sorted(s["dens"])
        de = sorted(s["dist"])
        print("  %2d×%-2d 配额%3d 实际%3d | 密度 %.3f→%.4f–%.4f | runs %d–%d | 孤立 %s | "
              "dist %.3f/%.3f/%.3f | 探格 %d–%d | 反查到贴法 %d/%d"
              % (n, n, QUOTA[n], s["n"], DENS[n], ds[0], ds[-1], min(s["runs"]), max(s["runs"]),
                 dict(sorted((x, s["iso"].count(x)) for x in set(s["iso"]))),
                 de[0], de[len(de) // 2], de[-1], min(s["rev"]), max(s["rev"]), s["hit"], s["n"]))
    all_dens = [v for n in DENS for v in per_size[n]["dens"]]
    all_dist = sorted(v for n in DENS for v in per_size[n]["dist"])
    print("总题数 %d（应为 176）；星座覆盖 %d/88" % (len(bank), len(per_const)))
    if sorted(x["id"] for x in bank) != list(range(1, len(bank) + 1)):
        hard.append("id 不是 1..176 连续")
    bad_cov = [cid for cid in order if len(per_const.get(cid, [])) != 2]
    if bad_cov:
        hard.append("星座覆盖不是每个 2 题：%s" % bad_cov)
    print("每个星座两题尺寸都不同：%d/%d；两题同尺寸的星座：%s"
          % (sum(1 for v in per_const.values() if len({x[1] for x in v}) == len(v)),
             len(per_const),
             {cid: [(x[0], x[1]) for x in v] for cid, v in per_const.items()
              if len({x[1] for x in v}) != len(v)} or "无"))
    print("两题的盘面矿点不同：%d/%d；矿点相同的星座：%s"
          % (sum(1 for v in per_const.values() if len({x[3] for x in v}) == len(v)),
             len(per_const),
             {cid: v for cid, v in per_const.items() if len({x[3] for x in v}) != len(v)} or "无"))
    print("与 campaign 同星座盘面矿点重复：%d 题（应为 0）；题库内部盘面重复：%d 题"
          % (camp_dup, bank_dup))
    bad_split = {cid: sorted(x[1] for x in v) for cid, v in per_const.items()
                 if not (len(v) == 2 and 6 <= min(x[1] for x in v) <= 9
                         and 10 <= max(x[1] for x in v) <= 11)}
    if bad_split:
        hard.append("不是「一题小盘 6–9 + 一题大盘 10–11」：%s" % bad_split)
    print("每个星座「一题小盘 6–9 + 一题大盘 10–11」：%s"
          % ("全部 88 个星座满足" if not bad_split else bad_split))
    print("贴法反查：映射 %s" % dict(sorted(variants.items())))
    print("          朝向 %s（左右各计一次：一个 rc 可能同时被多种映射/朝向复现）"
          % dict(sorted(orients.items())))
    print("          scale %s" % dict(sorted(scales.items())))
    print("手性一致（屏幕手性 == 真实天图手性）%d/%d = %.1f%%"
          % (chir_ok, len(bank), 100.0 * chir_ok / max(1, len(bank))))
    print("dist_err：min %.3f / 中位 %.3f / 均值 %.3f / max %.3f"
          % (all_dist[0], all_dist[len(all_dist) // 2],
             sum(all_dist) / len(all_dist), all_dist[-1]))
    nb_true = sum(per_size[n]["nb_true"] for n in DENS)
    print("nb_only_ok 为 True 的题数：%d（必须是 0）" % nb_true)
    runs_lo = min(min(per_size[n]["runs"]) for n in DENS if per_size[n]["n"])
    runs_hi = max(max(per_size[n]["runs"]) for n in DENS if per_size[n]["n"])
    print("runs_cells 范围：%d–%d（须 ≥3）" % (runs_lo, runs_hi))
    isos = [v for n in DENS for v in per_size[n]["iso"]]
    print("孤立雷分布：%s（须 ≤2）" % dict(sorted((x, isos.count(x)) for x in set(isos))))
    print("密度实测：%d 题全部在设计值 ±0.01 内（共 %d 题）"
          % (sum(1 for n in DENS for v in per_size[n]["dens"] if abs(v - DENS[n]) <= 0.01),
             len(all_dens)))
    print("字节数 %d；PNG 尺寸 %s" % (os.path.getsize(OUT_JSON),
                                    png_size(OUT_PNG) or "（未生成）"))
    print("共 %d 题；硬失败 %d 项" % (len(bank), len(hard)))
    for h in hard:
        print("  ✗ " + h)
    return 1 if hard else 0


# ---------------------------------------------------------------- 核对图
def render_png(levels, path):
    from PIL import Image, ImageDraw, ImageFont
    cols, cell, gap, margin, header = 15, 160, 6, 20, 68
    rows = (len(levels) + cols - 1) // cols
    W = margin * 2 + cols * cell + (cols - 1) * gap
    H = header + margin * 2 + rows * cell + (rows - 1) * gap
    assert W <= 2600, "核对图总宽 %d 超 2600" % W
    assert cell >= 110, "每格 %d 小于 110" % cell
    img = Image.new("RGB", (W, H), "white")
    dr = ImageDraw.Draw(img)

    def font(size, bold=False):
        for p in ((r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc"),
                  r"C:\Windows\Fonts\simhei.ttf"):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
        return ImageFont.load_default()

    f_name, f_sub, f_head = font(19, True), font(14), font(24, True)
    dr.text((margin, 14), "《星织 Asterweave》无尽模式专用题库 · 176 题星座形状核对"
                          "（每格画 theme.stars[].rc 与 theme.lines）",
            font=f_head, fill="#111827")
    dr.text((margin, 46), "浅底深线、棋盘为方形（上与真实天图同手性，不是镜像）；"
                          "标题 = 星座中文名，第二行 = 盘面尺寸与题号；点越大越亮（视星等）。",
            font=f_sub, fill="#5A6478")
    box = 110                     # 棋盘画成正方形（保持投影长宽比 = 形状不被拉伸）
    for idx, d in enumerate(levels):
        r, c = divmod(idx, cols)
        x0 = margin + c * (cell + gap)
        y0 = header + margin + r * (cell + gap)
        n = d["size"]
        dr.rectangle([x0, y0, x0 + cell, y0 + cell], outline="#C9CFDA", width=1)
        dr.text((x0 + 8, y0 + 5), d["theme"]["name"], font=f_name, fill="#111827")
        dr.text((x0 + 8, y0 + 27), "%d×%d · 题号 %d" % (n, n, d["id"]), font=f_sub, fill="#4B5768")
        bx, by = x0 + (cell - box) // 2, y0 + cell - box - 5
        dr.rectangle([bx, by, bx + box, by + box], fill="#FBFCFE", outline="#DCE1E8", width=1)
        step = box / n
        for i in range(1, n):
            dr.line([bx + i * step, by, bx + i * step, by + box], fill="#EDF0F5", width=1)
            dr.line([bx, by + i * step, bx + box, by + i * step], fill="#EDF0F5", width=1)
        rc = [(s["rc"][0], s["rc"][1]) for s in d["theme"]["stars"]]

        def ctr(i):
            return (bx + (rc[i][1] + 0.5) * step, by + (rc[i][0] + 0.5) * step)

        for (a, b) in d["theme"]["lines"]:
            dr.line([ctr(a), ctr(b)], fill="#2B3A55", width=3)
        for i, s in enumerate(d["theme"]["stars"]):
            px, py = ctr(i)
            mag = float(s["mag"])
            rad = step * max(0.30, min(0.46, 0.30 + (6.0 - mag) * 0.045))
            dr.ellipse([px - rad - 1.5, py - rad - 1.5, px + rad + 1.5, py + rad + 1.5], fill="white")
            fill = "#0E1B33" if mag <= 3.0 else ("#26375A" if mag <= 4.5 else "#5A6B8C")
            dr.ellipse([px - rad, py - rad, px + rad, py + rad], fill=fill, outline="#0B1526", width=1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print("已写出 %s（%dx%d，%d 格，每格 %d×%d、棋盘 %d×%d，%d 字节）"
          % (path, W, H, len(levels), cell, cell, box, box, os.path.getsize(path)), flush=True)


def main_png(args):
    levels = json.load(open(OUT_JSON, encoding="utf-8"))
    render_png(levels, OUT_PNG)
    return 0


def main():
    ap = argparse.ArgumentParser(description="生成无尽模式专用题库（88 星座 × 2 盘面 = 176 题）")
    ap.add_argument("--verify", action="store_true", help="只复核 tools/endless_bank_full.json")
    ap.add_argument("--png", action="store_true", help="只按已有 JSON 重画核对图")
    ap.add_argument("--debug", type=int, default=0, help="只跑指定尺寸的前 --limit 个星座（不写产物）")
    ap.add_argument("--limit", type=int, default=6, help="--debug 的星座个数")
    ap.add_argument("--budget", type=float, default=0.0,
                    help="每题搜索时间上限（秒）；>0 时覆盖 SIZE_BUDGET 表（默认 0 = 按尺寸表）")
    ap.add_argument("--scale", type=float, default=1.0, help="全部预算的缩放系数")
    ap.add_argument("--rounds", type=int, default=6, help="某一档配额凑不够时的加预算重试轮数")
    ap.add_argument("--seed", type=int, default=20261026)
    args = ap.parse_args()
    if args.verify:
        return main_verify(args)
    if args.png:
        return main_png(args)
    return main_generate(args)


if __name__ == "__main__":
    sys.exit(main())
