import re
for p in [r"冉政-设计思路文档.md", r"冉政-迭代优化过程文档.md", r"docs/SPEC.md"]:
    s=open(p,encoding="utf-8").read()
    print("="*24,p)
    for kw in ["星座星","杂星","线索贡献","50 关","50关","探格"]:
        idx=[m.start() for m in re.finditer(re.escape(kw),s)]
        print("  ",kw,len(idx))
    # 打印含表头的行
    for m in re.finditer(r"^\|.*(星座|探格|线索|杂星).*$",s,re.M):
        print("   >",m.group(0)[:150])
