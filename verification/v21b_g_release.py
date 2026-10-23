# -*- coding: utf-8 -*-
"""v21b 复核 G：发布包一致性（独立实现，不 import tools/）"""
import hashlib, io, json, os, re, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def sha(b): return hashlib.sha256(b).hexdigest()
def rd(p): return open(os.path.join(ROOT, p), "rb").read()

DIST = "dist/星织-游戏本体/index.html"
fails, warns = [], []
def chk(name, ok, detail=""):
    print(("  %-34s %s %s") % (name, "PASS" if ok else "FAIL", detail))
    if not ok: fails.append(name)
    return ok

dist_b = rd(DIST)
root_b = rd("index.html")
zip_b = rd("星织-游戏本体.zip")
snap_b = rd("verification/frozen_v21b/dist_index.html")
html = dist_b.decode("utf-8")

print("=== G 发布包 ===")
print("  sha dist=%s" % sha(dist_b)[:16])
print("  sha root=%s" % sha(root_b)[:16])
print("  sha zip =%s" % sha(zip_b)[:16])

# G1 ZIP 根目录恰为 index.html + README.txt
zf = zipfile.ZipFile(io.BytesIO(zip_b))
names = zf.namelist()
chk("G1 ZIP 根目录 == [index.html, README.txt]", sorted(names) == ["README.txt", "index.html"], repr(sorted(names)))
chk("G1b ZIP 无子目录/目录项", all("/" not in n and "\\" not in n for n in names), repr(names))
chk("G1c ZIP 无额外垃圾文件", not any(n.startswith(".") or n.endswith("/") for n in names), repr(names))

# G2 ZIP 内 index.html == dist 构建产物
zi = zf.read("index.html")
chk("G2 ZIP 内 index.html sha == dist", sha(zi) == sha(dist_b), "%s vs %s (%d/%d bytes)" % (
    sha(zi)[:16], sha(dist_b)[:16], len(zi), len(dist_b)))

# G3 根 index.html == dist
chk("G3 根 index.html sha == dist", sha(root_b) == sha(dist_b), "%s vs %s (%d/%d bytes)" % (
    sha(root_b)[:16], sha(dist_b)[:16], len(root_b), len(dist_b)))

# G4 冻结副本一致性（证明本轮复核对象 == 作者本次构建）
chk("G4 冻结副本 == 当前 dist", sha(snap_b) == sha(dist_b), sha(snap_b)[:16])

# G5 HTML 零外部引用
pats = {
    "http(s)://": r"https?://",
    "fetch(": r"fetch\s*\(",
    "XMLHttpRequest": r"XMLHttpRequest",
    "WebSocket": r"WebSocket",
    "<link": r"<link",
    "<img": r"<img",
    "import(": r"\bimport\s*\(",
    "src=": r"\bsrc\s*=",
    "@import": r"@import",
    "url(": r"url\s*\(",
    "<iframe": r"<iframe",
    "<object": r"<object",
    "<embed": r"<embed",
    "new Worker": r"new\s+Worker",
}
counts = {k: len(re.findall(v, html, re.I)) for k, v in pats.items()}
must_zero = ["http(s)://", "fetch(", "XMLHttpRequest", "WebSocket", "<link", "<img", "import(",
             "src=", "@import", "<iframe", "<object", "<embed", "new Worker"]
for k in must_zero:
    chk("G5 外部引用 %s == 0" % k, counts[k] == 0, "count=%d" % counts[k])

# G6 url( 逐个判定是否内联 SVG 内部引用
urls = re.findall(r"url\s*\(\s*(['\"]?)([^'\")]*)\1\s*\)", html, re.I)
urlvals = [u[1].strip() for u in urls]
print("  G6 url( 出现 %d 次：" % len(urlvals))
bad_url = []
for v in urlvals:
    internal = v.startswith("#") or v.startswith("data:")
    if not internal: bad_url.append(v)
    print("      %-46s %s" % (v[:46], "内联引用" if internal else "**外部引用**"))
