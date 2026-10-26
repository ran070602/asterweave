#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《星织 Asterweave》第 51–88 关（38 关）—— 盘面优先 + 真实星座形状保真。

设计（用户 2026-10-26 拍板）：
  * 51–60：11×11，雷密度 0.25，探格目标 45→52，timeK = 1.28
  * 61–74：11×11，雷密度 0.26，探格目标 48→56，timeK = 1.20
  * 75–88：11×11，雷密度 0.27，探格目标 52→60，timeK = 1.12
  星座 = tools/constellations88.json 里**尚未被第 1–50 关用过**的 38 个，按该文件
  （按英文名排序）的顺序依次配给第 51–88 关。

流程（沿用 tools/gen_difficulty_first.py 的「盘面优先」思路）：
  1. gen_layout() 造盘面 → 空行/空列 = 0、孤立雷 ≤2、雷数 = round(dens·n²)；
  2. gm.build_level() 定 opening（开局展开最多且 ≤38% 盘的 0 格）；
  3. gl.check_level(d, static=False) 验收：ok、nb_only_ok 必须为 False（**必须用数织**）、
     runs_cells ≥ 3、reveal_actions 落在本关设计的探格区间内、0 格比例 ≤ 0.38；
  4. 星座「贴」到雷上：把真实 ra/dec 做球面投影归一化成 pts_norm，遍历
     「4 种坐标映射（换轴 × 赤经镜像）× 8 种旋转/翻转 × 4 档缩放」，
     枚举所有合法吸附（每颗星吸到 1.6 格内最近的未占用雷），
     用**形状保真评分**挑最像真实星座的一种（见 shape_score 的注释）；
  5. gm.attach_theme() 生成 theme（stars[].rc = 盘面格坐标、lines 来自 constellations88
     的下标对），星必须落在雷上且互不重复。

产物（只写这三个）：
  tools/levels_51_88.json          38 条关卡（id 51–88）
  docs/星座形状核对_51-88.png       38 格星座形状核对图（白底深色线）

用法：
  python tools/gen_levels_51_88.py                # 生成 + 写 JSON + 画核对图
  python tools/gen_levels_51_88.py --verify       # 只复核已有 JSON（权威验收 + 逐关表）
  python tools/gen_levels_51_88.py --png          # 只按已有 JSON 重画核对图
  python tools/gen_levels_51_88.py --only 51,52   # 只生成指定关（调试）
  python tools/gen_levels_51_88.py --budget 45 --seed 20261026
