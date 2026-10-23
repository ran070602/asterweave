import re
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
for pat in ["reveal-flash","reveal-stage","winFlashPending","winRevealPending","winRevealDone","prefersReduced","prefers-reduced-motion","revealSkipBound","fast"]:
    print(pat, len(re.findall(re.escape(pat),h)))
print()
for m in re.finditer("reveal-flash",h): print(repr(h[m.start()-120:m.start()+60]))
