import os
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
a=h.index("/* SKY_INJECT_END */")
b=h.index("</script>")
print("SKY_INJECT_END",a,"scriptend",b,"logiclen",b-a)
open(r"verification\v21_logic.js","w",encoding="utf-8").write(h[a:b])
print("html head len",h.index("<script>"))
open(r"verification\v21_pre.html","w",encoding="utf-8").write(h[:h.index("<script>")])
