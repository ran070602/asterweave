h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
for pos in (274418,381109,37616,35778,36317,336359,370099,350627):
    print("=== ",pos)
    print(repr(h[pos-200:pos+260]))
    print()
