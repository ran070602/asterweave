#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 51–88 关候选合并进 tools/levels.json（先逐关过权威验收，不合格拒绝写入）。

用法：python tools/merge_levels_51_88.py [--write]
"""
import importlib.util, io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from star_proper_zh import PROPER   # 知名星的传统中文名（其余沿用「星座+拜耳字母」）

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sp = importlib.util.spec_from_file_location("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
gl = importlib.util.module_from_spec(sp); sp.loader.exec_module(gl)

CAND = os.path.join(ROOT, "tools", "levels_51_88.json")
LEVELS = os.path.join(ROOT, "tools", "levels.json")
DENS_LO, DENS_HI = 0.15, 0.28   # 0.27 的设计值在 11×11 上取整为 33 雷 = 0.2727


def isolated(mines, n):
    ms = set(map(tuple, mines))
    k = 0
    for (r, c) in ms:
        if not any((r + dr, c + dc) in ms for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)):
            k += 1
    return k


def validate(d):
    """返回 (problems, info)"""
    probs = []
    lid, n = d.get("id"), d.get("size")
    if not isinstance(lid, int) or not (51 <= lid <= 88):
        probs.append("id 不在 51–88")
    if not isinstance(n, int) or n != 11:
        probs.append("size 应为 11")
    mines = d.get("mines") or []
    dens = len(mines) / (n * n) if n else 0
    if not (DENS_LO <= dens <= DENS_HI):
        probs.append("密度 %.3f 超出 %.2f–%.2f" % (dens, DENS_LO, DENS_HI))
    iso = isolated(mines, n)
    if iso > 2:
        probs.append("孤立雷 %d > 2" % iso)
    ms = {tuple(m) for m in mines}
    for r in range(n):
        if not any((r, c) in ms for c in range(n)):
            probs.append("空行 %d" % (r + 1))
            break
    for c in range(n):
        if not any((r, c) in ms for r in range(n)):
            probs.append("空列 %d" % (c + 1))
            break
    if d.get("showRuns") is not True:
        probs.append("showRuns 应为 true")
    if d.get("lives") != 3:
        probs.append("lives 应为 3")
    zh = ((d.get("theme") or {}).get("name")) or ""
    want_name = "第 %d 关 · %s" % (lid, zh) if zh else None
    if want_name and d.get("name") != want_name:
        probs.append("name 应为 %r（现在 %r）" % (want_name, d.get("name")))
    tk = d.get("timeK")
    if not (isinstance(tk, (int, float)) and 0.5 <= tk <= 2.0):
        probs.append("timeK 缺失或越界：%r" % tk)
    th = d.get("theme") or {}
    for s in (th.get("stars") or []):
        rc = s.get("rc") or []
        if len(rc) < 2 or (rc[0], rc[1]) not in ms:
            probs.append("星 %s 不在雷上" % (s.get("name"),))
            break
    if len({(s["rc"][0], s["rc"][1]) for s in (th.get("stars") or [])}) != len(th.get("stars") or []):
        probs.append("星位置有重复")
    nstars = len(th.get("stars") or [])
    for (a, b) in (th.get("lines") or []):
        if not (0 <= a < nstars and 0 <= b < nstars) or a == b:
            probs.append("连线下标非法 %r" % ((a, b),))
            break

    ok, cprobs, info = gl.check_level(d, static=False)
    if not ok:
        probs.append("零猜测不可解/线索不自洽: %s" % "; ".join(cprobs))
    if info.get("nb_only_ok") is not False:
        probs.append("不用数织也能解（nb_only_ok=%s）" % info.get("nb_only_ok"))
    if (info.get("runs_cells") or 0) < 3:
        probs.append("数织参与过少 runs_cells=%s" % info.get("runs_cells"))
    info = dict(info or {})
    info["density"] = dens
    info["isolated"] = iso
    return probs, info


def main():
    write = "--write" in sys.argv
    c88 = {x["id"]: x for x in json.load(io.open(os.path.join(ROOT, "tools", "constellations88.json"), encoding="utf-8"))}
    cand = json.load(io.open(CAND, encoding="utf-8"))
    lv = json.load(io.open(LEVELS, encoding="utf-8"))
    print("候选 %d 关；现有 levels.json %d 关" % (len(cand), len(lv)))

    print("\n%-4s %-8s %-4s %-6s %-5s %-4s %-4s %-5s %s" % ("关", "星座", "雷", "密度", "探格", "数织", "孤立", "timeK", "问题"))
    all_ok = True
    seen = set()
    rows = []
    for d in sorted(cand, key=lambda x: x.get("id", 0)):
        probs, info = validate(d)
        if probs:
            all_ok = False
        seen.add(d.get("id"))
        zh = ((d.get("theme") or {}).get("name")) or "?"
        print("%-4s %-8s %-4s %-6.3f %-5s %-4s %-4s %-5s %s" % (
            d.get("id"), zh, len(d.get("mines") or []), info.get("density", 0),
            info.get("reveal_actions"), info.get("runs_cells"), info.get("isolated"), d.get("timeK"),
            "；".join(probs)[:60] if probs else "OK"))
        rows.append(d)
    missing = [i for i in range(51, 89) if i not in seen]
    if missing:
        print("\n!! 缺关卡: %s" % missing)
        all_ok = False
    if not all_ok:
        print("\n有未达标项，**拒绝写入**。修好候选后重跑。")
        return
    if not write:
        print("\n全部 38 关通过验收（未加 --write，未写入）")
        return
    # 写盘前：给知名星补传统中文名（只补 PROPER 里高置信度的条目）
    renamed = 0
    for d in rows:
        for s in ((d.get("theme") or {}).get("stars") or []):
            nm = PROPER.get(s.get("en"))
            if nm and s.get("name") != nm:
                s["name"] = nm
                renamed += 1
    print("已补传统中文星名 %d 处（其余沿用「星座+拜耳字母」）" % renamed)
    lv = [x for x in lv if x.get("id", 0) < 51] + rows
    io.open(LEVELS, "w", encoding="utf-8").write(json.dumps(lv, ensure_ascii=False, indent=2) + "\n")
    print("\n✅ 已写入 tools/levels.json：%d 关（1–50 原样保留 + 51–88）" % len(lv))


if __name__ == "__main__":
    main()
