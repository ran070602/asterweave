import json
K=json.load(open(r"tools/sky.json",encoding="utf-8"))
print(type(K), (list(K.keys())[:12] if isinstance(K,dict) else len(K)))
arr = K["sky"] if isinstance(K,dict) and "sky" in K else K
print("n sky",len(arr))
print(json.dumps(arr[0],ensure_ascii=False)[:1200])
