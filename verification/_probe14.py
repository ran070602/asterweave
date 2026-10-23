h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
for s in ["S.status = 'won';","winRevealDone = false;","winRevealPending = true;","render();","startBoardReveal(alreadyCleared);"]:
    import re
    print(repr(s), [m.start() for m in re.finditer(re.escape(s),h)][:6])
a=h.index("function checkWin")
print(repr(h[a:a+430]))
