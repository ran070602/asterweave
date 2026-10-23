import re
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
print("== winFlashPending 出现:", [(m.start(), h[max(0,m.start()-60):m.start()+40].replace("\n","\\n")) for m in re.finditer("winFlashPending",h)])
print()
for pat in ["结算","换一关","重玩本关","下一关","全部解锁","一键点亮","双击","轻触","长按","右键","单击"]:
    print(pat, len(re.findall(pat,h)))
print()
print("== body 结构（id 顺序）")
pre=h[:h.index("<script>")]
ids=[(m.start(),m.group(1)) for m in re.finditer(r'id="([^"]+)"',pre)]
print([i for _,i in ids])
