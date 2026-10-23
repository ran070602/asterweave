import json,re
s=open(r"docs/SPEC.md",encoding="utf-8").read()
print("=== SPEC 头部 ===")
print("\n".join(s.split("\n")[:14]))
print("=== SPEC 玩法定义 / 两种操作 ===")
a=s.index("## 1. 玩法定义"); b=s.index("## 2.")
print(s[a:b][:2000])
print("=== SPEC 3. 难度带 ===")
c=s.index("## 3."); d=s.index("## 4.")
print(s[c:d][:1200])
print("=== SPEC 里 双击/模式/结算/命数 出现次数 ===")
for k in ["双击","模式","结算","3 条","三条","命数","50"]:
    print("  ",k,len(re.findall(k,s)))
