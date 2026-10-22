# -*- coding: utf-8 -*-
"""v13 H：文档对账（两份冉政文档的 50 行关卡表 / README / 改名 / SPEC）。"""
import json, os, re, zipfile

ROOT = r"D:\AI-Native casual game"
LV = json.load(open(os.path.join(ROOT, "tools", "levels.json"), encoding="utf-8"))
B = json.load(open(os.path.join(ROOT, "verification", "v13_out_b.json"), encoding="utf-8"))

def read(p): return open(p, encoding="utf-8").read()

def parse_table(path, must_cols):
    lines = read(path).split("\n")
    hi = None
    for i, L in enumerate(lines):
        cells = [c.strip() for c in L.strip().strip("|").split("|")]
        if all(c in cells for c in must_cols) and len(cells) >= 8:
            hi = i; break
    assert hi is not None, "表头未找到: " + path
    header = [c.strip() for c in lines[hi].strip().strip("|").split("|")]
    sep = lines[hi + 1].strip()
    rows = []
    j = hi + 2
    while j < len(lines):
        L = lines[j]
        if not L.strip().startswith("|"): break
        cells = [c.strip() for c in L.strip().strip("|").split("|")]
        if len(cells) < len(header): break
        rows.append(cells); j += 1
    return dict(header_line=hi + 1, header=header, sep_line=hi + 2,
                sep_is_separator=bool(re.match(r"^\|[\s\-:|]+\|?$", sep)),
                body_start=hi + 3, body_end=j, rows=rows)

out = {}
for name, fn, extra in [("design", "冉政-设计思路文档.md", "只用数字能解？"),
                        ("iteration", "冉政-迭代优化过程文档.md", "必须用星图线索？")]:
    t = parse_table(os.path.join(ROOT, fn), ["星座", "杂星", "总雷"])
    mism = []
    for r, L in zip(t["rows"], LV):
        n = L["size"]
        exp = [str(L["id"]), L["theme"]["name"], "%d×%d" % (n, n), str(len(L["theme"]["stars"])),
               str(len(L["noise"])), str(len(L["mines"]))]
        got = [r[0], r[1], r[2], r[3], r[4], r[5]]
        if got != exp:
            mism.append("第%s行 表=%s 实测=%s" % (r[0], got, exp))
    # 探格列 & 最后一列（按表头名定位，避免列序差异）
    idx = {c: i for i, c in enumerate(t["header"])}
    iD = next((i for i, c in enumerate(t["header"]) if "探格" in c), None)
    iC = next((i for i, c in enumerate(t["header"]) if "数织" in c), None)
    iL = len(t["header"]) - 1
    digs = [r[iD] for r in t["rows"]]
    contrib = [r[iC] for r in t["rows"]]
    lastc = [r[iL] for r in t["rows"]]
    out[name] = dict(file=fn, header_line=t["header_line"], sep_is_separator=t["sep_is_separator"],
                     body_start=t["body_start"], body_end=t["body_end"], body_rows=len(t["rows"]),
                     header_cols=len(t["header"]), mismatches=mism, digs=digs, contrib=contrib,
                     last_col_name=t["header"][iL], last_col=lastc, header=t["header"])

