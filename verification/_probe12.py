import re
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
a=h.index("/* 通关：星座点亮后整体闪一下")
print(h[a-1500:a+900])
