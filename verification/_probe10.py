h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
pre=h[:h.index("<script>")]
b=pre.index("<body")
print(pre[b:])
