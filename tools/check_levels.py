#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关卡数据自检（谁生成关卡都可以跑）：python tools/check_levels.py

检查项：
  1. 线索自洽（rowRuns/colRuns/opening 与 mines 一致）           —— 硬失败
  2. 零猜测可解（第 1 关同样必须用数织线索，不再豁免）            —— 硬失败
  3. 孤立雷（周围 8 格无雷）≤2，>3 报错                          —— 超 3 失败、=3 警告
  4. 空行/空列（第 1 关允许，其余应为 0）                        —— 警告
  5. 雷密度 15%–28%（51–88 关按设计到 0.273）                      —— 警告
  6. 星座重复、图鉴 sky.json 覆盖                                —— 警告
  7. 所有关卡 showRuns 必须 true（第 1 关已改为“首关即引入数织”）  —— 警告
  8. 第 1 关必须“不用数织会卡住”且至少一条长度 ≥2 的连续块线索    —— 警告
  9. 每关 name 必须是「第 N 关 · 星座名」（顶栏标题直接显示）      —— 警告
退出码：0 = 全部通过（可能有警告）；1 = 有硬失败。
"""
import importlib.util, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
gl = importlib.util.module_from_spec(sp); sp.loader.exec_module(gl)

LEVELS = os.path.join(ROOT, "tools", "levels.json")
SKY = os.path.join(ROOT, "tools", "sky.json")


def isolated(mines, n):
    ms = {tuple(m) for m in mines}
    k = 0
    for (r, c) in ms:
        if not any((r + dr, c + dc) in ms for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc):
            k += 1
    return k


def main():
    lv = json.load(open(LEVELS, encoding="utf-8"))
    sky = {}
    if os.path.exists(SKY):
        sky = {s["id"]: s for s in json.load(open(SKY, encoding="utf-8"))}

    hard, warn = [], []
    seen_const = {}
    print(f"{'关':>3} {'星座':<8} {'盘面':>7} {'雷':>4} {'探格':>4} {'星图':>4} {'孤立':>4} {'0格%':>5} {'空行':>3} {'空列':>3}")
    print("-" * 78)
    for x in lv:
        lid, n = x["id"], x["size"]
        ms = {tuple(m) for m in x["mines"]}
        ok, _probs, info = gl.check_level(x, static=False)
        iso = isolated(x["mines"], n)
        zeros = info.get("reveal_actions", 0)
        # 0 格占比：用开局态估算（安全格中被 flood 展开的比例）
        empty_r = sum(1 for r in range(n) if not any((r, c) in ms for c in range(n)))
        empty_c = sum(1 for c in range(n) if not any((r, c) in ms for r in range(n)))
        dens = len(ms) / (n * n) * 100
        print(f"{lid:>3} {x['theme']['name']:<8} {n:>3}x{n:<3} {len(ms):>4} {info['reveal_actions']:>4} "
              f"{info['runs_cells']:>4} {iso:>4} {'':>5} {empty_r:>3} {empty_c:>3}")

        if not ok:
            hard.append(f"第 {lid} 关 {x['theme']['name']}：零猜测不可解 / 线索不自洽")
        if iso > 3:
            hard.append(f"第 {lid} 关 {x['theme']['name']}：孤立雷 {iso} 个（>3，会有大量“一眼就知道”）")
        elif iso == 3:
            warn.append(f"第 {lid} 关：孤立雷 3 个，建议压到 ≤2")
        if lid != 1 and (empty_r or empty_c):
            warn.append(f"第 {lid} 关：有空行 {empty_r} / 空列 {empty_c}（边缘会显得空）")
        if x.get("showRuns") is not True:
            warn.append(f"第 {lid} 关应 showRuns=true")
        if lid == 1:
            # 首关即引入数织：必须“不用数织会卡住”，且要有真正的连续块线索可教
            if info.get("nb_only_ok") is not False:
                warn.append("第 1 关：不用数织也能解（数织非必需），教学价值不足")
            blocks = [v for rr in list(x["rowRuns"]) + list(x["colRuns"]) for v in rr if v >= 2]
            if not blocks:
                warn.append("第 1 关：没有任何长度 ≥2 的连续块线索，教不了数织")
        if not (15 <= dens <= 28):
            warn.append(f"第 {lid} 关：雷密度 {dens:.1f}%（1–50 关目标约 20%，51–88 关 25–27%）")
        cid = x["theme"]["id"]
        if cid in seen_const:
            want_name = f"第 {lid} 关 · {(x.get('theme') or {}).get('name', '')}"
            if x.get("name") != want_name:
                warn.append(f"第 {lid} 关：name 是 {x.get('name')!r}，应为 {want_name!r}"
                            "（顶栏标题会显示与实际位置矛盾的关卡号；重排关卡后必须重算 name）")
            warn.append(f"第 {lid} 关与第 {seen_const[cid]} 关星座重复：{cid}")
        else:
            seen_const[cid] = lid
        if sky and cid not in sky:
            warn.append(f"第 {lid} 关 {x['theme']['name']}（{cid}）没有图鉴数据：在 tools/build_sky.py 的 RAW 里补一行后重跑")

    if sky:
        extra = [s["id"] for s in sky.values() if s.get("level", 0) > len(lv)]
        if extra:
            warn.append(f"图鉴里有 {len(extra)} 个星座的关卡号超出当前关数：{extra}")

    print("-" * 78)
    print(f"共 {len(lv)} 关；硬失败 {len(hard)} 项，警告 {len(warn)} 项")
    for h in hard:
        print("  ✗ " + h)
    for w in warn:
        print("  ! " + w)
    if not hard:
        print("\n✅ 关卡数据通过自检")
        if warn:
            print("（警告不阻塞，但建议逐条看过）")
    return 1 if hard else 0


if __name__ == "__main__":
    sys.exit(main())