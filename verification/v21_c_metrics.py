# -*- coding: utf-8 -*-
"""v21 复核 C：难度指标独立统计（口径见任务书）+ 与 tools/level_stats.json 对照"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LV = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))
ST = {x["id"]: x for x in json.load(open(os.path.join(ROOT, "tools/level_stats.json"), encoding="utf-8"))}
B = {x["lid"]: x for x in json.load(open(os.path.join(ROOT, "verification/v21_out_b.json"), encoding="utf-8"))}

print("%-3s %-9s %-5s %-5s %-7s %-8s %-7s %-5s %-5s %-5s %-5s %s" % (
    "关", "星座", "尺寸", "雷", "雷密%", "开局展开%", "0格%", "孤立", "空行", "空列", "探格", "level_stats 对照"))
print("-" * 130)
fails, mismatch = [], []
rows = []
for x in LV:
    lid, n = x["id"], x["size"]
    ms = {tuple(m) for m in x["mines"]}
    cnt = lambda r, c: sum(1 for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                           if (dr or dc) and (r + dr, c + dc) in ms)
    # 开局展开：从 opening 起的 0 格连通块（flood fill 到不动点）
    seen = set()
    st = [tuple(x["opening"])]
    while st:
        p = st.pop()
        if p in seen or p in ms: continue
        seen.add(p)
        if cnt(*p) == 0:
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    q = (p[0] + dr, p[1] + dc)
                    if (dr or dc) and 0 <= q[0] < n and 0 <= q[1] < n and q not in seen:
                        st.append(q)
    expand = len(seen) / (n * n)
    zeros = sum(1 for r in range(n) for c in range(n) if (r, c) not in ms and cnt(r, c) == 0)
    zr = zeros / (n * n)
    safe = n * n - len(ms)
    iso = sum(1 for (r, c) in ms if not any((r + dr, c + dc) in ms
              for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc))
    er = sum(1 for r in range(n) if not any((r, c) in ms for c in range(n)))
    ec = sum(1 for c in range(n) if not any((r, c) in ms for r in range(n)))
    dens = len(ms) / (n * n)
    s = ST[lid]
    cmp_ok = (s["size"] == n and s["mines"] == len(ms) and s["stars"] == len(x["theme"]["stars"])
              and s["noise"] == len(x["noise"]) and s["iso"] == iso and s["isEmpty"] == [er, ec]
              and s["showRuns"] == x["showRuns"] and abs(s["zr"] - round(zeros / safe * 100)) <= 1)
    if not cmp_ok: mismatch.append(lid)
    rows.append(dict(lid=lid, name=x["theme"]["name"], size=n, mines=len(ms), density=dens,
                     expand=expand, zr=zr, zeros=zeros, iso=iso, er=er, ec=ec,
                     probes=ST[lid]["probes"], runs=ST[lid]["runs"], nb_only=ST[lid]["nb_only"],
                     rounded_zr=round(zeros / safe * 100)))
    print("%-3d %-9s %-5s %-5d %-7.1f %-8.1f %-7.1f %-5d %-5d %-5d %-5d %s" % (
        lid, x["theme"]["name"], "%dx%d" % (n, n), len(ms), dens * 100, expand * 100, zr * 100,
        iso, er, ec, ST[lid]["probes"], "OK" if cmp_ok else "DIFF"))
print("-" * 130)
checks = [
    ("尺寸<=11", all(r["size"] <= 11 for r in rows), "max=%d" % max(r["size"] for r in rows)),
    ("开局展开<=38%(分母 n²)", all(r["expand"] <= 0.38 for r in rows),
     "max=%.1f%% (L%d)" % (max(r["expand"] for r in rows) * 100,
                            max(rows, key=lambda r: r["expand"])["lid"])),
    ("0格<=40%(分母 n²)", all(r["zr"] <= 0.40 for r in rows),
     "max=%.1f%% (L%d)" % (max(r["zr"] for r in rows) * 100, max(rows, key=lambda r: r["zr"])["lid"])),
    ("孤立雷<=2", all(r["iso"] <= 2 for r in rows), "max=%d" % max(r["iso"] for r in rows)),
    ("前五关无空行空列", all(r["er"] == 0 and r["ec"] == 0 for r in rows[:5]), ""),
    ("50关全部无空行空列", all(r["er"] == 0 and r["ec"] == 0 for r in rows), ""),
    ("雷密度 15%-25%", all(0.15 <= r["density"] <= 0.25 for r in rows),
     "min=%.1f%% max=%.1f%%" % (min(r["density"] for r in rows) * 100, max(r["density"] for r in rows) * 100)),
]
for name, ok, extra in checks:
    print(("  %-24s %s %s") % (name, "PASS" if ok else "FAIL", extra))
    if not ok: fails.append(name)
print("C level_stats 逐关对照差异关号:", mismatch if mismatch else "无")
# level_stats 口径：探格 = 求解器 reveal_actions；zr = zeros/safe*100 四舍五入
diffs = [r["lid"] for r in rows if abs(ST[r["lid"]]["probes"] - B[r["lid"]]["reveal_actions"]) > 2]
print("C 我方探格(reveal_actions) 与 level_stats.probes 相差 >2 的关:", diffs if diffs else "无")
mx = max(rows, key=lambda r: abs(ST[r["lid"]]["probes"] - B[r["lid"]]["reveal_actions"]))
print("C 最大探格差：L%d 我方 %d vs 文件 %d" % (mx["lid"], B[mx["lid"]]["reveal_actions"], ST[mx["lid"]]["probes"]))
print("C 探格范围 %d..%d；开局展开最小 %.1f%% 最大 %.1f%%" % (
    min(r["probes"] for r in rows), max(r["probes"] for r in rows),
    min(r["expand"] for r in rows) * 100, max(r["expand"] for r in rows) * 100))
print("C_VERDICT", "PASS" if not fails else "FAIL")
json.dump(rows, open(os.path.join(ROOT, "verification/v21_out_c.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