"""
import argparse
import importlib.util
import json
import math
import os
import random
import re
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
OUT_JSON = os.path.join(ROOT, "tools", "levels_51_88.json")
OUT_PNG = os.path.join(ROOT, "docs", "星座形状核对_51-88.png")

# ---------------------------------------------------------------- 难度曲线
CURVE = [
    # (首关, 末关, 雷密度, 探格起始, 探格结束, timeK)
    (51, 60, 0.25, 45, 52, 1.28),
    (61, 74, 0.26, 48, 56, 1.20),
    (75, 88, 0.27, 52, 60, 1.12),
]
PROBE_HALF = 3          # 探格设计区间 = 目标值 ±3（报告里如实给出）
FIELDS = ["id", "name", "size", "mines", "noise", "showRuns", "opening", "lives",
          "teach", "technique", "rowRuns", "colRuns", "theme", "timeK"]

# ---------------------------------------------------------------- 形状保真
SCALES = (0.62, 0.72, 0.82, 0.92)
MIRROR_PEN = 0.35       # 与真实天区手性相反时的固定罚分
DUP_PEN = 0.05          # 两条下标不同的连线画成同一段几何线时的罚分
OFF_PEN = 0.04          # 图形偏离盘面中心的罚分（除以 n）
SCALE_BONUS = 0.03      # 同等形状下偏向更大的图（更好认）
GREAT = 0.09            # dist_err 低于此值且不镜像 → 立即采用


def unit_vec(ra_h, dec_deg):
    ra, de = math.radians(ra_h * 15.0), math.radians(dec_deg)
    return (math.cos(de) * math.cos(ra), math.cos(de) * math.sin(ra), math.sin(de))


def canonical_shape(stars):
    """真实 ra/dec → 屏幕坐标 (X 右正, Y 下正) 的归一化形状。

    用星座质心处的**球面投影**（gnomonic，天区跨度小时与真实观感一致）：
      X = -east（天图上东在左），Y = -north（屏幕 Y 向下）。
    再平移 + 等比缩放到 [0,1]（保长宽比），保证 snap 的 span=(n-1)·scale 不拉伸形状。
    返回 (归一化点列, 手性符号)；手性 = 按星表顺序求 Σ cross(P_i - 质心, P_{i+1} - 质心) 的符号，
    旋转不变、镜像反号，用来判定贴法有没有被镜像。
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
        if cosc < 0.05:                     # 跨度过大，投影退化 → 退化成等距圆柱
            fallback = True
            break
        pts.append((sum(a * b for a, b in zip(u, east)) / cosc,
                    sum(a * b for a, b in zip(u, north)) / cosc))
    if fallback:                            # 退化兜底（本 38 个星座都不会触发）
        pts = []
        for s in stars:
            dl = (s["raH"] * 15.0 - math.degrees(ra0) + 180.0) % 360.0 - 180.0
            pts.append((dl * math.cos(math.radians(dec0)), s["decDeg"] - dec0))
    XY = [(-p[0], -p[1]) for p in pts]      # 东在左、北在上（屏幕坐标 Y 向下）
    xs = [p[0] for p in XY]
    ys = [p[1] for p in XY]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    XY = [((p[0] - min(xs)) / span, (p[1] - min(ys)) / span) for p in XY]
    return XY, chirality(XY)


def chirality(XY):
    m = len(XY)
    gx = sum(p[0] for p in XY) / m
    gy = sum(p[1] for p in XY) / m
    s = 0.0
    for i in range(m):
        a, b = XY[i], XY[(i + 1) % m]
        s += (a[0] - gx) * (b[1] - gy) - (a[1] - gy) * (b[0] - gx)
    return 1 if s > 0 else (-1 if s < 0 else 0)


def variants(canon):
    """canon（屏幕坐标 X,Y）→ 4 种「喂给 snap 的 (行向坐标, 列向坐标)」映射。

    snap 读 pts[0] 当行、pts[1] 当列（注意：gm.snap 内部把两者写反了，这里按正确语义实现）：
      direct     ：(行, 列) = (Y, X)  —— 即 (x 由赤经、y 由赤纬) 的原样映射
      direct_ra   ：赤经镜像（X → 1-X）
      swap       ：(行, 列) = (X, Y)  —— 换轴映射
      swap_ra     ：换轴 + 赤经镜像
    换轴/镜像的 8 种朝向在 transforms() 下会互相重复，调用方按键去重。
    """
    X = [p[0] for p in canon]
    Y = [p[1] for p in canon]
    Xm = [1.0 - x for x in X]
    out = [
        ("direct", [(Y[i], X[i]) for i in range(len(X))]),
        ("direct_ra", [(Y[i], Xm[i]) for i in range(len(X))]),
        ("swap", [(X[i], Y[i]) for i in range(len(X))]),
        ("swap_ra", [(Xm[i], Y[i]) for i in range(len(X))]),
    ]
    return out


