import json
from pathlib import Path
R = Path(r"D:\AI-Native casual game\verification")
a = json.loads((R/"out_a.json").read_text(encoding="utf-8"))
d = json.loads((R/"out_d.json").read_text(encoding="utf-8"))
b = json.loads((R/"out_b.json").read_text(encoding="utf-8"))
c = json.loads((R/"out_c.json").read_text(encoding="utf-8"))
print("A checks:", len(a["checks"]), "fail:", sum(1 for x in a["checks"] if not x["ok"]), "html:", a["extras"]["html"]["sha256"][:16])
print("D total:", d["summary"]["total"], "pass:", d["summary"]["pass"], "fail:", d["summary"]["fail"], "html:", d["summary"]["html_sha256"][:16], d["summary"]["html_path"])
for l in b["levels"]:
    print("B L%d a_only=%s a+b=%s a=%d b=%d digs=%d | a_only remaining=%d" % (
        l["id"], l["a_only"]["complete"], l["a_plus_b"]["complete"], l["a_plus_b"]["steps_a"],
        l["a_plus_b"]["steps_b"], l["a_plus_b"]["explicit_reveals"], l["a_only"]["unknown_left"]))
for l in c["levels"]:
    print("C L%d full=%d nodes=%d t=%ss cross=%s(%s) | no_numbers=%d" % (
        l["id"], l["full"]["solutions"], l["full"]["nodes"], l["full"]["elapsed_s"],
        l["cross_check_agree"], l.get("cross_check_solutions"), l["no_numbers"]["solutions"]))
print("D failed ids:", [x["id"] for x in d["summary"]["failed"]])
