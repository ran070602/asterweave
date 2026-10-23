import re,os
ROOT=r"D:\Asterweave"
targets=[(r"冉政-设计思路文档.md",["探格 19–47","7×7–11×11","15.6%","杂星 6–22","6 颗","第 1 关"]),
         (r"冉政-迭代优化过程文档.md",["7×7–11×11","15.6%","杂星 6–22","探格 19–47"]),
         (r"docs/SPEC.md",["10 关初版","teach","v1.7","## 4.","v1.4"])]
for p,kws in targets:
    s=open(os.path.join(ROOT,p),encoding="utf-8").read().split("\n")
    print("="*20,p)
    for i,l in enumerate(s):
        for k in kws:
            if k in l:
                print("  L%-4d [%s] %s"%(i+1,k,l.strip()[:150])); break
