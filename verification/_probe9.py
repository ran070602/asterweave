import re
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
for m in re.finditer("双击",h): print("双击@",m.start(),repr(h[m.start()-90:m.start()+40]))
print()
for m in re.finditer("结算",h):
    seg=h[m.start()-45:m.start()+25].replace("\n","\\n")
    print("结算@",m.start(),repr(seg))
print()
print("== 静态按钮文本")
pre=h[:h.index("<script>")]
for m in re.finditer(r'<button[^>]*>(.*?)</button>',pre,re.S):
    print(repr(m.group(0)[:150]))
