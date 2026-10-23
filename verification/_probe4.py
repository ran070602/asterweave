import re,json,hashlib
h=open(r"verification/frozen_v21/dist_index.html",encoding="utf-8").read()
print("len",len(h))
for pat in ["const LEVELS","const SKY","LEVELS=","SKY=","DBL_MS","lastMouse","introOverlay","actHint","winFlashPending","dataset.gameState","showRuns"]:
    idxs=[m.start() for m in re.finditer(re.escape(pat),h)]
    print(pat, len(idxs), idxs[:8])
print("---- scripts")
for m in re.finditer(r"<script[^>]*>",h):
    print(m.start(), m.group(0)[:120])
print("---- external refs")
for pat in [r"https?://", r"fetch\(", r"XMLHttpRequest", r"WebSocket", r"<link", r"<img", r"import\(", r"url\("]:
    print(pat, len(re.findall(pat,h)))
