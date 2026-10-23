import difflib
a=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
b=open(r"dist/星织-游戏本体/index.html",encoding="utf-8").read()
al=a.split("\n"); bl=b.split("\n")
d=list(difflib.unified_diff(al,bl,"A","B",n=0))
print("total diff lines",len(d))
for l in d: print(l[:190])
print("=== 脚本区（含 LEVELS）以外是否有 JS 变化 ===")
sa=a[a.index("/* SKY_INJECT_END */"):]; sb=b[b.index("/* SKY_INJECT_END */"):]
print("logic len",len(sa),len(sb),"equal:",sa==sb)
import re
def norm(s): return re.sub(r"\s+","",s)
print("logic normalized equal:", norm(sa)==norm(sb))
# 找逻辑区差异
dl=list(difflib.unified_diff(sa.split("\n"),sb.split("\n"),n=1))
print("logic diff lines",len(dl))
for l in dl[:60]: print("  ",l[:180])
