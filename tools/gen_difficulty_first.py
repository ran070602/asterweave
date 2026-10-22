#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""难度优先的关卡生成器（v2 思路，用户 2026-10-22 指定）：

1. 先按"可玩性"定盘面：棋盘尺寸（≤11，手机友好）、雷密度、孤立雷、空行空列、0 区；
2. 用求解器验收该盘面"零猜测可解"；
3. **再从盘面里找出星座**：把星座图案做旋转/翻转/缩放后"贴"到已有的雷上（每颗星吸附到最近的一颗雷），
   贴上的那组雷就是 `theme.stars`，其余全部是杂星（`noise`）。
4. 星座只是"命名"一层，不改变难度。

输出：tools/levels_new.json（21 关之后的关卡）
"""
import importlib.util, json, math, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

gl = load("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
f = load("f", os.path.join(ROOT, "tools", "fit_constellation_levels.py"))

# ---------------------------------------------------------------- 星座池
POOL = {
    "摩羯座": ("Capricornus", f.CAPRICORNUS, f.CAPRICORNUS_L),
    "天鹤座": ("Grus", f.GRUS, f.GRUS_L),
    "凤凰座": ("Phoenix", f.PHOENIX, f.PHOENIX_L),
    "孔雀座": ("Pavo", f.PAVO, f.PAVO_L),
    "室女座": ("Virgo", f.VIRGO, f.VIRGO_L),
    "船底座": ("Carina", f.CARINA, f.CARINA_L),
    "宝瓶座": ("Aquarius", f.AQUARIUS, f.AQUARIUS_L),
    "双鱼座": ("Pisces", f.PISCES, f.PISCES_L),
    "蛇夫座": ("Ophiuchus", f.OPHIUCHUS, f.OPHIUCHUS_L),
    "长蛇座": ("Hydra", f.HYDRA, f.HYDRA_L),
    "天秤座": ("Libra", f.LIBRA, f.LIBRA_L),
}

# 21–30 关：先定难度（尺寸/密度/探格目标），再配星座
PLAN = [
    dict(lid=21, zh="摩羯座", size=9,  dens=0.18, probes=(22, 32), teach=""),
    dict(lid=22, zh="天鹤座", size=9,  dens=0.19, probes=(24, 34), teach=""),
    dict(lid=23, zh="凤凰座", size=10, dens=0.19, probes=(26, 36), teach=""),
    dict(lid=24, zh="孔雀座", size=10, dens=0.20, probes=(28, 38), teach=""),
    dict(lid=25, zh="室女座", size=10, dens=0.20, probes=(28, 40), teach=""),
    dict(lid=26, zh="船底座", size=11, dens=0.20, probes=(30, 42), teach=""),
    dict(lid=27, zh="宝瓶座", size=11, dens=0.21, probes=(30, 44), teach=""),
    dict(lid=28, zh="双鱼座", size=11, dens=0.21, probes=(32, 44), teach=""),
    dict(lid=29, zh="蛇夫座", size=11, dens=0.22, probes=(33, 46), teach=""),
    dict(lid=30, zh="长蛇座", size=11, dens=0.22, probes=(33, 46), teach=""),
]


def transforms(points):
    """归一化星位 → 旋转/翻转后的归一化坐标（保持 0..1）"""
    out = []
    for rot in (0, 90, 180, 270):
        for flip in (False, True):
            pts = []
            for (x, y) in points:
                if flip:
                    x = 1 - x
                a = math.radians(rot)
                # 以 (0.5,0.5) 为中心旋转，再平移到 0..1
                cx, cy = x - 0.5, y - 0.5
                nx = cx * math.cos(a) - cy * math.sin(a) + 0.5
                ny = cx * math.sin(a) + cy * math.cos(a) + 0.5
                pts.append((nx, ny))
            out.append(pts)
    return out


def snap(pts_norm, mines, n, scale):
    """把（已变换的）星位贴到雷上：每颗星吸附 1.5 格内最近的未占用雷。"""
    mines = list(mines)
    span = (n - 1) * scale
    best = None
    # 用每颗雷作为"第一颗星"的锚点，避免枚举所有平移
    for (mr, mc) in mines:
        for (px, py) in ((pts_norm[0][1], pts_norm[0][0]),):
            dy = mr - py * span
            dx = mc - px * span
            if abs(dy - round(dy)) > 0.34 or abs(dx - round(dx)) > 0.34:
                continue
            used, chosen, cost = set(), [], 0.0
            ok = True
            for (x, y) in pts_norm:
                tr, tc = y * span + dy, x * span + dx
                cand = None; cd = 99
                for (rr, cc) in mines:
                    if (rr, cc) in used:
                        continue
                    d2 = (rr - tr) ** 2 + (cc - tc) ** 2
                    if d2 < cd:
                        cd, cand = d2, (rr, cc)
                if cand is None or cd > 2.6:      # 允许 ~1.6 格误差
                    ok = False; break
                used.add(cand); chosen.append(cand); cost += cd
            if not ok:
                continue
            rows = [p[0] for p in chosen]; cols = [p[1] for p in chosen]
            if max(rows) - min(rows) < n * 0.4 or max(cols) - min(cols) < n * 0.4:
                continue                            # 太挤，不像星座
            cxs = sum(p[1] for p in chosen) / len(chosen)
            cys = sum(p[0] for p in chosen) / len(chosen)
            off = (abs(cxs - (n - 1) / 2) + abs(cys - (n - 1) / 2)) / n
            score = (round(off, 1), cost, abs(scale - 0.75))
            if best is None or score < best[0]:
                best = (score, chosen)
    return best[1] if best else None


def neighbours(n, cell):
    r, c = cell
    return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr or dc) and 0 <= r + dr < n and 0 <= c + dc < n]


def gen_layout(n, k, rng):
    """先给每行/每列各铺一颗（消灭空行空列），再在已有雷旁边生长到 k 颗（压低孤立雷）。
    这是"先定难度、再找星座"的第一步：盘面完全由难度参数决定，与星座无关。"""
    ms = set()
    cols = list(range(n)); rng.shuffle(cols)
    for r in range(n):
        ms.add((r, cols[r % n]))
    for c in range(n):
        if not any((r, c) in ms for r in range(n)):
            r = rng.randrange(n)
            for m in list(ms):
                if m[0] == r:
                    ms.discard(m); ms.add((r, c)); break
    guard = 0
    while len(ms) < k and guard < 5000:
        guard += 1
        base = rng.choice(list(ms))
        cand = [x for x in neighbours(n, base) if x not in ms]
        if cand:
            ms.add(rng.choice(cand))
        else:
            free = [(r, c) for r in range(n) for c in range(n) if (r, c) not in ms]
            if not free:
                break
            ms.add(rng.choice(free))
    return ms


def make_board(pl, rng):
    n = pl["size"]
    k = int(round(pl["dens"] * n * n))
    zh = pl["zh"]
    en, stars, lines = POOL[zh]
    k = max(k, len(stars))
    best_cand = None
    for attempt in range(3000):
        ms = gen_layout(n, k, rng)
        if any(not any((r, c) in ms for c in range(n)) for r in range(n)):
            continue
        if any(not any((r, c) in ms for r in range(n)) for c in range(n)):
            continue
        if f.isolated_mines({"mines": [list(x) for x in ms]}, n) > 2:
            continue
        iso = f.isolated_mines({"mines": [list(x) for x in ms]}, n)
        d = build_level(pl, ms, en, stars, lines, n)
        if d is None:
            continue
        ok, probs, info = gl.check_level(d, static=False)
        if not ok:
            continue
        zeros, zr = f.stats_of(d, n)
        if zr > 0.38:
            continue
        if not (pl["probes"][0] <= info["reveal_actions"] <= pl["probes"][1] + 6):
            continue
        iso_now = f.isolated_mines({"mines": [list(x) for x in ms]}, n)
        mid = (pl["probes"][0] + pl["probes"][1]) / 2
        cand_score = (iso_now, abs(info["reveal_actions"] - mid), zr)
        # 从盘面里"认出"星座
        pts_all = [(x, y) for (_, _, (x, y), _) in stars]
        for scale in (0.62, 0.72, 0.82, 0.92):
            for pts in transforms(pts_all):
                chosen = snap(pts, ms, n, scale)
                if not chosen:
                    continue
                d2 = attach_theme(d, en, stars, lines, chosen, n, zh)
                if d2:
                    if "best" not in dir() or True:
                        pass
                    cand = (cand_score, d2, info, zeros, zr)
                    if best_cand is None or cand[0] < best_cand[0]:
                        best_cand = cand
                    if cand_score[0] == 0 and cand_score[1] <= 2:
                        return d2, info, zeros, zr
    return (best_cand[1], best_cand[2], best_cand[3], best_cand[4]) if best_cand else None


def build_level(pl, ms, en, stars, lines, n):
    d = {
        "id": pl["lid"], "name": f"第 {pl['lid']} 关 · {pl['zh']}", "size": n,
        "mines": [list(rc) for rc in sorted(ms)], "noise": [],
        "showRuns": True, "opening": [0, 0], "lives": 3,
        "teach": pl["teach"], "technique": "constellation",
        "rowRuns": [gl.line_runs([(r, c) in ms for c in range(n)]) for r in range(n)],
        "colRuns": [gl.line_runs([(r, c) in ms for r in range(n)]) for c in range(n)],
    }
    p0 = gl.Puzzle(n, [tuple(m) for m in d["mines"]], (0, 0), True)
    best = None
    for r in range(n):
        for c in range(n):
            if (r, c) in p0.mines or p0.num[r][c] != 0:
                continue
            kk = gl.opening_reveal_count(gl.Puzzle(n, [tuple(m) for m in d["mines"]], (r, c), True))
            if kk / (n * n) > 0.38:
                continue
            if best is None or kk > best[0]:
                best = (kk, r, c)
    if best is None:
        return None
    d["opening"] = [best[1], best[2]]
    return d


def attach_theme(d, en, stars, lines, chosen, n, zh):
    order = []
    for idx, (name_zh, name_en, _xy, mag) in enumerate(stars):
        order.append(idx)
    theme_stars = []
    for idx, pos in enumerate(chosen):
        name_zh, name_en, _xy, mag = stars[idx]
        theme_stars.append({"name": name_zh, "en": name_en, "rc": [pos[0], pos[1]], "mag": mag,
                            "tint": ("warm" if name_zh in ("参宿四", "心宿二") else
                                     ("cool" if name_zh in ("参宿七", "天津四") else "neutral"))})
    ms = {tuple(m) for m in d["mines"]}
    if any((s["rc"][0], s["rc"][1]) not in ms for s in theme_stars):
        return None
    if len({(s["rc"][0], s["rc"][1]) for s in theme_stars}) != len(theme_stars):
        return None
    d["theme"] = {"id": en.lower().replace(" ", "-"), "name": zh, "nameEn": en,
                  "fact": f.FACTS.get(en, ""), "stars": theme_stars, "lines": lines}
    star_rc = {(s["rc"][0], s["rc"][1]) for s in theme_stars}
    d["noise"] = [list(rc) for rc in sorted(ms - star_rc)]
    return d


def main():
    rng = random.Random(20261023)
    out = []
    for pl in PLAN:
        got = None
        # 失败兜底：换棋盘尺寸 / 微调密度再试（棋盘仍 ≤11）
        for size, ddelta in ((pl["size"], 0.0), (pl["size"] + 1, 0.0), (pl["size"], 0.01),
                             (pl["size"] + 1, 0.01), (pl["size"] + 1, -0.01)):
            if size > 11:
                continue
            trial = dict(pl, size=size, dens=max(0.16, min(0.24, pl["dens"] + ddelta)))
            got = make_board(trial, rng)
            if got:
                break
        if not got:
            print(f"!! 第 {pl['lid']} 关 {pl['zh']} 生成失败")
            continue
        d, info, zeros, zr = got
        n = d["size"]
        iso = f.isolated_mines(d, n)
        print(f"第 {pl['lid']:2d} 关 {pl['zh']:5s} {n}x{n} 雷{len(d['mines']):2d} "
              f"星座星{len(d['theme']['stars']):2d} 杂{len(d['noise']):2d} 探格{info['reveal_actions']:2d} "
              f"星图{info['runs_cells']:2d} 孤立{iso} 0格{zr*100:.0f}%"
              f"{' 必须星图' if not info['nb_only_ok'] else ' 数字可解'}")
        out.append(d)
    if len(out) < 3:
        print("!! 生成数量不足，放弃写入"); sys.exit(1)
    json.dump(out, open(os.path.join(ROOT, "tools", "levels_new.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ 已写出 tools/levels_new.json（{len(out)} 关）")


if __name__ == "__main__":
    main()