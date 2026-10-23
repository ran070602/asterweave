import json,io
L=json.load(open(r"tools/levels.json",encoding="utf-8"))
print(type(L))
if isinstance(L,dict): print(list(L.keys())[:50])
lv = L["levels"] if isinstance(L,dict) and "levels" in L else L
print("n levels",len(lv))
print(json.dumps(lv[0],ensure_ascii=False)[:2500])
