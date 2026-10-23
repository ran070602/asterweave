import re
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
for m in re.finditer(r"reveal-stage",h):
    print("---",m.start()); print(h[m.start()-140:m.start()+320])
