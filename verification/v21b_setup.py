# -*- coding: utf-8 -*-
"""v21b：把上一轮独立实现的 v21_* 校验器冻结为本轮 v21b_* 快照，
   并把「HTML 来源」从 frozen_v21b/dist_index.html 改为当前 dist 构建产物，
   输出文件全部改名，避免与并发写入者冲突。只写 verification/。"""
import hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, "verification")
LIVE = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")

def rd(p):
    return open(os.path.join(V, p), encoding="utf-8").read()

def wr(p, s):
    open(os.path.join(V, p), "w", encoding="utf-8", newline="\n").write(s)

manifest = {}

# --- 1) v21_stub.js -> v21b_stub.js : 默认 HTML 指向当前 dist ---
s = rd("v21_stub.js")
assert "frozen_v21b" in s, "stub 默认路径已变化，需人工检查"
s = s.replace("path.join(__dirname, 'frozen_v21b', 'dist_index.html')",
              "path.join(__dirname, '..', 'dist', '星织-游戏本体', 'index.html')")
assert "frozen_v21b" not in s
wr("v21b_stub.js", s)

# --- 2) v21_play.js -> v21b_play.js : 读 v21b_solution.json / 当前 tools ---
s = rd("v21_play.js")
s = s.replace("'v21_solution.json'", "'v21b_solution.json'")
s = s.replace("path.join(__dirname, 'frozen_v21b', 'levels.json')",
              "path.join(__dirname, '..', 'tools', 'levels.json')")
s = s.replace("path.join(__dirname, 'frozen_v21b', 'sky.json')",
              "path.join(__dirname, '..', 'tools', 'sky.json')")
assert "frozen_v21b" not in s and "v21_solution" not in s
wr("v21b_play.js", s)

# --- 3) v21_a_data.py -> v21b_a_data.py : 默认 HTML 指向当前 dist ---
s = rd("v21_a_data.py")
s = re.sub(r'os\.path\.join\(ROOT, "verification/frozen_v21b/dist_index\.html"\)',
           'os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")', s)
assert "frozen_v21b" not in s, s[s.find("frozen_v21b") - 200:s.find("frozen_v21b") + 120]
wr("v21b_a_data.py", s)

# --- 4) v21_b_solve.py -> v21b_b_solve.py : 输出改名 ---
s = rd("v21_b_solve.py")
s = s.replace('"verification/v21_out_b.json"', '"verification/v21b_out_b.json"')
s = s.replace('"verification/v21_solution.json"', '"verification/v21b_solution.json"')
assert "v21_out_b" not in s.replace("v21b_out_b", "") and "v21_solution" not in s.replace("v21b_solution", "")
wr("v21b_b_solve.py", s)

# --- 5) v21_c_metrics.py -> v21b_c_metrics.py : 读 v21b 中间产物 ---
s = rd("v21_c_metrics.py")
s = s.replace('"verification/v21_out_b.json"', '"verification/v21b_out_b.json"')
s = s.replace('"verification/v21_out_c.json"', '"verification/v21b_out_c.json"')
assert "v21_out_" not in s.replace("v21b_out_", "")
wr("v21b_c_metrics.py", s)

# --- 6) v21_d_dom.js -> v21b_d_dom.js : 依赖与输出改名，HTML 用当前 dist ---
s = rd("v21_d_dom.js")
s = s.replace("require('./v21_stub.js')", "require('./v21b_stub.js')")
s = s.replace("require('./v21_play.js')", "require('./v21b_play.js')")
s = s.replace("path.join(__dirname, 'frozen_v21b', 'dist_index.html')",
              "path.join(__dirname, '..', 'dist', '星织-游戏本体', 'index.html')")
s = s.replace("'v21_out_d.json'", "'v21b_out_d.json'")
assert "frozen_v21b" not in s and "v21_out_" not in s.replace("v21b_out_", "")
wr("v21b_d_dom.js", s)

# --- 7) v21_e_dom.js -> v21b_e_dom.js ---
s = rd("v21_e_dom.js")
s = s.replace("require('./v21_stub.js')", "require('./v21b_stub.js')")
s = s.replace("require('./v21_play.js')", "require('./v21b_play.js')")
s = s.replace("path.join(__dirname, 'frozen_v21b', 'dist_index.html')",
              "path.join(__dirname, '..', 'dist', '星织-游戏本体', 'index.html')")
s = re.sub(r"'v21_out_e\.json'", "'v21b_out_e.json'", s)
assert "frozen_v21b" not in s and "v21_out_" not in s.replace("v21b_out_", "")
wr("v21b_e_dom.js", s)

# --- 8) v21_f_anim.js -> v21b_f_anim.js ---
s = rd("v21_f_anim.js")
s = s.replace("require('./v21_stub.js')", "require('./v21b_stub.js')")
s = s.replace("require('./v21_play.js')", "require('./v21b_play.js')")
s = s.replace("path.join(__dirname, 'frozen_v21b', 'dist_index.html')",
              "path.join(__dirname, '..', 'dist', '星织-游戏本体', 'index.html')")
s = s.replace("'v21_out_f.json'", "'v21b_out_f.json'")
assert "frozen_v21b" not in s and "v21_out_" not in s.replace("v21b_out_", "")
wr("v21b_f_anim.js", s)

for f in ["v21b_stub.js", "v21b_play.js", "v21b_a_data.py", "v21b_b_solve.py",
          "v21b_c_metrics.py", "v21b_d_dom.js", "v21b_e_dom.js", "v21b_f_anim.js"]:
    b = open(os.path.join(V, f), "rb").read()
    manifest[f] = hashlib.sha256(b).hexdigest()

src = hashlib.sha256(open(LIVE, "rb").read()).hexdigest()
print("LIVE dist/index.html sha256 =", src)
print("字节 =", os.path.getsize(LIVE))
for k, v in manifest.items():
    print("%-18s %s" % (k, v[:16]))
