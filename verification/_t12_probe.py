# -*- coding: utf-8 -*-
"""T12 复核用：冻结/当前产物的 sha256 对照 + manifest 字节编码 + ZIP 条目明细。"""
import hashlib
import json
import pathlib
import zipfile

ROOT = pathlib.Path(r"D:\AI-Native casual game")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


pairs = [
    ("frozen10 dist snapshot", ROOT / "verification/frozen10/dist_index_snapshot.html"),
    ("cur dist index.html", ROOT / "dist/冉政-游戏本体/index.html"),
    ("frozen10 release.zip", ROOT / "verification/frozen10/release.zip"),
    ("cur root zip", ROOT / "冉政-游戏本体.zip"),
    ("frozen10 levels", ROOT / "verification/frozen10/levels_10levels.json"),
    ("cur tools/levels.json", ROOT / "tools/levels.json"),
    ("frozen10 report", ROOT / "verification/frozen10/report_10levels.md"),
    ("cur tools/report.md", ROOT / "tools/report.md"),
    ("frozen10 SPEC_v1.1", ROOT / "verification/frozen10/SPEC_v1.1.md"),
    ("cur docs/SPEC.md", ROOT / "docs/SPEC.md"),
    ("frozen10 build_manifest", ROOT / "verification/frozen10/build_manifest.json"),
    ("cur dist/build_manifest.json", ROOT / "dist/build_manifest.json"),
    ("frozen10 design_doc", ROOT / "verification/frozen10/design_doc.md"),
    ("cur 设计思路文档", ROOT / "冉政-设计思路文档.md"),
    ("frozen10 iteration_doc", ROOT / "verification/frozen10/iteration_doc.md"),
    ("cur 迭代优化过程文档", ROOT / "冉政-迭代优化过程文档.md"),
]
print("== 冻结副本 vs 当前产物 sha256 ==")
for label, p in pairs:
    print("%-34s %s  %s" % (label, sha(p) if p.exists() else "MISSING", p.stat().st_size if p.exists() else "-"))

print()
print("== dist/build_manifest.json 原始字节 ==")
raw = (ROOT / "dist/build_manifest.json").read_bytes()
print("bytes =", len(raw), "| BOM =", raw[:3] == b"\xef\xbb\xbf")
try:
    txt = raw.decode("utf-8")
    print("utf-8 decode: OK")
except Exception as e:
    txt = raw.decode("utf-8", "replace")
    print("utf-8 decode FAILED:", e)
print("--- 原文 ---")
print(txt)
m = json.loads(txt)
print("--- 解析后的路径字段（原始码点） ---")
for k in ("ui_source", "build_output", "zip", "levels_source"):
    if k in m:
        print("%-14s %r" % (k, m[k]))

print()
print("== 根目录 ZIP 条目 ==")
with zipfile.ZipFile(ROOT / "冉政-游戏本体.zip") as z:
    info = z.infolist()
    print("条目数 =", len(info))
    for i in info:
        data = z.read(i.filename)
        print("  %-14r size=%-6d sha256=%s" % (i.filename, i.file_size, hashlib.sha256(data).hexdigest()))
    inner = z.read("index.html")
print("ZIP 内 index.html sha256 =", hashlib.sha256(inner).hexdigest())
print("dist  index.html sha256 =", sha(ROOT / "dist/冉政-游戏本体/index.html"))
print("逐字节一致 =", inner == (ROOT / "dist/冉政-游戏本体/index.html").read_bytes())