import re
for tag,p in [("frozen_1126",r"verification/frozen_v21/dist_index.html"),("live_1206",r"dist/星织-游戏本体/index.html")]:
    h=open(p,encoding="utf-8").read()
    m=re.search(r"\n  \.overlay\{",h)
    print(tag, "'.overlay{' 基础规则存在:", bool(m))
    if m: print("   ", h[m.start():m.start()+260].replace("\n","\\n"))
    m2=re.search(r"\n  \.overlay\.open\{",h)
    print("   .overlay.open:", h[m2.start():m2.start()+120].replace("\n","\\n") if m2 else None)
    print("   orphan 行 'font-weight:800;color:#08111f;background' 出现:", h.count("font-weight:800;color:#08111f;background"))
    print()
