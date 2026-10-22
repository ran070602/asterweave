#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v13-e 专项：星织 星座图鉴 level 映射 —— 结构断言（独立复算，不信任 build_sky.py）。

解析发布包 dist/星织-游戏本体/index.html 中 /* SKY_INJECT_START */ 与
/* LEVELS_INJECT_START */ 之间的内嵌数据，做：
  S1  SKY 恰好 50 条
  S2  LEVELS 恰好 50 条
  S3  对每个 LEVELS[i].theme.id 反查出关卡号 -> 与 SKY 中同 id 的 level 完全一致
  S4  SKY 中不存在 LEVELS 里没有的 id / level 为 null
  S5  SKY[].level 唯一且集合恰为 {1..50}
  S6  与 tools/sky.json、tools/levels.json 独立比对（三方一致）
  S7  zip 内 index.html 与 dist 内 index.html 的 SHA256 一致
"""
import json, os, re, sys, hashlib, zipfile

ROOT = r"D:\AI-Native casual game"
DIST_HTML = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")
TOOLS_SKY = os.path.join(ROOT, "tools", "sky.json")
TOOLS_LEVELS = os.path.join(ROOT, "tools", "levels.json")
ZIP = os.path.join(ROOT, "星织-游戏本体.zip")

results = []


def check(name, ok, evidence):
    results.append((name, bool(ok), evidence))
    print(("PASS " if ok else "FAIL ") + name + " :: " + evidence)
    return bool(ok)


def extract_block(html, marker):
    start = html.index("/* %s_START */" % marker)
    end = html.index("/* %s_END */" % marker)
    body = html[start:end]
    body = body.split("*/\n", 1)[1]           # drop the START comment line
    m = re.search(r"=\s*(\[)", body)
    body = body[m.start(1):]
    depth = 0
    in_str = False
    esc = False
    for i, ch in enumerate(body):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                return json.loads(body[:i + 1])
    raise ValueError("unbalanced block for " + marker)


html = open(DIST_HTML, encoding="utf-8").read()
sky = extract_block(html, "SKY_INJECT")
levels = extract_block(html, "LEVELS_INJECT")

check("S1 SKY 条数 = 50", len(sky) == 50, "len(SKY)=%d" % len(sky))
check("S2 LEVELS 条数 = 50", len(levels) == 50, "len(LEVELS)=%d" % len(levels))

lmap = {}
dup_theme = []
for x in levels:
    tid = (x.get("theme") or {}).get("id")
    if tid is None:
        continue
    if tid in lmap:
        dup_theme.append(tid)
    lmap[tid] = x["id"]

# S3
bad = []
for s in sky:
    real = lmap.get(s["id"], None)
    if real != s["level"]:
        bad.append((s["id"], s["zh"], s["level"], real))
check("S3 SKY[].level == LEVELS[theme.id].id (50/50)", not bad and len(lmap) == 50,
      "mismatch=%r ; theme.id 反查表大小=%d ; 重复 theme.id=%r" % (bad, len(lmap), dup_theme))

# S4
orphan = [(s["id"], s["level"]) for s in sky if s["id"] not in lmap or s["level"] is None]
check("S4 无孤儿 id / 无 null level", not orphan, "orphan=%r" % (orphan,))

# S5
lv = sorted(s["level"] for s in sky)
check("S5 level 唯一且恰为 1..50", lv == list(range(1, 51)),
      "unique=%d min=%s max=%s missing=%r" % (
          len(set(lv)), lv[0], lv[-1], sorted(set(range(1, 51)) - set(lv))))

# S6  与 tools 下源数据独立比对
t_sky = json.load(open(TOOLS_SKY, encoding="utf-8"))
t_levels = json.load(open(TOOLS_LEVELS, encoding="utf-8"))
t_lmap = {x["theme"]["id"]: x["id"] for x in t_levels if (x.get("theme") or {}).get("id")}
t_bad = [(s["id"], s["level"], t_lmap.get(s["id"])) for s in t_sky
         if s["level"] != t_lmap.get(s["id"])]
same_as_dist = (json.dumps(sky, sort_keys=True, ensure_ascii=False)
                == json.dumps(t_sky, sort_keys=True, ensure_ascii=False))
check("S6 tools/sky.json 与 dist 内嵌 SKY 一致 且 tools 自身 level 正确",
      same_as_dist and not t_bad,
      "dist==tools(sky)=%s ; tools mismatch=%r" % (same_as_dist, t_bad))

# S7 zip
with zipfile.ZipFile(ZIP) as z:
    names = z.namelist()
    inner = [n for n in names if n.endswith("index.html")]
    zhash = hashlib.sha256(z.read(inner[0])).hexdigest() if inner else None
dhash = hashlib.sha256(open(DIST_HTML, "rb").read()).hexdigest()
check("S7 zip 内 index.html == dist/index.html", zhash == dhash,
      "zip=%s dist=%s entry=%r" % ((zhash or "?")[:16], dhash[:16], inner))

# 关键三例显式打印（上一轮 bug 的星座）
focus = {s["id"]: s["level"] for s in sky}
print("FOCUS ophiuchus=%s carina=%s hydra=%s capricornus=%s grus=%s"
      % (focus.get("ophiuchus"), focus.get("carina"), focus.get("hydra"),
         focus.get("capricornus"), focus.get("grus")))
print("L1..L6 =", [s["id"] for s in sorted(sky, key=lambda x: x["level"])][:6])
print("L26..L31 =", [s["id"] for s in sorted(sky, key=lambda x: x["level"])][25:31])

out = {"results": [{"name": n, "ok": o, "evidence": e} for n, o, e in results],
       "level_by_id": {s["id"]: s["level"] for s in sky},
       "id_by_level": {s["level"]: s["id"] for s in sky}}
with open(os.path.join(ROOT, "verification", "v13_e_struct.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
print("ALL_PASS" if all(r[1] for r in results) else "HAS_FAIL")
sys.exit(0 if all(r[1] for r in results) else 1)
