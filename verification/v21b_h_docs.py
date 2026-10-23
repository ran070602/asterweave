# -*- coding: utf-8 -*-
"""v21b 复核 H：文档对账（两份冉政-*.md 的 50 行关卡表 vs tools/levels.json + level_stats.json；SPEC 操作契约 vs 实现）"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = open(os.path.join(ROOT, "dist", "星织-游戏本体", "index.html"), encoding="utf-8").read()
LV = json.load(open(os.path.join(ROOT, "tools/levels.json"), encoding="utf-8"))
ST = {x["id"]: x for x in json.load(open(os.path.join(ROOT, "tools/level_stats.json"), encoding="utf-8"))}
SPEC = open(os.path.join(ROOT, "docs", "SPEC.md"), encoding="utf-8").read()

fails, notes = [], []
def chk(name, ok, detail=""):
    print("  %-46s %s %s" % (name, "PASS" if ok else "FAIL", detail))
    if not ok: fails.append(name)
    return ok

TABLES = {
    "冉政-设计思路文档.md": dict(
        file="冉政-设计思路文档.md", title="50 关曲线",
        cols=["关", "星座", "棋盘", "星座星", "杂星", "总雷", "探格次数※", "数织线索贡献", "只用数字能解？"],
        sol="number_only"),
    "冉政-迭代优化过程文档.md": dict(
        file="冉政-迭代优化过程文档.md", title="v1.3 曲线实测",
        cols=["关", "星座", "棋盘", "星座星", "杂星", "总雷", "探格", "数织线索贡献", "必须用星图线索？"],
        sol="must_use_sky"),
}

print("=== H 文档对账 ===")
summary = {}
for key, meta in TABLES.items():
    lines = open(os.path.join(ROOT, meta["file"]), encoding="utf-8").read().split("\n")
    hi = None
    for i, l in enumerate(lines):
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) == len(meta["cols"]) and cells[0] == "关" and cells[1] == "星座":
            hi = i; hdr = cells; break
    if hi is None:
        chk("%s 找到关卡表头" % key, False); continue
    chk("%s 表头逐列一致" % key, hdr == meta["cols"], "%s" % hdr)

    rows = []
    for l in lines[hi + 1:]:
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) != len(meta["cols"]): 
            if rows: break
            continue
        if not re.fullmatch(r"\d+", cells[0]):
            if rows: break
            continue
        rows.append(cells)

    chk("%s 关卡表行数 == 50" % key, len(rows) == 50, "实测 %d 行" % len(rows))
    ids = [int(r[0]) for r in rows]
    chk("%s 关号恰为 1..50" % key, ids == list(range(1, 51)), "%s..%s" % (ids[:3], ids[-3:]))

    bad = []
    n_nb_false = 0
    for r in rows:
        lid = int(r[0]); s = ST[lid]; lv = LV[lid - 1]
        sz = int(re.match(r"(\d+)\s*[×xX]\s*(\d+)", r[2]).group(1))
        exp = dict(星座=(s["name"], lv["theme"]["name"]), 棋盘=sz, 星座星=s["stars"], 杂星=s["noise"],
                   总雷=s["mines"], 探格=s["probes"], 数织线索贡献=s["runs"])
        got = dict(星座=r[1], 棋盘=sz, 星座星=int(r[3]), 杂星=int(r[4]), 总雷=int(r[5]),
                   探格=int(r[6]), 数织线索贡献=int(r[7]))
        # 尺寸：文档棋盘 vs levels.json size（两者都要 == level_stats.size）
        if sz != lv["size"] or s["size"] != lv["size"]:
            bad.append("L%d 尺寸 文档%d levels%d stats%d" % (lid, sz, lv["size"], s["size"]))
        # 星座星 / 杂星 / 总雷：文档 vs stats vs levels.json 三方
        if not (int(r[3]) == s["stars"] == len(lv["theme"]["stars"])):
            bad.append("L%d 星座星 文档%s stats%s levels%d" % (lid, r[3], s["stars"], len(lv["theme"]["stars"])))
        if not (int(r[4]) == s["noise"] == len(lv["noise"])):
            bad.append("L%d 杂星 文档%s stats%s levels%d" % (lid, r[4], s["noise"], len(lv["noise"])))
        if not (int(r[5]) == s["mines"] == len(lv["mines"])):
            bad.append("L%d 总雷 文档%s stats%s levels%d" % (lid, r[5], s["mines"], len(lv["mines"])))
        if int(r[6]) != s["probes"]:
            bad.append("L%d 探格 文档%s stats%s" % (lid, r[6], s["probes"]))
        if int(r[7]) != s["runs"]:
            bad.append("L%d 数织线索贡献 文档%s stats%s" % (lid, r[7], s["runs"]))
        if r[1] != s["name"] or r[1] != lv["theme"]["name"]:
            bad.append("L%d 星座名 文档%s stats%s levels%s" % (lid, r[1], s["name"], lv["theme"]["name"]))
        # 推理门类列：与 level_stats.nb_only 极性强绑定
        txt = r[8]
        if meta["sol"] == "number_only":
            want_yes = s["nb_only"]
            ok = txt.startswith("是") if want_yes else txt.startswith("否")
        else:
            if lid == 1:
                ok = txt.startswith("—") or txt.startswith("-")
            else:
                ok = txt.startswith("是") if not s["nb_only"] else txt.startswith("否")
        if not ok:
            bad.append("L%d 推理列 %r vs nb_only=%s" % (lid, txt, s["nb_only"]))
        if not s["nb_only"]: n_nb_false += 1

    chk("%s 逐格一致（尺寸/星座星/杂星/总雷/探格/线索贡献/星座名）" % key, not bad,
        "差异 %d 处" % len(bad))
    for b in bad[:6]: print("        ✗ " + b)
    summary[key] = n_nb_false
    print("      %s：nb_only=False（必须用第二套线索）= %d 关；表内 authoritative" % (key, n_nb_false))

chk("两份文档对「必须用线索的关数」结论一致", len(set(summary.values())) <= 1, repr(summary))

# 文档里若显式写了关数，核对
doc_txt = {k: open(os.path.join(ROOT, k), encoding="utf-8").read() for k in TABLES}
for k, t in doc_txt.items():
    for m in re.finditer(r"([^\n]{0,40}?)(\d+)\s*关[^\n]{0,20}?(必须用星图|不用数织|纯数字|只用数字)[^\n]{0,30}", t):
        print("      [%s] 关数表述：%s" % (k, m.group(0).strip()[:120]))

# ---- SPEC 操作契约 vs 实现 ----
print("  --- SPEC 操作契约 vs 实现 ---")
chk("SPEC 无模式切换（轻触/长按、单击/右键）", ("无模式切换" in SPEC) and ("轻触" in SPEC) and ("长按" in SPEC))
chk("SPEC 明示无双击标记", ("不做双击标记" in SPEC) or ("双击" in SPEC))
m = re.search(r"长按（?~?(\d+)\s*ms）?", SPEC)
spec_lp = int(m.group(1)) if m else None
impl_lp = int(re.search(r"LONG_PRESS_MS\s*=\s*(\d+)", DIST).group(1))
chk("SPEC 长按阈值 == 实现 LONG_PRESS_MS", spec_lp == impl_lp, "SPEC=%s 实现=%s" % (spec_lp, impl_lp))
m2 = re.search(r"容差（(\d+)\s*px）", SPEC)
impl_tol = int(re.search(r"MOVE_TOL\s*=\s*(\d+)", DIST).group(1))
chk("SPEC 拖动容差 == 实现 MOVE_TOL", (int(m2.group(1)) if m2 else None) == impl_tol,
    "SPEC=%s 实现=%s" % (m2.group(1) if m2 else None, impl_tol))
chk("实现无 DBL_MS / lastMouse（双击标记已移除）",
    "DBL_MS" not in DIST and "lastMouse" not in DIST)
chk("实现 contextmenu 被 preventDefault（长按/右键不弹系统菜单）",
    "addEventListener('contextmenu'" in DIST and "preventDefault" in DIST)
chk("实现无「模式」按钮（无模式切换 UI）",
    not re.search(r"<button[^>]*>[^<]*模式", DIST) and not re.search(r"id=\"[^\"]*[Mm]ode[^\"]*Btn\"", DIST))

# ---- 通关结算条按钮措辞：SPEC 要求「★ 图鉴详情」而非「结算」 ----
win_row = [l for l in SPEC.split("\n") if "通关" in l and "图鉴详情" in l]
chk("SPEC 通关结算条写作「★ 图鉴详情」", bool(win_row) and "结算条" in SPEC,
    (win_row[0].strip()[:110] if win_row else "未找到"))
chk("SPEC 未把通关按钮称作「结算」", not re.search(r"通关[^\n]{0,60}\*\*结算\*\*", SPEC))
# 迭代文档仍写「结算」——历史叙述，与当前实现不符
iter_txt = doc_txt["冉政-迭代优化过程文档.md"]
stale = re.findall(r"[^\n]*\|[^\n]*✅ 通关[^\n]*\*{0,2}结算\*{0,2}[^\n]*", iter_txt)
if stale:
    notes.append("迭代文档仍写「通关 = 结算」：%s" % stale[0].strip()[:100])
    print("      ⚠ 迭代文档残留：%s" % stale[0].strip()[:100])
chk("迭代文档与实现一致（通关按钮非「结算」）", not stale,
    "实现按钮 = ★ 图鉴详情 / ↻ 重来本关 / 下一关 →（见 D3e）")

print("H 失败项 %d" % len(fails))
for f in fails: print("  ✗ " + f)
for n in notes: print("  ⚠ " + n)
print("H_VERDICT", "PASS" if not fails else "FAIL")
