#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键跑全部运行时测试套件（verification/v*_test.js），汇总并通过/失败判定退出码。

用法：
    python tools/run_tests.py            # 跑全部
    python tools/run_tests.py v22 v23    # 只跑名字含这些片段的套件

约定：
  · 每个套件是 `node <file>`，脚本自身打印 `SUMMARY pass=N fail=M` 并以退出码表示成败；
  · 本脚本只在**全部套件都通过**时返回 0，任何一套失败或崩溃（含加载期异常）都返回 1 并列出原因。
  · 套件读取 `dist/星织-游戏本体/index.html`——**跑之前请先构建**（`python tools/build_release.py`），
    否则测的是上一版产物。本脚本会打印该文件的 sha256 与字节数，便于与构建记录对齐。
"""
import glob
import hashlib
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODE = r"D:\develop\NodeJS\node.exe" if os.path.exists(r"D:\develop\NodeJS\node.exe") else "node"
DIST = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")

filters = [a for a in sys.argv[1:] if not a.startswith("-")]
files = sorted(glob.glob(os.path.join(ROOT, "verification", "v*_test.js")))
if filters:
    files = [f for f in files if any(k in os.path.basename(f) for k in filters)]

if not os.path.exists(DIST):
    print("!! 找不到 %s，请先 `python tools/build_release.py`" % DIST)
    sys.exit(2)
raw = io.open(DIST, "rb").read()
print("被测产物：dist/星织-游戏本体/index.html  %d 字节  sha256=%s…" %
      (len(raw), hashlib.sha256(raw).hexdigest()[:16]))
print("套件 %d 个\n" % len(files))

rows, total_pass, total_fail, bad = [], 0, 0, []
for f in files:
    name = os.path.basename(f)
    r = subprocess.run([NODE, f], cwd=ROOT, capture_output=True, text=True, errors="ignore")
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(r"SUMMARY\s+pass=(\d+)\s+fail=(\d+)", out)
    if m:
        p, fl = int(m.group(1)), int(m.group(2))
        total_pass += p
        total_fail += fl
        ok = (fl == 0 and r.returncode == 0)
        rows.append((name, p, fl, r.returncode, "OK" if ok else "FAIL"))
        if not ok:
            bad.append((name, "有失败断言" if fl else "退出码非 0"))
    else:
        tail = [l.strip() for l in out.strip().splitlines() if l.strip()][-1:] or ["(无输出)"]
        rows.append((name, 0, 0, r.returncode, "CRASH"))
        bad.append((name, "未打印 SUMMARY（大概率加载期异常）：" + tail[0][:120]))

w = max(len(r[0]) for r in rows) if rows else 10
for name, p, fl, code, status in rows:
    print("  %-*s  pass=%-4d fail=%-4d exit=%-3d %s" % (w, name, p, fl, code, status))
print("\n  合计：pass=%d fail=%d（%d 套，%d 套通过）" %
      (total_pass, total_fail, len(rows), sum(1 for r in rows if r[4] == "OK")))
if bad:
    print("\n失败明细：")
    for name, why in bad:
        print("  · %s：%s" % (name, why))
    sys.exit(1)
print("\n✅ 全部套件通过")
