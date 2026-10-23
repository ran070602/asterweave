# -*- coding: utf-8 -*-
"""v21 复核 E（数据侧）：图鉴 SKY 与关卡 LEVELS 的 level<->theme.id 对应"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = open(os.environ.get("V21_HTML") or os.path.join(ROOT, "verification/frozen_v21b/dist_index.html"), encoding="utf-8").read()

def embedded(name):
    a = HTML.index("/* %s_INJECT_START */" % name)
    b = HTML.index("/* %s_INJECT_END */" % name)
    blk = HTML[a:b]
    eq = blk.index("const %s = " % name) + len("const %s = " % name)
    return json.loads(blk[eq:].strip()[:-1])

LV = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))
SKYF = json.load(open(os.path.join(ROOT, "tools/sky.json"), encoding="utf-8"))
SKY = embedded("SKY")
fails = []

if SKY != SKYF: fails.append("内嵌 SKY != tools/sky.json")
ids = [s["id"] for s in SKY]
if len(ids) != len(set(ids)): fails.append("sky.json id 有重复")
levels = [s["level"] for s in SKY]
if sorted(levels) != list(range(1, 51)): fails.append("sky level 不是 1..50 的唯一覆盖")

byid = {s["id"]: s for s in SKY}
for i, x in enumerate(LV):
    tid = x["theme"]["id"]
    if tid not in byid: fails.append("L%d theme.id %s 不在 SKY" % (i + 1, tid)); continue
    if byid[tid]["level"] != i + 1:
        fails.append("L%d theme.id %s 的 SKY.level=%s" % (i + 1, tid, byid[tid]["level"]))
    if byid[tid]["zh"] != x["theme"]["name"]:
        fails.append("L%d 星座名不一致 %s / %s" % (i + 1, byid[tid]["zh"], x["theme"]["name"]))
    # fact 一致性：skyDetailHtml 用的是 LEVELS[].theme.fact
    nb = byid[tid].get("neighbors") or []
    for n in nb:
        if n.get("id") and n["id"] not in byid: fails.append("L%d 相邻星座 %s 不在 SKY" % (i + 1, n["id"]))
        if n.get("id") and byid[n["id"]].get("level") != n.get("level"):
            fails.append("L%d 相邻 %s level 不符" % (i + 1, n["id"]))

print("E 内嵌 SKY == sky.json :", SKY == SKYF, " 星座数 =", len(SKY))
print("E level 1..50 唯一覆盖 :", sorted(levels) == list(range(1, 51)))
print("E theme.id -> level 双向一致 :", not fails)
for f in fails: print("  ✗ " + f)
print("E_VERDICT", "PASS" if not fails else "FAIL")