# 探格 / 仅邻域解 与独立求解器、项目自带 level_stats.json 交叉
stats = {s["id"]: s for s in json.load(open(os.path.join(ROOT, "tools", "level_stats.json"), encoding="utf-8"))}
mine_need = sorted(int(k) for k, v in B.items() if not v["r1_only"])
for k, d in out.items():
    if k == "design":
        doc_r1only = [r.startswith("是") for r in d["last_col"]]      # 只用数字能解？
        doc_need_rows = [i + 1 for i, x in enumerate(doc_r1only) if not x]
    else:
        doc_need_rows = [i + 1 for i, r in enumerate(d["last_col"]) if r.startswith("是")]
    d["doc_need_rows"] = doc_need_rows
    d["solver_need_rows"] = mine_need
    d["need_match"] = doc_need_rows == mine_need
    d["probe_vs_doc"] = [(i + 1, int(d["digs"][i]), stats[i + 1]["probes"]) for i in range(len(d["digs"]))
                         if int(d["digs"][i]) != stats[i + 1]["probes"]]
    d["digs_vs_solver"] = [(i + 1, int(d["digs"][i]), B[str(i + 1)]["digs"]) for i in range(len(d["digs"]))
                           if int(d["digs"][i]) != B[str(i + 1)]["digs"]]
    d["contrib_vs_stats"] = [(i + 1, d["contrib"][i], stats[i + 1]["runs"]) for i in range(len(d["contrib"]))
                             if str(stats[i + 1]["runs"]) != str(d["contrib"][i])]
    d["nb_only_stats"] = sorted(i for i, s in stats.items() if s["nb_only"])
    d["nb_only_match_solver"] = d["nb_only_stats"] == [i for i in range(1, 51) if str(i) in B and B[str(i)]["r1_only"]]

print("=== H 文档对账 ===")
for k, d in out.items():
    print("[%s] %s" % (k, d["file"]))
    print("  表头行 L%d（%d 列：%s）" % (d["header_line"], d["header_cols"], " | ".join(d["header"])))
    print("  分隔行存在且为分隔线: %s | 表体 L%d–L%d 共 %d 行（期望 50）" % (
        d["sep_is_separator"], d["body_start"], d["body_end"], d["body_rows"]))
    print("  星座/尺寸/星座星/杂星/总雷 与 levels.json 不符: %d 处" % len(d["mismatches"]))
    for m in d["mismatches"][:6]: print("    -", m)
    print("  最后列「%s」推出“必须用星图线索”的关: %d 个；独立求解器需数织的关: %d 个 → %s" % (
        d["last_col_name"], len(d["doc_need_rows"]), len(mine_need), "一致" if d["need_match"] else "不一致"))
    if not d["need_match"]:
        print("    文档称“不需要数织”=%s / 求解器仅邻域可解=%s" % (
            [i for i in range(1, 51) if i not in d["doc_need_rows"]],
            [i for i in range(1, 51) if i not in mine_need]))
    print("  数织线索贡献列 vs level_stats.runs 不符: %d 处 %s" % (len(d["contrib_vs_stats"]), d["contrib_vs_stats"][:5]))
    print("  探格列 vs level_stats.probes 不符: %d 处 %s" % (len(d["probe_vs_doc"]), d["probe_vs_doc"][:6]))
    print("  探格列(文档 %s…%s) vs 本求解器(%s…%s) 不符: %d/50 处，最大差 %d" % (
        d["digs"][0], d["digs"][-1], min(v["digs"] for v in B.values()), max(v["digs"] for v in B.values()),
        len(d["digs_vs_solver"]), max(abs(a - b) for _, a, b in d["digs_vs_solver"]) if d["digs_vs_solver"] else 0))
    print("  level_stats.nb_only=%s 与求解器一致: %s" % (d["nb_only_stats"], d["nb_only_match_solver"]))