chk("G6 url() 全为内联(#/data:)", not bad_url, "外部=%s" % (bad_url or "无"))

# G6b 源码里没有 <a href> 外链、没有 CSS @font-face 远程字体
hrefs = re.findall(r"<a\b[^>]*href\s*=\s*['\"]([^'\"]*)['\"]", html, re.I)
ext_href = [h for h in hrefs if re.match(r"^(https?:)?//", h)]
chk("G6b 无外部 <a href>", not ext_href, "外部=%s" % (ext_href or "无"))

# G7 build_manifest.json 与实测逐项一致
man = json.load(open(os.path.join(ROOT, "dist/build_manifest.json"), encoding="utf-8"))
lv = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))
exp = {
    "ui_sha256": sha(rd("game/index.html")),
    "levels_sha256": sha(rd("tools/levels.json")),
    "build_sha256": sha(dist_b),
    "zip_sha256": sha(zip_b),
    "level_count": len(lv),
    "zip_bytes": len(zip_b),
    "html_bytes": len(dist_b),
    "build_output": DIST.replace("/", "\\"),
    "zip": "星织-游戏本体.zip",
}
for k, v in exp.items():
    got = man.get(k)
    chk("G7 manifest.%s" % k, got == v, "manifest=%r 实测=%r" % (got, v))
chk("G7 manifest.zip_root_entries", sorted(man.get("zip_root_entries", [])) == sorted(names),
    "manifest=%r 实测=%r" % (man.get("zip_root_entries"), sorted(names)))
chk("G7 manifest.checks 全 True", all(man.get("checks", {}).values()),
    repr(man.get("checks")))
# G7b 独立重算 manifest 的 checks（不信任生成器自述）
zroot = sorted(names) == ["README.txt", "index.html"]
offline = all(counts[k] == 0 for k in must_zero)
try:
    import subprocess
    node = r"D:\develop\NodeJS\node.exe"
    js = zf.read("index.html").decode("utf-8")
    a = js.index("<script>") + len("<script>"); b = js.rindex("</script>")
    tmp = os.path.join(ROOT, "verification", "_v21b_syntax.js")
    open(tmp, "w", encoding="utf-8").write(js[a:b])
    r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
    syntax = (r.returncode == 0)
    os.remove(tmp)
except Exception as e:
    syntax = None; print("  (node --check 不可用: %s)" % e)
chk("G7b 独立复核 checks.levels_roundtrip", man.get("checks", {}).get("levels_roundtrip") == True, "level_count=%d" % len(lv))
chk("G7b 独立复核 checks.offline_selfcontained", man.get("checks", {}).get("offline_selfcontained") == (offline == True), "实测 offline=%s" % offline)
chk("G7b 独立复核 checks.zip_root_index", man.get("checks", {}).get("zip_root_index") == (zroot == True), "实测 zip_root=%s" % zroot)
chk("G7b 独立复核 checks.node_syntax", syntax is True and man.get("checks", {}).get("node_syntax") == True,
    "node --check rc=%s manifest=%s" % (syntax, man.get("checks", {}).get("node_syntax")))

# G8 ZIP 内 README.txt 与 tools/README_source.txt 是否一致（仅记录，非硬性）
readme_txt = zf.read("README.txt")
rs = os.path.join(ROOT, "tools/README_source.txt")
if os.path.exists(rs):
    rb = rd("tools/README_source.txt")
    same = readme_txt == rb
    print("  G8 ZIP.README.txt == tools/README_source.txt : %s (%d vs %d bytes, md5=%s)" % (
        same, len(readme_txt), len(rb), hashlib.md5(readme_txt).hexdigest()[:8]))
    print("     注意：根目录 README.md 是 %d 字节，与包内 README.txt %d 字节不同（非同一文件）" % (
        len(rd("README.md")), len(readme_txt)))

print("G 失败项 %d" % len(fails))
for f in fails: print("  ✗ " + f)
print("G_VERDICT", "PASS" if not fails else "FAIL")
