import json, collections, re
from pathlib import Path
d = json.loads(Path(r"D:\AI-Native casual game\verification\out_d.json").read_text(encoding="utf-8"))
buckets = collections.OrderedDict()
for r in d["results"]:
    m = re.match(r"^(D\d[a-b]?|SPEC)", r["id"])
    k = m.group(1) if m else r["id"][:8]
    b = buckets.setdefault(k, [0,0])
    b[0] += 1
    if not r["ok"]: b[1] += 1
for k,v in buckets.items():
    print("%-8s 共 %2d 项，不通过 %d" % (k, v[0], v[1]))
print("summary:", d["summary"]["total"], d["summary"]["pass"], d["summary"]["fail"])
print("html_utf8_bytes:", d["summary"]["html_utf8_bytes"], "sha:", d["summary"]["html_sha256"])
