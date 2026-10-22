# -*- coding: utf-8 -*-
"""v13 A (数据自洽) + C (难度指标独立统计)。

独立实现：不 import / 不复制 tools/{generate_levels,fit_constellation_levels,gen_difficulty_first}.py。
数据来源：tools/levels.json + dist/星织-游戏本体/index.html 内嵌 LEVELS。
"""
import json, os, re, sys

ROOT = r"D:\AI-Native casual game"
LV = os.path.join(ROOT, "tools", "levels.json")
DIST = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")

def load_dist_block(path, name):
    s = open(path, encoding="utf-8").read()
    m = re.search(r"const " + name + r" = (\[.*?\n\]);\n/\* " + name + r"_INJECT_END \*/", s, re.S)
    assert m, "block %s not found" % name
    return m.group(1), json.loads(m.group(1))

def nbrs_of(i, n):
    r, c = divmod(i, n)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0: continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n: yield rr * n + cc

def runs_of(mine, n, by_row, k):
    out, cur = [], 0
    for t in range(n):
        i = k * n + t if by_row else t * n + k
        if i in mine: cur += 1
        else:
            if cur: out.append(cur)
            cur = 0
    if cur: out.append(cur)
    return out

def flood_reveal(start, n, mine, counts):
    """独立 flood fill：从 start 展开 0 区（与 SPEC 语义一致）。返回已翻开集合。"""
    seen, stack = set(), [start]
    while stack:
        i = stack.pop()
        if i in seen or i in mine: continue
        seen.add(i)
        if counts[i] == 0:
            stack.extend(j for j in nbrs_of(i, n) if j not in mine)
    return seen