def snap_all(pts, mines, n, scale):
    """枚举所有合法贴法。pts 的 (行, 列) 语义同 variants()。

    与 gm.snap 同规则（每颗星吸到 1.6 格内最近的未占用雷、以第一颗星所在雷为锚），
    区别有二：(a) 修正了 gm.snap 里行列写反的问题；(b) 不只返回 snap 自认为最好的一种，
    而是把每种锚点产生的合法贴法全部返回，交给 shape_score 挑最像真实星座的。
    """
    ms = list(mines)
    span = (n - 1) * scale
    out, seen = [], set()
    px0, py0 = pts[0][1], pts[0][0]          # px=列, py=行
    for (mr, mc) in ms:
        dy = mr - py0 * span
        dx = mc - px0 * span
        if abs(dy - round(dy)) > 0.34 or abs(dx - round(dx)) > 0.34:
            continue
        used, chosen, cost, ok = set(), [], 0.0, True
        for (a, b) in pts:                    # a=行向, b=列向
            tr, tc = a * span + dy, b * span + dx
            cand, cd = None, 99.0
            for rc in ms:
                if rc in used:
                    continue
                d2 = (rc[0] - tr) ** 2 + (rc[1] - tc) ** 2
                if d2 < cd:
                    cd, cand = d2, rc
            if cand is None or cd > 2.6:      # 允许 ~1.6 格误差（与 gm.snap 一致）
                ok = False
                break
            used.add(cand)
            chosen.append(cand)
            cost += cd
        if not ok:
            continue
        rows = [p[0] for p in chosen]
        cols = [p[1] for p in chosen]
        if max(rows) - min(rows) < 1 or max(cols) - min(cols) < 1:
            continue                          # 退化成一团
        key = tuple(sorted(chosen))
        if key in seen:
            continue
        seen.add(key)
        out.append((chosen, cost))
    return out


