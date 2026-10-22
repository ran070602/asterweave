# -*- coding: utf-8 -*-
"""v13 G：发布包核验（ZIP 根结构 / ZIP 与 dist 的 index.html 一致性 / 零外部引用 / build_manifest 对账）。"""
import hashlib, json, os, re, zipfile

ROOT = r"D:\AI-Native casual game"
DIST = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")
ZIP = os.path.join(ROOT, "星织-游戏本体.zip")
MAN = os.path.join(ROOT, "dist", "build_manifest.json")

def sha(b): return hashlib.sha256(b).hexdigest()

dist_src = open(DIST, "rb").read()
dist_text = dist_src.decode("utf-8")
zf = zipfile.ZipFile(ZIP)
names = zf.namelist()
index_b = zf.read("index.html")
readme_b = zf.read("README.txt")
readme = readme_b.decode("utf-8")
man = json.load(open(MAN, encoding="utf-8"))

res = {}
res["zip_names"] = names
res["zip_root_exact"] = sorted(names) == ["README.txt", "index.html"]
res["zip_index_sha"] = sha(index_b)
res["dist_index_sha"] = sha(dist_src)
res["zip_index_equals_dist"] = sha(index_b) == sha(dist_src)
res["zip_index_bytes"] = len(index_b)
res["zip_index_bytes_equal"] = len(index_b) == len(dist_src)

# 零外部引用
pats = ["http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "<link", "<img", "import(", "src=", "url("]
counts = {p: dist_text.count(p) for p in pats}
res["external_counts"] = counts
res["external_zero"] = all(counts[p] == 0 for p in pats)

# build_manifest 对账
res["manifest"] = man
lv = json.load(open(os.path.join(ROOT, "tools", "levels.json"), encoding="utf-8"))
res["levels_count_actual"] = len(lv)

# 从 manifest 里挑出与 index.html 相关的字段逐一对账
flat = json.dumps(man, ensure_ascii=False)
res["manifest_text"] = flat
res["manifest_has_dist_sha"] = sha(dist_src)[: ] in flat or sha(dist_src)[:16] in flat
res["manifest_mentions_50"] = "50" in flat

print("=== G 发布包 ===")
print("ZIP 条目:", names, "| 根目录恰为 index.html+README.txt:", res["zip_root_exact"])
print("ZIP index.html sha256:", res["zip_index_sha"])
print("dist index.html sha256:", res["dist_index_sha"])
print("两者一致:", res["zip_index_equals_dist"], "| 字节 %d vs %d -> %s" % (
    res["zip_index_bytes"], len(dist_src), res["zip_index_bytes_equal"]))
print("外部引用计数:", counts, "-> 全零:", res["external_zero"])
print("build_manifest.json:", flat)
print("manifest 含 dist sha:", res["manifest_has_dist_sha"], "| 含 50:", res["manifest_mentions_50"])
print("README.txt 字节:", len(readme_b), "| 行数:", readme.count("\n") + 1)
for kw in ["图鉴", "观测", "标记", "全部解锁", "星织", "Asterweave", "50"]:
    print("  README.txt 含 %-6s: %s" % (kw, kw in readme))
json.dump(res, open(os.path.join(ROOT, "verification", "v13_out_g.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
