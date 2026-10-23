import difflib,re
a=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
b=open(r"dist/星织-游戏本体/index.html",encoding="utf-8").read()
print("len",len(a),len(b))
al=a.split("\n"); bl=b.split("\n")
print("lines",len(al),len(bl))
d=list(difflib.unified_diff(al,bl,"frozen_1126","live_1206",n=1))
print("diff hunks lines:",len(d))
out=[l for l in d]
# 只打印非关卡数据的差异（跳过巨长 JSON 区块）
for l in out[:250]:
    print(l[:200])
