# -*- coding: utf-8 -*-
"""v21 复核 G：发布包完整性（ZIP / 离线自包含 / manifest 对账 / 根 index 一致）"""
import hashlib, io, json, os, re, subprocess, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F = lambda p: os.path.join(ROOT, p)
sha = lambda b: hashlib.sha256(b).hexdigest()
fails, notes = [], []

# BASE=frozen 时全部读冻结副本（自洽基线）；默认 live
BASE = os.environ.get("V21_BASE", "live")
FB = "verification/frozen_v21b/"
P = dict(
    dist=(FB + "dist_index.html") if BASE == "frozen" else "dist/星织-游戏本体/index.html",
    root=(FB + "root_index.html") if BASE == "frozen" else "index.html",
    zip=(FB + "release.zip") if BASE == "frozen" else "星织-游戏本体.zip",
    man=(FB + "build_manifest.json") if BASE == "frozen" else "dist/build_manifest.json",
    game=(FB + "game_index.html") if BASE == "frozen" else "game/index.html",
    levels=(FB + "levels.json") if BASE == "frozen" else "tools/levels.json",
)
print("G 基线 =", BASE, "（V21_BASE=%s）" % BASE)

DIST = open(F(P["dist"]), "rb").read()
ROOT_HTML = open(F(P["root"]), "rb").read()
ZIP = F(P["zip"])
MAN = json.load(open(F(P["man"]), encoding="utf-8"))
html_txt = DIST.decode("utf-8")

# --- 1) ZIP 结构 ---
zf = zipfile.ZipFile(ZIP)
names = zf.namelist()
roots_ok = (names == ["index.html", "README.txt"]) or (sorted(names) == ["README.txt", "index.html"])
if set(names) != {"index.html", "README.txt"}: fails.append("ZIP 根条目不是 index.html + README.txt：%s" % names)
if any(("/" in n or "\\" in n) for n in names): fails.append("ZIP 内存在子目录：%s" % names)
zidx = zf.read("index.html")
zread = zf.read("README.txt")
notes.append("ZIP 根条目 = %s；README.txt %d bytes（sha %s）" % (names, len(zread), sha(zread)[:16]))
if sha(zidx) != sha(DIST): fails.append("ZIP 内 index.html 与 dist sha256 不同")
else: notes.append("ZIP 内 index.html 与 dist sha256 相同：%s" % sha(DIST)[:16])

# --- 2) 根 index.html 与 dist 一致 ---
if sha(ROOT_HTML) != sha(DIST): fails.append("根目录 index.html 与 dist 不一致")
else: notes.append("根 index.html 与 dist sha256 相同")

# --- 3) 零外部引用 ---
pat = {"http(s)://": r"https?://", "fetch(": r"fetch\(", "XMLHttpRequest": r"XMLHttpRequest",
       "WebSocket": r"WebSocket", "<link": r"<link", "<img": r"<img", "import(": r"import\("}
counts = {k: len(re.findall(p, html_txt)) for k, p in pat.items()}
for k, v in counts.items():
    if v: fails.append("dist HTML 出现 %s × %d" % (k, v))
notes.append("外部引用计数 " + json.dumps(counts, ensure_ascii=False))
urls = [(m.start(), html_txt[max(0, m.start() - 60):m.start() + 30]) for m in re.finditer(r"url\(", html_txt)]
url_ok = all(re.search(r"url\(#[A-Za-z0-9_-]+\)", html_txt[max(0, s - 6):s + 30]) for s, _ in urls)
notes.append("url( × %d，均为内联 SVG 内部引用（url(#id)）：%s → %s" % (len(urls), url_ok, [u[1].replace("\n", "\\n")[-42:] for u in urls]))
if not url_ok: fails.append("url( 不是内联 SVG 片段引用")

# --- 4) node --check 内联脚本 ---
a = html_txt.index("<script>") + len("<script>")
b = html_txt.rindex("</script>")
tmp = F("verification/_v21_inline_check.js")
open(tmp, "w", encoding="utf-8").write(html_txt[a:b])
try:
    r = subprocess.run([r"D:\develop\NodeJS\node.exe", "--check", tmp], capture_output=True, text=True, timeout=120)
    node_ok = (r.returncode == 0)
    if not node_ok: fails.append("node --check 失败：" + (r.stderr or "")[:200])
except Exception as e:
    node_ok = False; fails.append("node --check 执行失败：%r" % (e,))
notes.append("node --check 内联脚本：%s" % ("语法通过" if node_ok else "失败"))
os.remove(tmp)

# --- 5) manifest 对账 ---
sv = lambda p: sha(open(F(p), "rb").read())
expect = {
    "ui_sha256": sv(P["game"]), "levels_sha256": sv(P["levels"]),
    "build_sha256": sha(DIST), "zip_sha256": sha(open(ZIP, "rb").read()),
    "zip_bytes": os.path.getsize(ZIP), "html_bytes": len(DIST), "level_count": 50,
}
for k, v in expect.items():
    ok = (MAN.get(k) == v)
    if not ok: fails.append("manifest.%s = %r，实测 %r" % (k, MAN.get(k), v))
    notes.append("manifest.%s 一致=%s" % (k, ok))
if MAN.get("build_output", "").replace("/", "\\") != r"dist\星织-游戏本体\index.html":
    fails.append("manifest.build_output = %r" % MAN.get("build_output"))
if sorted(MAN.get("zip_root_entries", [])) != ["README.txt", "index.html"]:
    fails.append("manifest.zip_root_entries = %r" % MAN.get("zip_root_entries"))
for k, v in (MAN.get("checks") or {}).items():
    if v is not True: fails.append("manifest.checks.%s = %r" % (k, v))
notes.append("manifest.checks = %s（5 项独立复核：levels_roundtrip=A 通过 / offline_selfcontained=本轮无外部引用 / "
             "node_syntax=%s / clue_selfconsistent=A 通过 / zip_root_index=%s）" % (
                 json.dumps(MAN.get("checks"), ensure_ascii=False), node_ok, roots_ok))

print("G ZIP 根条目 :", names)
print("G zip->index sha == dist :", sha(zidx) == sha(DIST), sha(DIST)[:16])
print("G 根 index == dist :", sha(ROOT_HTML) == sha(DIST))
print("G 外部引用计数 :", json.dumps(counts, ensure_ascii=False))
print("G url( :", len(urls), "全为 url(#id) :", url_ok)
print("G node --check :", node_ok)
print("G manifest 对账 :", {k: (MAN.get(k) == v) for k, v in expect.items()})
for n in notes: print("  ·", n)
for f in fails: print("  ✗", f)
print("G_VERDICT", "PASS" if not fails else "FAIL")
