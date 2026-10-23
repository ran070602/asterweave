import json
S=json.load(open(r"tools/level_stats.json",encoding="utf-8"))
print(type(S), (list(S.keys())[:12] if isinstance(S,dict) else len(S)))
print(json.dumps(S if isinstance(S,dict) else S[:3],ensure_ascii=False)[:1800])
print("---- manifest")
M=json.load(open(r"dist/build_manifest.json",encoding="utf-8"))
print(json.dumps(M,ensure_ascii=False,indent=1))
