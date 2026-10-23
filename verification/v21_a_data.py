# -*- coding: utf-8 -*-
"""v21 复核 A：关卡数据自洽（独立实现，不 import tools/）"""
import json, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p): return json.load(open(os.path.join(ROOT, p), encoding="utf-8"))

HTML = open(os.environ.get("V21_HTML") or os.path.join(ROOT, "verification/frozen_v21b/dist_index.html"), encoding="utf-8").read()

def embedded(varname):
    a = HTML.index("/* %s_INJECT_START */" % varname)
    b = HTML.index("/* %s_INJECT_END */" % varname)
    blk = HTML[a:b]
    eq = blk.index("const %s = " % varname) + len("const %s = " % varname)
    txt = blk[eq:].strip()
    assert txt.endswith(";"), txt[-40:]
    return json.loads(txt[:-1])

def runs_of(vals):
    out, cur = [], 0
    for v in vals:
        if v: cur += 1
        elif cur: out.append(cur); cur = 0
    if cur: out.append(cur)
    return out

lv = load("tools/levels.json")
emb = embedded("LEVELS")
fails, notes = [], []

if len(lv) != 50: fails.append("levels.json 不是 50 关：%d" % len(lv))
if emb != lv: fails.append("内嵌 LEVELS != tools/levels.json（deep-diff 见下）")
else: notes.append("内嵌 LEVELS 与 tools/levels.json 逐字节等价（json 反序列化后 deep equal）")

ids, tids = [], {}
for i, x in enumerate(lv):
    lid, n = x["id"], x["size"]
    ids.append(lid)
    ms = {tuple(m) for m in x["mines"]}
    st = {tuple(s["rc"]) for s in x["theme"]["stars"]}
    nz = {tuple(m) for m in x["noise"]}
    # 1 runs 自洽
    rr = [runs_of([1 if (r, c) in ms else 0 for c in range(n)]) for r in range(n)]
    cc = [runs_of([1 if (r, c) in ms else 0 for r in range(n)]) for c in range(n)]
    if [list(v) for v in x["rowRuns"]] != rr: fails.append("L%d rowRuns 与 mines 不一致" % lid)
    if [list(v) for v in x["colRuns"]] != cc: fails.append("L%d colRuns 与 mines 不一致" % lid)
    # 2 noise/stars 关系
    if not st <= ms: fails.append("L%d theme.stars 有格不在 mines 里：%s" % (lid, sorted(st - ms)))
    if not nz <= ms: fails.append("L%d noise 有格不在 mines 里：%s" % (lid, sorted(nz - ms)))
    if st & nz: fails.append("L%d noise 与 theme.stars 重叠：%s" % (lid, sorted(st & nz)))
    if len(nz) != len(x["noise"]): fails.append("L%d noise 自身有重复" % lid)
    if len(st) != len(x["theme"]["stars"]): fails.append("L%d theme.stars 自身有重复" % lid)
    # 3 opening 是安全 0 格
    orow, ocol = x["opening"]
    if (orow, ocol) in ms: fails.append("L%d opening 是雷" % lid)
    nb = [(orow + dr, ocol + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc]
    hit = [p for p in nb if p in ms]
    if hit: fails.append("L%d opening 不是 0 格，邻雷 %s" % (lid, hit))
    # 4 showRuns
    want = False if lid == 1 else True
    if x.get("showRuns") is not want: fails.append("L%d showRuns=%r 期望 %r" % (lid, x.get("showRuns"), want))
    # 6 theme.id 唯一
    cid = x["theme"]["id"]
    if cid in tids: fails.append("L%d theme.id %s 与 L%d 重复" % (lid, cid, tids[cid]))
    tids[cid] = lid
    # 附加
    if x.get("lives") != 3: fails.append("L%d lives=%r 期望 3" % (lid, x.get("lives")))
    if x["theme"]["id"] != x["theme"].get("id"): fails.append("L%d theme.id 缺失" % lid)

if ids != list(range(1, 51)): fails.append("id 不是 1..50 连续：%s" % ids)
if len(tids) != 50: fails.append("theme.id 去重后 %d 个，期望 50" % len(tids))

print("A 关数=%d  theme.id 唯一=%d" % (len(lv), len(tids)))
print("A 内嵌==levels.json :", emb == lv)
if emb != lv:
    for i, (a, b) in enumerate(zip(emb, lv)):
        if a != b:
            ka = set(a) | set(b)
            print("  第 %d 项差异键：%s" % (i + 1, [k for k in ka if a.get(k) != b.get(k)]))
            break
    print("  长度 %d vs %d" % (len(emb), len(lv)))
for n_ in notes: print("A", n_)
print("A 失败项 %d" % len(fails))
for f in fails: print("  ✗ " + f)
print("A_VERDICT", "PASS" if not fails else "FAIL")
