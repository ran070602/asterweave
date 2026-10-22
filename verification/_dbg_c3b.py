import json, importlib.util
from pathlib import Path
ROOT = Path(r"D:\AI-Native casual game")
spec = importlib.util.spec_from_file_location("cuni", ROOT/"verification"/"c_uniqueness.py")
cuni = importlib.util.module_from_spec(spec); spec.loader.exec_module(cuni)
lv = json.loads((ROOT/"tools"/"levels.json").read_text(encoding="utf-8"))[2]
ctx = cuni.Ctx(lv)
print("row_opts[4] (%d):" % len(ctx.row_opts[4]))
for p in ctx.row_opts[4]:
    print("   ", "".join(str(x) for x in p))
print("direct call:", ["".join(str(x) for x in p) for p in cuni.row_patterns_exact(7,[1,1],set())])
print("0001010 in direct:", tuple(0,0,0,1,0,1,0) in cuni.row_patterns_exact(7,[1,1],set()))
