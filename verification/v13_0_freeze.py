# -*- coding: utf-8 -*-
"""v13 step 0: freeze artifacts + sha256. Independent of tools/*.py."""
import hashlib, json, os, shutil, sys, zipfile

ROOT = r"D:\AI-Native casual game"
OUT = os.path.join(ROOT, "verification", "frozen_v13")
os.makedirs(OUT, exist_ok=True)

TARGETS = [
    ("dist_index.html", r"dist\星织-游戏本体\index.html"),
    ("game_index.html", r"game\index.html"),
    ("levels.json", r"tools\levels.json"),
    ("SPEC.md", r"docs\SPEC.md"),
    ("design_doc.md", r"冉政-设计思路文档.md"),
    ("iteration_doc.md", r"冉政-迭代优化过程文档.md"),
    ("build_manifest.json", r"dist\build_manifest.json"),
    ("release.zip", r"星织-游戏本体.zip"),
    ("README.md", r"README.md"),
]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

res = {"root": ROOT, "files": {}}
for label, rel in TARGETS:
    src = os.path.join(ROOT, rel)
    if not os.path.exists(src):
        res["files"][label] = {"rel": rel, "exists": False}
        continue
    dst = os.path.join(OUT, label)
    shutil.copy2(src, dst)
    res["files"][label] = {"rel": rel, "exists": True,
                           "sha256": sha(src), "bytes": os.path.getsize(src),
                           "frozen": os.path.join("verification", "frozen_v13", label)}

# zip listing
zp = os.path.join(ROOT, "星织-游戏本体.zip")
with zipfile.ZipFile(zp) as z:
    res["zip_names"] = z.namelist()
    res["zip_top"] = sorted({n.split("/")[0] for n in z.namelist()})

print(json.dumps(res, ensure_ascii=False, indent=1))
