# -*- coding: utf-8 -*-
"""v21 复核 H：文档对账（两份文档的 50 行关卡表 vs levels.json + level_stats.json；SPEC 版本/交互）"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LV = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))
ST = {x["id"]: x for x in json.load(open(os.path.join(ROOT, "tools/level_stats.json"), encoding="utf-8"))}
B = {x["lid"]: x for x in json.load(open(os.path.join(ROOT, "verification/v21_out_b.json"), encoding="utf-8"))}
sys.path.insert(0, os.path.join(ROOT, "verification"))
DOCS = [("冉政-设计思路文档.md", "设计思路"), ("冉政-迭代优化过程文档.md", "迭代优化")]

def tables(path):
    lines = open(os.path.join(ROOT, path), encoding="utf-8").read().split("\n")
    out = []
    for i, l in enumerate(lines):
        if l.startswith("|") and "总雷" in l and "星座" in l:
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append((i + 1, [c.strip() for c in l.strip().strip("|").split("|")], rows))
    return out

# 我方独立口径：仅邻域推理能否通关（showRuns 一律关掉）
sys.argv = [sys.argv[0]]
import importlib.util
spec = importlib.util.spec_from_file_location("v21b", os.path.join(ROOT, "verification/v21_b_solve.py"))

fails, notes = [], []
# 1) 文档表格逐格对账
for path, tag in DOCS:
    ts = tables(path)
    if len(ts) != 1:
        fails.append("%s 找到 %d 个「星座/总雷」表" % (tag, len(ts))); continue
    lno, hdr, rows = ts[0]
    if len(rows) != 50: fails.append("%s 表格数据行 %d（期望 50）" % (tag, len(rows)))
    bad = []
    for r in rows:
        if len(r) < 9: bad.append("列数不足: %s" % r); continue
        lid = int(r[0]); x = LV[lid - 1]; s = ST[lid]
        exp = [str(lid), x["theme"]["name"], "%d×%d" % (x["size"], x["size"]),
               str(len(x["theme"]["stars"])), str(len(x["noise"])), str(len(x["mines"])),
               str(s["probes"]), str(s["runs"])]
        got = r[:8]
        if got != exp:
            bad.append("L%d 文档%s != 实测%s" % (lid, got, exp))
    notes.append("%s 表 @L%d 表头=%s；50 行逐格对账差异 %d" % (tag, lno, "|".join(hdr), len(bad)))
    for b in bad[:12]: notes.append("   ✗ " + b)
    if bad: fails.append("%s 表 8 列与 levels.json/level_stats.json 有 %d 处不符" % (tag, len(bad)))

# 2) 最后一列（只用数字能解？/ 必须用星图线索？）与实测
for path, tag in DOCS:
    lno, hdr, rows = tables(path)[0]
    mism = []
    for r in rows:
        lid = int(r[0]); last = r[8]
        nb = ST[lid]["nb_only"]
        if "只用数字" in hdr[8]:
            doc_yes = last.startswith("是")
            if doc_yes != nb: mism.append("L%d 文档=%s 实测nb_only=%s" % (lid, last, nb))
        else:
            need = last.startswith("是")
            if need != (not nb): mism.append("L%d 文档=%s 实测必须用线索=%s" % (lid, last, not nb))
    notes.append("%s 末列口径「%s」与 level_stats.nb_only 不符 %d 处：%s" % (tag, hdr[8], len(mism), mism[:10]))
    if mism: fails.append("%s 末列与实测不符 %d 处" % (tag, len(mism)))

# 3) 正文断言 vs 实测
probes = [ST[i]["probes"] for i in range(1, 51)]
dens = [len(LV[i]["mines"]) / (LV[i]["size"] ** 2) for i in range(50)]
noise = [len(LV[i]["noise"]) for i in range(50)]
nb_false = [i + 1 for i in range(50) if not ST[i + 1]["nb_only"]]
nb_true = [i + 1 for i in range(50) if ST[i + 1]["nb_only"]]
notes.append("实测 探格 %d–%d；雷密度 %.1f%%–%.1f%%（均值 %.1f%%）；杂星 %d–%d 颗；尺寸 %d×%d–%d×%d" % (
    min(probes), max(probes), min(dens) * 100, max(dens) * 100, sum(dens) / 50 * 100,
    min(noise), max(noise), min(x["size"] for x in LV), min(x["size"] for x in LV),
    max(x["size"] for x in LV), max(x["size"] for x in LV)))
notes.append("实测 nb_only=true 的关：%s（其余 %d 关必须用行列线索）" % (nb_true, len(nb_false)))
teach = [(x["id"], x["theme"]["name"], (x.get("teach") or "")[:18]) for x in LV if (x.get("teach") or "")]
notes.append("teach 非空的关：%s" % teach)

CLAIMS = [
    ("设计思路/迭代：『50 关里有 45 关重新变成“必须用星图线索”』", len(nb_false) == 45,
     "实测必须用线索 = %d 关" % len(nb_false)),
    ("设计思路：『探格 19–47 次随关卡上升』", min(probes) >= 19 and max(probes) <= 47,
     "实测探格 %d–%d" % (min(probes), max(probes))),
    ("设计思路 L226：『全 50 关棋盘 7×7–11×11』", all(x["size"] >= 7 for x in LV),
     "实测最小 %d×%d（第 1 关）；该句同段还写『第 1 关现在是 6×6』自相矛盾" % (LV[0]["size"], LV[0]["size"])),
    ("设计思路 L77 / SPEC：『第 2 关数织贡献 12 格、第 10 关 10 格』『L2 数织贡献要求 ≥5（实测 12 格）』",
     ST[2]["runs"] == 12 and ST[10]["runs"] == 10,
     "实测 L2 数织贡献=%d、L10=%d（两文档自己的表也写 L2=3）" % (ST[2]["runs"], ST[10]["runs"])),
    ("设计思路：『雷密度 15.6%–24.0%，均值 21.6%』", abs(min(dens) * 100 - 15.6) < 0.05 and abs(max(dens) * 100 - 24.0) < 0.05,
     "实测 %.1f%%–%.1f%%，均值 %.1f%%" % (min(dens) * 100, max(dens) * 100, sum(dens) / 50 * 100)),
    ("设计思路：『全 50 关杂星 6–22 颗』『第 1 关杂星 6 颗』", min(noise) == 6,
     "实测杂星 %d–%d 颗（第 1 关 %d 颗）" % (min(noise), max(noise), noise[0])),
    ("SPEC §3：『第 1 关必须只靠邻域推理就能零猜测通关（数织贡献=0）』",
     ST[1]["nb_only"] is True and ST[1]["runs"] == 0,
     "L1 nb_only=%s runs=%d" % (ST[1]["nb_only"], ST[1]["runs"])),
    ("SPEC：『teach 只在第 1、2、6 关非空（10 关初版）』", len(teach) == 3,
     "实测 teach 非空 %d 关：%s" % (len(teach), [t[0] for t in teach])),
]
for name, ok, ev in CLAIMS:
    notes.append("[%s] %s → %s" % ("OK" if ok else "不符", name, ev))
    if not ok: fails.append(name + "（" + ev + "）")

# 4) SPEC 版本号
sp = open(os.path.join(ROOT, "docs/SPEC.md"), encoding="utf-8").read()
vers = re.findall(r"v1\.\d+", sp)
title = sp.split("\n")[0]
notes.append("SPEC 标题：%s；文中出现的版本号统计：%s" % (title, {v: vers.count(v) for v in sorted(set(vers))}))
for v in ["v1.5", "v1.6", "v1.7"]:
    if v not in sp: fails.append("SPEC 标题写 %s 但正文没有任何 %s 修订说明" % (re.search(r"v1\.\d+", title).group(0), v))
# 交互描述一致性
inter = ["轻触 = 观测", "长按（~380ms）= 标记", "单击 = 观测", "右键 = 标记", "Enter = 观测", "空格 = 标记", "不做双击标记"]
miss = [k for k in inter if k not in sp]
notes.append("SPEC 现行交互要素齐全：%s（缺 %s）" % (not miss, miss))
if miss: fails.append("SPEC 交互描述缺 " + str(miss))
if "结算" in sp:
    for m in re.finditer("结算", sp):
        notes.append("   SPEC 结算上下文: ..." + sp[max(0, m.start() - 70):m.start() + 50].replace("\n", " ") + "...")

print("\n".join(notes))
print("-" * 90)
for f in fails: print("  ✗ " + f)
print("H 不符项 %d" % len(fails))
print("H_VERDICT", "PASS" if not fails else "FAIL")
