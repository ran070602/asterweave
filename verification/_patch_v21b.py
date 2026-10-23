for p,old,new in [
 (r"verification/v21_a_data.py",
  'open(os.path.join(ROOT, "verification/frozen_v21/dist_index.html"), encoding="utf-8")',
  'open(os.environ.get("V21_HTML") or os.path.join(ROOT, "verification/frozen_v21b/dist_index.html"), encoding="utf-8")'),
 (r"verification/v21_e_sky.py",
  'open(os.path.join(ROOT, "verification/frozen_v21/dist_index.html"), encoding="utf-8")',
  'open(os.environ.get("V21_HTML") or os.path.join(ROOT, "verification/frozen_v21b/dist_index.html"), encoding="utf-8")'),
]:
    s=open(p,encoding="utf-8").read()
    if old not in s: print("MISS",p); continue
    open(p,"w",encoding="utf-8").write(s.replace(old,new)); print("OK",p)
