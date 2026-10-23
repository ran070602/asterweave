import re
for p in [r"冉政-设计思路文档.md", r"冉政-迭代优化过程文档.md", r"docs/SPEC.md"]:
    s=open(p,encoding="utf-8").read()
    print("="*20,p,len(s),"chars", s.count("\n")+1,"lines")
    for m in re.finditer(r"^\|.*$",s,re.M):
        print("   TBL:",m.group(0)[:160])
        if m.start()> 0 and False: pass
    print()
