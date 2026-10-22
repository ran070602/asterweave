# -*- coding: utf-8 -*-
"""T12：把「当前」被复核产物冻结到 verification/frozen11/（供 t11_release_check.py 复现同一修订）。"""
import hashlib
import pathlib
import shutil

ROOT = pathlib.Path(r"D:\AI-Native casual game")
DST = ROOT / "verification" / "frozen11"
DST.mkdir(parents=True, exist_ok=True)

MAP = [
    (ROOT / "dist/冉政-游戏本体/index.html", "dist_index_snapshot.html"),
    (ROOT / "冉政-游戏本体.zip", "release.zip"),
    (ROOT / "tools/levels.json", "levels_10levels.json"),
    (ROOT / "tools/report.md", "report_10levels.md"),
    (ROOT / "dist/build_manifest.json", "build_manifest.json"),
    (ROOT / "docs/SPEC.md", "SPEC_v1.2.md"),
    (ROOT / "冉政-设计思路文档.md", "design_doc.md"),
    (ROOT / "冉政-迭代优化过程文档.md", "iteration_doc.md"),
    (ROOT / "tools/independent_counts.json", "independent_counts.json"),
]

print("== 冻结到 %s ==" % DST)
for src, name in MAP:
    shutil.copyfile(src, DST / name)
    h = hashlib.sha256((DST / name).read_bytes()).hexdigest()
    print("  %-28s %s  %d bytes" % (name, h, (DST / name).stat().st_size))