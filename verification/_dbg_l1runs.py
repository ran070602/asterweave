import json, importlib.util, copy
from pathlib import Path
ROOT = Path(r"D:\AI-Native casual game")
spec = importlib.util.spec_from_file_location("cuni", ROOT/"verification"/"c_uniqueness.py")
cuni = importlib.util.module_from_spec(spec); spec.loader.exec_module(cuni)
lv = json.loads((ROOT/"tools"/"levels.json").read_text(encoding="utf-8"))[0]
print("诊断：第1关若把'未显示的' rowRuns/colRuns 也当作约束（即报告表头写的'连续块+数字+雷总数'），解数是多少？")
lv2 = copy.deepcopy(lv); lv2["showRuns"] = True
ctx = cuni.Ctx(lv2)
res = cuni.method_dfs(ctx, True, __import__("time").monotonic()+60)
print("  解数 =", res["solutions"], " 节点 =", res["nodes"])
print("  样本:", res["sols_sample"][:2])
print("而 showRuns=false（真实可见信息）时解数 = 26（见 out_c.json）")