# README / 改名 / SPEC
root_readme = read(os.path.join(ROOT, "README.md"))
zreadme = zipfile.ZipFile(os.path.join(ROOT, "星织-游戏本体.zip")).read("README.txt").decode("utf-8")
spec = read(os.path.join(ROOT, "docs", "SPEC.md"))
d1, d2 = read(os.path.join(ROOT, "冉政-设计思路文档.md")), read(os.path.join(ROOT, "冉政-迭代优化过程文档.md"))
checks = {
    "README.md 提及图鉴": "图鉴" in root_readme,
    "README.md 说明玩法（观测/标记）": ("观测" in root_readme and "标记" in root_readme),
    "README.md 提到全部解锁": "全部解锁" in root_readme,
    "README.txt(包内) 提及图鉴": "图鉴" in zreadme,
    "README.txt(包内) 说明玩法": ("观测" in zreadme and "标记" in zreadme),
    "README.txt(包内) 提到全部解锁": "全部解锁" in zreadme,
    "README/文档已改名 星织": "星织" in root_readme and "星织" in zreadme,
    "英文名 Asterweave 出现": "Asterweave" in root_readme and "Asterweave" in zreadme,
    "SPEC 已改名 星织/Asterweave": ("星织" in spec) and ("Asterweave" in spec),
    "设计文档已改名": "星织" in d1, "迭代文档已改名": "星织" in d2,
    "SPEC 版本号": (re.search(r"v1\.\d+", spec) or re.search(r"\*\*v1\.\d+\*\*", spec)).group(0) if re.search(r"v1\.\d+", spec) else "未找到",
    "设计文档仍写「10 关曲线」标题但表格 50 行": bool(re.search(r"10 关曲线", d1)),
}
print()
for k, v in checks.items(): print("  %-34s %s" % (k, v))
# 旧名残留检查
for label, txt in [("README.md", root_readme), ("README.txt", zreadme), ("SPEC.md", spec),
                   ("设计文档", d1), ("迭代文档", d2)]:
    old = [w for w in ["迷阵", "迷宫", "雷线", "leixian.migong", "星织-游戏本体"] if w in txt]
    print("  %-10s 旧名/可疑残留词: %s" % (label, old))
# 具体数值主张 vs 实测
claims = {}
empty_rc, noise_n, dens = [], [], []
for L in LV:
    n = L["size"]
    mine = {r * n + c for r, c in L["mines"]}   # 注意：n 必须先赋值，否则集合推导式会用到上一关的 n
    er = sum(1 for r in range(n) if not any(r * n + c in mine for c in range(n)))
    ec = sum(1 for c in range(n) if not any(r * n + c in mine for r in range(n)))
    if er or ec: empty_rc.append((L["id"], er, ec))
    noise_n.append((L["id"], len(L["noise"])))
    dens.append(len(mine) / (n * n) * 100)
claims["有空行/空列的关"] = empty_rc
claims["第 1 关杂星数"] = noise_n[0][1]
claims["前 10 关杂星数"] = [c for _, c in noise_n[:10]]
claims["杂星总数范围"] = (min(c for _, c in noise_n), max(c for _, c in noise_n))
claims["雷密度范围/均值"] = (round(min(dens), 1), round(max(dens), 1), round(sum(dens) / 50, 1))
claims["尺寸集合"] = sorted({L["size"] for L in LV})
claims["后半段(26-50)雷数范围"] = (min(len(LV[i]["mines"]) for i in range(25, 50)),
                                   max(len(LV[i]["mines"]) for i in range(25, 50)))
print()
print("=== 文档具体主张 vs 实测 ===")
for k, v in claims.items(): print("  %-26s %s" % (k, v))
d1n, d2n = d1, d2
print("  [旧稿主张是否已订正]")
print("   设计文档仍写「杂星（1–2 颗）」: {}（期望 False）".format("（1–2 颗）" in d1n))
print("   仍写「目标雷密度约 18%」: {}（期望 False）".format("约 18%" in d1n))
print("   仍有「10 关曲线」标题: {}（期望 False）".format(re.search(r"10 关曲线", d1n) is not None))
print("   已给出杂星实测区间「6–22」: {}（期望 True）".format("6–22" in d1n and "6–22" in d2n))
print("   已给出密度实测「15.6%–24.0%」: {}（期望 True）".format("15.6%–24.0%" in d1n and "15.6%–24.0%" in d2n))
print("   已把「每行每列」补上第 1 关例外: {}（期望 True）".format("第 1 关走降级例外" in d1n))
print("   已把探格列标注为生成器口径: {}（期望 True）".format("生成器口径" in d1n and "生成器口径" in d2n))
print("   两份文档标题均已改为 50 关: {}（期望 True）".format("50 关曲线" in d1n and "全量 50 关" in d2n))

json.dump(dict(tables={k: {kk: vv for kk, vv in d.items() if kk != "rows"} for k, d in out.items()},
               checks=checks, claims=claims), open(os.path.join(ROOT, "verification", "v13_out_h.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
