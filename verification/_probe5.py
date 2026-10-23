import re
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
for m in re.finditer(r"</?script",h):
    print(m.start(), h[m.start():m.start()+60].replace("\n","\\n"))
