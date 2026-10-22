import re, io, sys
sys.stdout.reconfigure(encoding="utf-8")
h = open(r"D:\Asterweave\dist\星织-游戏本体\index.html", encoding="utf-8").read()
scripts = re.findall(r"<script[^>]*>([\s\S]*?)</script>", h)
print("script count:", len(scripts), "lens:", [len(s) for s in scripts])
js = scripts[0]
ids = set(re.findall(r'\bid="([^"]+)"', h))
print("static ids:", len(ids))
ids = set()
for m in re.finditer(r"<(\w+)([^>]*?\bid=\"([^\"]+)\"[^>]*?)>", h):
    ids.add(m.group(3))
want = set(re.findall(r"getElementById\(['\"]([^'\"]+)['\"]\)", js))
print("getElementById unique:", len(want))
print("MISSING:", sorted(want - ids))
print("btnNum refs:", len(re.findall(r"btnNum", js)), " btnTotal refs:", len(re.findall(r"btnTotal", js)))
print("skyEls assign block:", re.search(r"const skyEls = \{[\s\S]*?\};", js).group(0))