def main():
    lv = json.load(open(LV, encoding="utf-8"))
    emb_text, emb = load_dist_block(DIST, "LEVELS")
    _sky_text, sky = load_dist_block(DIST, "SKY")

    fails, warn = [], []
    rows = []
    seen_ids, seen_names = {}, {}

    A = lambda cond, msg: (None if cond else fails.append(msg))

    A(len(lv) == 50, "levels.json 关数=%d != 50" % len(lv))
    A(len(emb) == 50, "HTML 内嵌关数=%d != 50" % len(emb))

    # A6 内嵌 == json（结构等价 + 规范化字节等价）
    if json.loads(json.dumps(emb, sort_keys=True)) != json.loads(json.dumps(lv, sort_keys=True)):
        fails.append("内嵌 LEVELS 与 levels.json 结构不等价")
    canon = json.dumps(lv, ensure_ascii=False, indent=2)
    inj = emb_text.strip()
    inj_norm = re.sub(r"\s+", "", inj)
    A(inj_norm == re.sub(r"\s+", "", canon), "内嵌 LEVELS 文本与 levels.json 规范化文本不一致")

    for idx, L in enumerate(lv):
        lid, n = L["id"], L["size"]
        tag = "第%d关(%s)" % (lid, L["theme"]["name"])
        A(lid == idx + 1, "%s id 与序号不符" % tag)
        mine = {r * n + c for r, c in L["mines"]}
        A(len(mine) == len(L["mines"]), "%s mines 有重复/越界" % tag)
        A(all(0 <= r < n and 0 <= c < n for r, c in L["mines"]), "%s mines 越界" % tag)

        # A2 数织线索
        rr = [runs_of(mine, n, True, k) for k in range(n)]
        cc = [runs_of(mine, n, False, k) for k in range(n)]
        A(rr == [list(x) for x in L["rowRuns"]], "%s rowRuns 与 mines 不一致" % tag)
        A(cc == [list(x) for x in L["colRuns"]], "%s colRuns 与 mines 不一致" % tag)

        # A3 noise ⊆ mines 且与星座星不重叠
        noise = {r * n + c for r, c in L["noise"]}
        A(noise <= mine, "%s noise 不在 mines 内" % tag)
        stars = L["theme"]["stars"]
        src = {(s["rc"][0] * n + s["rc"][1]) for s in stars}
        A(not (noise & src), "%s noise 与星座星重叠" % tag)
        A(src <= mine, "%s 星座星不在 mines 内" % tag)
        A(len(src) == len(stars), "%s 星座星坐标重复" % tag)
        A(len({s["name"] for s in stars}) == len(stars), "%s 星座星名重复" % tag)
        for ln in L["theme"]["lines"]:
            A(len(ln) == 2 and 0 <= ln[0] < len(stars) and 0 <= ln[1] < len(stars), "%s lines 下标越界" % tag)
            A(ln[0] != ln[1], "%s lines 自环" % tag)

        # A4 opening
        orow, ocol = L["opening"]
        oi = orow * n + ocol
        counts = [sum(1 for j in nbrs_of(i, n) if j in mine) for i in range(n * n)]
        A(oi not in mine, "%s opening 是雷" % tag)
        A(counts[oi] == 0, "%s opening 邻域雷数=%d != 0" % (tag, counts[oi]))
        rev = flood_reveal(oi, n, mine, counts)
        open_ratio = len(rev) / (n * n) * 100.0

        # A5 showRuns
        A(L["showRuns"] == (lid != 1), "%s showRuns=%s 不符（仅第1关 false）" % (tag, L["showRuns"]))

        # A7 星座唯一
        tid = L["theme"]["id"]
        if tid in seen_ids: fails.append("星座 id 重复：%s（第%d/第%d关）" % (tid, seen_ids[tid], lid))
        seen_ids[tid] = lid
        tn = L["theme"]["name"]
        if tn in seen_names: fails.append("星座名重复：%s（第%d/第%d关）" % (tn, seen_names[tn], lid))
        seen_names[tn] = lid

        # C 指标
        iz = counts.count(0)
        iso = sum(1 for m in mine if not (set(nbrs_of(m, n)) & mine))
        rows.append(dict(lid=lid, name=tn, n=n, mines=len(mine),
                         dens=len(mine) / (n * n) * 100.0, openn=len(rev),
                         open_ratio=open_ratio, zero=iz, zero_ratio=iz / (n * n) * 100.0,
                         iso=iso, stars=len(stars), noise=len(noise), lines=len(L["theme"]["lines"])))

    # C 阈值（复核口径：展开 ≤38%、0 格 ≤40%、孤立雷 ≤2、尺寸 ≤11）
    over = []
    for r in rows:
        if r["n"] > 11: over.append("第%d关 尺寸 %d>11" % (r["lid"], r["n"]))
        if r["open_ratio"] > 38.0: over.append("第%d关 展开 %.1f%%>38%%" % (r["lid"], r["open_ratio"]))
        if r["zero_ratio"] > 40.0: over.append("第%d关 0格 %.1f%%>40%%" % (r["lid"], r["zero_ratio"]))
        if r["iso"] > 2: over.append("第%d关 孤立雷 %d>2" % (r["lid"], r["iso"]))
    # 备选口径（分母=安全格）用于确认口径不改变判定
    alt = []
    for r, L in zip(rows, lv):
        safe = r["n"] * r["n"] - r["mines"]
        if r["openn"] / safe > 0.38: alt.append("第%d关 展开/安全格 %.1f%%>38%%" % (r["lid"], r["openn"] / safe * 100))
        if r["zero"] / safe > 0.40: alt.append("第%d关 0格/安全格 %.1f%%>40%%" % (r["lid"], r["zero"] / safe * 100))

    out = dict(A_fail=fails, C_over=over, C_over_alt_denom=alt, rows=rows,
               sizes=sorted({r["n"] for r in rows}),
               sky_len=len(sky), sky_levels=[s.get("level") for s in sky],
               sky_ids=[s.get("id") for s in sky], levels_sha=None)
    print("=== A 数据自洽 ===")
    print("A 失败项:", len(fails))
    for f in fails: print("  -", f)
    print("=== C 难度指标（阈值 展开<=38% 0格<=40% 孤立雷<=2 尺寸<=11）===")
    print("超出项:", len(over))
    for f in over: print("  -", f)
    print("备选分母(安全格)超出项:", len(alt))
    for f in alt: print("  -", f)
    print("尺寸集合:", out["sizes"], " SKY 条目:", len(sky))
    print("SKY level 覆盖:", sorted(set(x for x in out["sky_levels"] if x is not None)), "唯一:", len(set(out["sky_levels"])) == len(out["sky_levels"]))
    print()
    print("%-3s %-8s %-6s %-4s %-7s %-9s %-9s %-4s %-4s %-4s" % (
        "关", "星座", "盘面", "雷", "密度%", "展开格", "展开占比%", "0格", "0格%", "孤立"))
    for r in rows:
        print("%-3d %-8s %-6s %-4d %-7.1f %-9d %-9.1f %-4d %-4.1f %-4d" % (
            r["lid"], r["name"], "%dx%d" % (r["n"], r["n"]), r["mines"], r["dens"],
            r["openn"], r["open_ratio"], r["zero"], r["zero_ratio"], r["iso"]))
    json.dump(out, open(os.path.join(ROOT, "verification", "v13_out_a.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
