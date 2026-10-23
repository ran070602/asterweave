import re,io
for p,old,new in [
 (r"verification/v21_d_dom.js",
  "const HTML = fs.readFileSync(path.join(__dirname, 'frozen_v21', 'dist_index.html'), 'utf8');",
  "const HTML = fs.readFileSync(process.env.V21_HTML || path.join(__dirname, 'frozen_v21b', 'dist_index.html'), 'utf8');"),
 (r"verification/v21_f_anim.js",
  "const HTML = fs.readFileSync(path.join(__dirname, 'frozen_v21', 'dist_index.html'), 'utf8');",
  "const HTML = fs.readFileSync(process.env.V21_HTML || path.join(__dirname, 'frozen_v21b', 'dist_index.html'), 'utf8');"),
 (r"verification/v21_play.js",
  "frozen_v21', 'levels.json'", "frozen_v21b', 'levels.json'"),
 (r"verification/v21_play.js",
  "frozen_v21', 'sky.json'", "frozen_v21b', 'sky.json'"),
 (r"verification/v21_d_dom.js",
  "require('./v21_play.js')", "require('./v21_play.js')"),
]:
    s=open(p,encoding="utf-8").read()
    if old not in s: print("MISS",p,old[:60]); continue
    s=s.replace(old,new); open(p,"w",encoding="utf-8").write(s); print("OK",p,old[:50])
