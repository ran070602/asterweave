import re
DOCS=[r"冉政-设计思路文档.md", r"冉政-迭代优化过程文档.md"]
for p in DOCS:
    s=open(p,encoding="utf-8").read()
    lines=s.split("\n")
    print("="*26,p)
    for i,l in enumerate(lines):
        if l.startswith("|") and "总雷" in l:
            print("  header @L%d: %s"%(i+1,l[:130]))
            j=i+2; n=0; first=None; last=None; cases=[]
            while j<len(lines) and lines[j].startswith("|"):
                cells=[c.strip() for c in lines[j].strip().strip("|").split("|")]
                n+=1
                if first is None: first=cells
                last=cells
                if len(cells)<2 or not cells[0].isdigit(): cases.append(lines[j][:80])
                j+=1
            print("   数据行=%d 首行=%s"%(n,first))
            print("   末行=%s"%(last,))
            if cases: print("   非数字首列行:",cases[:3])
    for kw in ["星图线索","必须用","只用数字","零猜测"]:
        for m in re.finditer(re.escape(kw),s):
            seg=s[max(0,m.start()-160):m.start()+120].replace("\n"," ")
            if "关" in seg or "数" in seg: print("   [%s] ...%s..."%(kw,seg))
