# -*- coding: utf-8 -*-
"""v21b 复核 E（数据侧，独立实现）：内嵌 SKY 与 LEVELS 的 level <-> theme.id 对应"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = open(os.environ.get("V21_HTML") or os.path.join(ROOT, "dist", "星织-游戏本体", "index.html"),
            encoding="utf-8").read()

def embedded(name):
    a = HTML.index("/* %s_INJECT_START */" % name)
    b = HTML.index("/* %s_INJECT_END */" % name)
    blk = HTML[a:b]
    eq = blk.index("const %s = " % name) + len("const %s = " % name)
    return json.loads(blk[eq:].strip()[:-1])

LV = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))
SKYF = json.load(open(os.path.join(ROOT, "tools/sky.json"), encoding="utf-8"))
SKY = embedded("SKY")
LV_EMB = embedded("LEVELS")
fails = []

print("=== E 星座图鉴（数据侧） ===")
print("  内嵌 SKY == tools/sky.json :", SKY == SKYF, " 星座数 =", len(SKY))
print("  内嵌 LEVELS == tools/levels.json :", LV_EMB == LV)
if SKY != SKYF: fails.append("内嵌 SKY != tools/sky.json")
if LV_EMB != LV: fails.append("内嵌 LEVELS != tools/levels.json")

ids = [s["id"] for s in SKY]
if len(ids) != len(set(ids)): fails.append("SKY id 有重复")
levels = [s["level"] for s in SKY]
lvl_ok = (sorted(levels) == list(range(1, 51)))
print("  SKY[].level 唯一覆盖 1..50 :", lvl_ok, "(n=%d, min=%s max=%s)" % (len(levels), min(levels), max(levels)))
if not lvl_ok: fails.append("SKY level 不是 1..50 唯一覆盖")

# 核心断言：SKY[].level == LEVELS[theme.id].id，双向
byid = {s["id"]: s for s in SKY}
bylv = {s["level"]: s for s in SKY}
bad_fwd, bad_back = [], []
for x in LV:
    tid = x["theme"]["id"]
    if tid not in byid:
        fails.append("L%d theme.id %s 不在 SKY" % (x["id"], tid)); continue
    if byid[tid]["level"] != x["id"]:
        bad_fwd.append((x["id"], tid, byid[tid]["level"]))
    if byid[tid]["zh"] != x["theme"]["name"]:
        fails.append("L%d 星座名不一致 %s / %s" % (x["id"], byid[tid]["zh"], x["theme"]["name"]))
for s in SKY:
    x = LV[s["level"] - 1]
    if x["theme"]["id"] != s["id"]:
        bad_back.append((s["level"], s["id"], x["theme"]["id"]))
if bad_fwd: fails.append("正向 SKY[].level != LEVELS[id].id : %s" % bad_fwd)
if bad_back: fails.append("反向 LEVELS[level-1].theme.id != SKY[].id : %s" % bad_back)
print("  SKY[].level == LEVELS[theme.id].id 正向 :", not bad_fwd)
print("  LEVELS[level-1].theme.id == SKY[].id 反向 :", not bad_back)

# 邻接星座引用必须在 SKY 内且 level 自洽
nb_bad = []
for s in SKY:
    for n in (s.get("neighbors") or []):
        if n.get("id") and n["id"] not in byid: nb_bad.append((s["id"], n["id"], "missing"))
        elif n.get("id") and byid[n["id"]].get("level") != n.get("level"):
            nb_bad.append((s["id"], n["id"], "level %s vs %s" % (n.get("level"), byid[n["id"]].get("level"))))
print("  neighbors 引用自洽 :", not nb_bad, nb_bad[:5] if nb_bad else "")
if nb_bad: fails.append("neighbors 引用异常 %s" % nb_bad[:5])

print("E 失败项 %d" % len(fails))
for f in fails: print("  ✗ " + f)
print("E_VERDICT", "PASS" if not fails else "FAIL")
