import re
for p in [r"冉政-迭代优化过程文档.md", r"docs/SPEC.md"]:
    s=open(p,encoding="utf-8").read()
    print("="*24,p,len(s),"chars")
    for m in re.finditer(r"^#{1,4} .*$",s,re.M): print("  H:",m.group(0)[:110])
    print("  table rows:",len(re.findall(r"^\|",s,re.M)))