def shape_score(rc, canon, line_set, scale, cost, n):
    """形状保真评分（越小越像）。

    判据 = 逐对距离一致度：把「贴好后 rc 的两两距离矩阵」与「真实 ra/dec 投影后归一化的
    两两距离矩阵」各自除以自身均值，再按权重求均方根差 dist_err（旋转/镜像/缩放无关，
    因此纯粹度量「吸附到格子后被扭曲了多少」；连线上的星对权重 ×2，因为玩家只看见线）。
    再叠加：手性罚分（真实天图东在左，被镜像的贴法 +0.35）、同段重复罚分、
    偏心罚分、以及偏向大图的微小奖励（更好认）。
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


def best_theme(d, const, n):
    """在盘面的雷里给该星座找「最像真实形状」的贴法；返回 (score, 带 theme 的 dict, meta)。"""
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
                if best is None or sc < best[0]:
                    best = (sc, chosen, {"variant": vname, "orient": oi, "scale": scale,
                                         "cost": round(cost, 3), "mirror": sc[1],
                                         "dist_err": sc[2], "dup": sc[3]})
            if best and best[0][0] <= GREAT and best[0][1] == 0:
                break
        if best and best[0][0] <= GREAT and best[0][1] == 0:
            break
    if best is None:
        return None
    sc, chosen, meta = best
    d2 = gm.attach_theme(d, const["en"], const["stars_game"], const["lines"], chosen, n, const["zh"])
    if not d2:
        return None
    meta["rc"] = [tuple(p) for p in chosen]
    return sc, d2, meta


# ---------------------------------------------------------------- 计划
def build_plan():
    consts = json.load(open(CONST_JSON, encoding="utf-8"))
    levels = json.load(open(LEVELS_JSON, encoding="utf-8"))
    used = {x["theme"]["id"] for x in levels}
    rest = [c for c in consts if c["id"] not in used]
    plan = []
    for (lo, hi, dens, p0, p1, tk) in CURVE:
        span = hi - lo
        for lid in range(lo, hi + 1):
            t = int(round(p0 + (p1 - p0) * (lid - lo) / span)) if span else p0
            plan.append({"lid": lid, "dens": dens, "target": t,
                         "probes": (t - PROBE_HALF, t + PROBE_HALF), "timeK": tk})
    assert len(rest) == len(plan), "剩余星座 %d 个 != 待生成关卡 %d 个" % (len(rest), len(plan))
    for pl, c in zip(plan, rest):
        pl["const"] = {
            "id": c["id"], "zh": c["zh"], "en": c["en"],
            "stars": c["stars"], "lines": c["lines"],
            # gm.attach_theme 要的是 (中文名, 英文名, (x, y), mag) 形式，xy 不参与贴图
            "stars_game": [(s["zh"], s["en"], (0.0, 0.0), s["mag"]) for s in c["stars"]],
        }
        pl.update(size=11, teach="", technique="constellation", zh=c["zh"])
        # 让 attach_theme 直接产出 constellations88 里的科普文案（fit 里已有的 2 条旧文案优先）。
        # 注意 gm 模块内部**另有一份** fit_constellation_levels 的实例（gm.f），attach_theme 用的是它。
        f.FACTS.setdefault(c["en"], c["fact"])
        gm.f.FACTS.setdefault(c["en"], c["fact"])
    return plan


def filled(ms, n):
    return (all(any((r, c) in ms for c in range(n)) for r in range(n)) and
            all(any((r, c) in ms for r in range(n)) for c in range(n)))


def isolated(ms, n):
    return f.isolated_mines({"mines": [list(x) for x in ms]}, n)


# ---------------------------------------------------------------- 生成
def generate_one(pl, rng, budget, max_boards, log=print):
    n = pl["size"]
    k = int(round(pl["dens"] * n * n))
    lo, hi = pl["probes"]
    t0 = time.time()
    attempts = boards = 0
    best = None
    reasons = {"empty": 0, "iso": 0, "noopen": 0, "check": 0, "probe": 0, "zero": 0, "theme": 0}
    while time.time() - t0 < budget and attempts < 6000 and boards < max_boards:
        attempts += 1
        ms = gm.gen_layout(n, k, rng)
        if not filled(ms, n):
            reasons["empty"] += 1
            continue
        if isolated(ms, n) > 2:
            reasons["iso"] += 1
            continue
        d = gm.build_level(pl, ms, pl["const"]["en"], pl["const"]["stars_game"],
                           pl["const"]["lines"], n)
        if d is None:
            reasons["noopen"] += 1
            continue
        ok, _probs, info = gl.check_level(d, static=False)
        if not ok or info["nb_only_ok"] is not False:
            reasons["check"] += 1
            continue
        if info["runs_cells"] < 3:
            reasons["check"] += 1
            continue
        if not (lo <= info["reveal_actions"] <= hi):
            reasons["probe"] += 1
            continue
        zeros, zr = f.stats_of(d, n)
        if zr > 0.38:
            reasons["zero"] += 1
            continue
        boards += 1
        got = best_theme(d, pl["const"], n)
        if not got:
            reasons["theme"] += 1
            continue
        sc, d2, meta = got
        if best is None or sc < best[0]:
            best = (sc, d2, meta, info, zeros, zr)
        if sc[0] <= GREAT and sc[1] == 0:
            break
    if best is None:
        return None, attempts, boards, reasons, time.time() - t0
    sc, d2, meta, info, zeros, zr = best
    d2["timeK"] = pl["timeK"]
    out = {key: d2[key] for key in FIELDS}
    return (out, meta, info, zeros, zr, attempts, boards), attempts, boards, reasons, time.time() - t0


def main_generate(args):
    plan = build_plan()
    only = None
    if args.only:
        only = {int(x) for x in args.only.split(",") if x.strip()}
        plan = [p for p in plan if p["lid"] in only]
    rng = random.Random(args.seed)
    results, fails = [], []
    for pl in plan:
        max_boards = 20 if pl["target"] <= 52 else (14 if pl["target"] <= 56 else 10)
        got, attempts, boards, reasons, dt = generate_one(pl, rng, args.budget, max_boards)
        if not got:
            print("!! 第 %d 关 %s 未生成（尝试 %d、通过盘面 %d、%.1fs；%s）"
                  % (pl["lid"], pl["zh"], attempts, boards, dt, reasons), flush=True)
            fails.append(pl["lid"])
            continue
        out, meta, info, zeros, zr, attempts, boards = got
        results.append((pl, out, meta, info, zeros, zr))
        print("第 %2d 关 %-6s 星%d 贴法=%-9s 朝向%d scale=%.2f dist=%.3f 镜像%d | 雷%d 探格%d 数织%d 0格%.0f%% "
              "| 候选盘面%d 尝试%d %.1fs"
              % (pl["lid"], pl["zh"], len(pl["const"]["stars"]), meta["variant"], meta["orient"],
                 meta["scale"], meta["dist_err"], meta["mirror"], len(out["mines"]),
                 info["reveal_actions"], info["runs_cells"], zr * 100, boards, attempts, dt),
              flush=True)

    if args.only:
        print("\n（--only 模式：不写产物）")
        return 0 if not fails else 1

    levels = [r[1] for r in results]
    levels.sort(key=lambda x: x["id"])
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(levels, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\n已写出 %s（%d 关，%d 字节）" % (OUT_JSON, len(levels), os.path.getsize(OUT_JSON)))
    if fails:
        print("!! 未生成的关卡：%s" % fails)
    render_png(levels, OUT_PNG)
    return 1 if fails else 0


# ---------------------------------------------------------------- 复核
def identify(rc, mines, const, n):
    """从 theme.stars[].rc 反查出它对应哪种映射/朝向/缩放（复核用，独立于生成时的记录）。"""
    want = tuple(sorted(tuple(p) for p in rc))
    canon, _ = canonical_shape(const["stars"])
    hits = []
    for vname, pts in variants(canon):
        for oi, tp in enumerate(gm.transforms(pts)):
            for scale in SCALES:
                for chosen, _cost in snap_all(tp, mines, n, scale):
                    if tuple(sorted(chosen)) == want:
                        hits.append((vname, oi, scale))
                        break
    return hits


def check_theme(d, const):
    probs = []
    st = d["theme"]["stars"]
    ms = {tuple(x) for x in d["mines"]}
    if [tuple(p) for p in d["theme"]["lines"]] != [tuple(p) for p in const["lines"]]:
        probs.append("theme.lines 与 constellations88 不一致")
    if d["theme"]["id"] != const["id"]:
        probs.append("theme.id %s != %s" % (d["theme"]["id"], const["id"]))
    if d["theme"]["name"] != const["zh"]:
        probs.append("theme.name 不是 %s" % const["zh"])
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


def main_verify(args):
    plan = {p["lid"]: p for p in build_plan()}
    levels = json.load(open(OUT_JSON, encoding="utf-8"))
    hard, vstats = [], {}
    print("%3s %-6s %-26s %4s %6s %5s %6s %5s %4s %4s %6s %5s"
          % ("id", "星座", "name", "size", "雷/密度", "探格", "区间", "runs", "孤立", "镜像", "dist", "timeK"))
    print("-" * 112)
    seen_ids = set()
    for d in levels:
        lid = d["id"]
        pl = plan.get(lid)
        if pl is None:
            hard.append("第 %d 关不在 51–88 计划内" % lid)
            continue
        const = pl["const"]
        n = d["size"]
        ms = {tuple(x) for x in d["mines"]}
        dens = len(ms) / (n * n)
        ok, probs, info = gl.check_level(d, static=False)
        iso = isolated(d["mines"], n)
        empty_r = sum(1 for r in range(n) if not any((r, c) in ms for c in range(n)))
        empty_c = sum(1 for c in range(n) if not any((r, c) in ms for r in range(n)))
        # --- 形状保真（从产物独立复算）---
        canon, _ = canonical_shape(const["stars"])
        line_set = {tuple(sorted(p)) for p in const["lines"]}
        rc = [tuple(s["rc"]) for s in d["theme"]["stars"]]
        sc = shape_score(rc, canon, line_set, 1.0, 0.0, n)
        hits = identify(rc, [tuple(x) for x in d["mines"]], const, n)
        for h in hits:
            vstats.setdefault(h[0], set()).add(lid)
        # --- 硬性验收 ---
        if sorted(d.keys()) != sorted(FIELDS):
            hard.append("第 %d 关字段集不符：%s" % (lid, sorted(d.keys())))
        if d["name"] != "第 %d 关 · %s" % (lid, const["zh"]):
            hard.append("第 %d 关 name=%r 与 id/星座不符" % (lid, d["name"]))
        if not ok:
            hard.append("第 %d 关 check_level 失败：%s" % (lid, probs))
        if info["nb_only_ok"] is not False:
            hard.append("第 %d 关 nb_only_ok=%s（不是必须用数织）" % (lid, info["nb_only_ok"]))
        if info["runs_cells"] < 3:
            hard.append("第 %d 关 runs_cells=%d < 3" % (lid, info["runs_cells"]))
        if not (pl["probes"][0] <= info["reveal_actions"] <= pl["probes"][1]):
            hard.append("第 %d 关 探格 %d 不在设计区间 %s" % (lid, info["reveal_actions"], pl["probes"]))
        if iso > 2:
            hard.append("第 %d 关 孤立雷 %d > 2" % (lid, iso))
        if empty_r or empty_c:
            hard.append("第 %d 关 空行 %d / 空列 %d" % (lid, empty_r, empty_c))
        if abs(dens - pl["dens"]) > 0.01:
            hard.append("第 %d 关 密度 %.4f 偏离设计 %.2f 超过 ±0.01" % (lid, dens, pl["dens"]))
        if d["size"] != 11 or d["showRuns"] is not True or d["lives"] != 3 \
                or d["technique"] != "constellation" or d["teach"] != "":
            hard.append("第 %d 关 size/showRuns/lives/technique/teach 不符" % lid)
        if d["timeK"] != pl["timeK"]:
            hard.append("第 %d 关 timeK=%s != %s" % (lid, d["timeK"], pl["timeK"]))
        for pr in check_theme(d, const):
            hard.append("第 %d 关 %s" % (lid, pr))
        if not hits:
            hard.append("第 %d 关 贴法反查不到（rc 不是任何一种映射/朝向/缩放的合法吸附结果）" % lid)
        seen_ids.add(lid)
        print("%3d %-6s %-26s %4d %3d/%.3f %5d %6s %5d %4d %4d %6.3f %5s"
              % (lid, const["zh"], d["name"], n, len(ms), dens, info["reveal_actions"],
                 "%d-%d" % tuple(pl["probes"]), info["runs_cells"], iso, sc[1], sc[2], d["timeK"]))
    if seen_ids != set(range(51, 89)):
        hard.append("id 集合不是 51–88：缺 %s" % sorted(set(range(51, 89)) - seen_ids))
    print("-" * 112)
    print("贴法反查（一个 rc 可能同时被多种映射/朝向复现，此处按星座计次）：")
    for k in sorted(vstats):
        print("   %-10s %d 关" % (k, len(vstats[k])))
    print("共 %d 关；硬失败 %d 项" % (len(levels), len(hard)))
    for h in hard:
        print("  ✗ " + h)
    lo_d, hi_d = density_band()
    over = [x["id"] for x in levels if not (lo_d <= len(x["mines"]) / (x["size"] ** 2) * 100 <= hi_d)]
    over25 = [x["id"] for x in levels if len(x["mines"]) / (x["size"] ** 2) * 100 > 25]
    print("tools/check_levels.py 当前密度带 = [%g%%, %g%%] → 触发该警告：%d 关（%s…）"
          % (lo_d, hi_d, len(over), over[:6]))
    print("若仍按最初的 [15%%, 25%%] 带 → 会触发：%d 关（%s…）" % (len(over25), over25[:6]))
    print("这些关也会触发「没有图鉴数据（sky.json）」警告：%d 关（sky.json 目前只有 50 条，由另一会话扩展）"
          % len(seen_ids))
    return 1 if hard else 0


def density_band():
    """从 tools/check_levels.py 里读出它当前的密度阈值（另一会话可能已经调过）。"""
    try:
        src = open(os.path.join(ROOT, "tools", "check_levels.py"), encoding="utf-8").read()
        m = re.search(r"not\s*\(\s*(\d+(?:\.\d+)?)\s*<=\s*dens\s*<=\s*(\d+(?:\.\d+)?)\s*\)", src)
        if m:
            return float(m.group(1)), float(m.group(2))
    except OSError:
        pass
    return 15.0, 25.0


# ---------------------------------------------------------------- 核对图
def render_png(levels, path):
    from PIL import Image, ImageDraw, ImageFont
    n = levels[0]["size"] if levels else 11
    cols, cell, gap, margin, header = 7, 320, 10, 20, 56
    rows = (len(levels) + cols - 1) // cols
    W = margin * 2 + cols * cell + (cols - 1) * gap
    H = header + margin * 2 + rows * cell + (rows - 1) * gap
    assert W <= 2400, "核对图总宽 %d 超 2400" % W
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

    f_cell, f_head = font(23), font(30, True)
    dr.text((margin, 14), "《星织 Asterweave》第 51–88 关 星座形状核对（theme.stars[].rc + lines，n=%d）" % n,
            font=f_head, fill="#111827")
    box = cell - 56              # 每格棋盘边长
    pad = (cell - box) // 2
    step = box / n
    for idx, d in enumerate(levels):
        r, c = divmod(idx, cols)
        x0 = margin + c * (cell + gap)
        y0 = header + margin + r * (cell + gap)
        dr.rectangle([x0, y0, x0 + cell, y0 + cell], outline="#D5D9E0", width=2)
        title = "第 %d 关 · %s" % (d["id"], d["theme"]["name"])
        dr.text((x0 + 10, y0 + 12), title, font=f_cell, fill="#111827")
        bx, by = x0 + pad, y0 + 52
        dr.rectangle([bx, by, bx + box, by + box], outline="#E3E6EC", width=1)
        for i in range(1, n):
            dr.line([bx + i * step, by, bx + i * step, by + box], fill="#F1F3F7", width=1)
            dr.line([bx, by + i * step, bx + box, by + i * step], fill="#F1F3F7", width=1)
        rc = [(s["rc"][0], s["rc"][1]) for s in d["theme"]["stars"]]

        def ctr(i):
            return (bx + (rc[i][1] + 0.5) * step, by + (rc[i][0] + 0.5) * step)

        for (a, b) in d["theme"]["lines"]:
            dr.line([ctr(a), ctr(b)], fill="#3B4A63", width=4)
        for i, s in enumerate(d["theme"]["stars"]):
            px, py = ctr(i)
            rad = max(4.0, min(11.0, 4.0 + (6.0 - float(s["mag"])) * 1.15))
            dr.ellipse([px - rad - 2, py - rad - 2, px + rad + 2, py + rad + 2], fill="white")
            fill = "#0E1B33" if float(s["mag"]) <= 3.0 else ("#26375A" if float(s["mag"]) <= 4.5 else "#5A6B8C")
            dr.ellipse([px - rad, py - rad, px + rad, py + rad], fill=fill, outline="#0B1526", width=1)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print("已写出 %s（%dx%d，%d 格，%d 字节）" % (path, W, H, len(levels), os.path.getsize(path)))


def main_png(args):
    levels = json.load(open(OUT_JSON, encoding="utf-8"))
    render_png(levels, OUT_PNG)
    return 0


def main():
    ap = argparse.ArgumentParser(description="生成第 51–88 关（盘面优先 + 真实星座形状保真）")
    ap.add_argument("--verify", action="store_true", help="只复核 tools/levels_51_88.json")
    ap.add_argument("--png", action="store_true", help="只按已有 JSON 重画核对图")
    ap.add_argument("--only", default=None, help="只生成这些关（逗号分隔，调试用，不写产物）")
    ap.add_argument("--budget", type=float, default=45.0, help="每关搜索时间上限（秒）")
    ap.add_argument("--seed", type=int, default=20261026)
    args = ap.parse_args()
    if args.verify:
        return main_verify(args)
    if args.png:
        return main_png(args)
    return main_generate(args)


if __name__ == "__main__":
    sys.exit(main())
