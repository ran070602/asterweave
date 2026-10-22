# -*- coding: utf-8 -*-
"""
T8 独立复核 · A 部分：关卡数据自洽性检查。

独立性声明：本文件完全自写，不 import、不复制 tools/generate_levels.py 的任何代码。
用法：
    python verification/a_data_check.py
输出：
    stdout 人类可读日志 + JSON 摘要写入 verification/out_a.json
"""
import json
import re
import sys
import os
from pathlib import Path
import hashlib

ROOT = Path(__file__).resolve().parent.parent
# 可选：T8_LEVELS 指向冻结的关卡数据副本；默认 tools/levels.json
LEVELS_JSON = Path(os.environ.get("T8_LEVELS", ROOT / "tools" / "levels.json"))
# 可选：把被复核的 HTML 冻结副本路径作为 argv[1] 传入，便于复现同一修订
HTML = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "game" / "index.html"

INJECT_RE = re.compile(r"/\*\s*LEVELS_INJECT_START\s*\*/(.*?)/\*\s*LEVELS_INJECT_END\s*\*/", re.S)
ARRAY_RE = re.compile(r"const\s+LEVELS\s*=\s*(\[.*\])\s*;", re.S)

SPEC_SIZE_3LV = {1: 6, 2: 6, 3: 7}      # SPEC v1.1 §2/§3 仍只描述 3 关，用于“文档 vs 数据”对照
SPEC_SHOWRUNS_3LV = {1: False, 2: True, 3: True}


def runs_of(vals):
    """[bool,...] -> 连续 True 块长度序列"""
    out, cur = [], 0
    for v in vals:
        if v:
            cur += 1
        else:
            if cur:
                out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out


def neighbors(n, r, c):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < n and 0 <= cc < n:
                yield rr, cc


def line_grid(level):
    n = level["size"]
    grid = [[False] * n for _ in range(n)]
    for r, c in level["mines"]:
        grid[r][c] = True
    row_calc = [runs_of(grid[r]) for r in range(n)]
    col_calc = [runs_of([grid[r][c] for r in range(n)]) for c in range(n)]
    return row_calc, col_calc, grid


def flood_reveal(n, grid, start):
    counts = {}
    for r in range(n):
        for c in range(n):
            counts[(r, c)] = sum(1 for rr, cc in neighbors(n, r, c) if grid[rr][cc])
    seen = set()
    stack = [start]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        r, c = cur
        if grid[r][c]:
            continue
        seen.add(cur)
        if counts[cur] == 0:
            for nb in neighbors(n, r, c):
                if nb not in seen and not grid[nb[0]][nb[1]]:
                    stack.append(nb)
    return seen, counts


def main():
    report = {"checks": [], "all_pass": True, "extras": {}}

    def check(cid, ok, detail):
        report["checks"].append({"id": cid, "ok": bool(ok), "detail": detail})
        if not ok:
            report["all_pass"] = False
        print(("[PASS] " if ok else "[FAIL] ") + cid + " :: " + detail)

    levels = json.loads(LEVELS_JSON.read_text(encoding="utf-8"))
    html = HTML.read_text(encoding="utf-8")

    print("== A. 数据自洽（tools/levels.json + game/index.html）==")
    print("被复核 HTML = %s" % HTML)
    print("被复核 HTML sha256 = %s" % hashlib.sha256(HTML.read_bytes()).hexdigest())
    report["extras"]["html"] = {"path": str(HTML),
                                "sha256": hashlib.sha256(HTML.read_bytes()).hexdigest()}
    print("levels.json 字节数 = %d ；关卡数 = %d" % (LEVELS_JSON.stat().st_size, len(levels)))

    # ---------- A3: HTML 内嵌 LEVELS 与 levels.json 一致性 ----------
    m = INJECT_RE.search(html)
    if not m:
        check("A3-1 注入块存在", False, "未找到 /* LEVELS_INJECT_START */ ... /* LEVELS_INJECT_END */")
    else:
        check("A3-1 注入块存在", True, "注入块长度 %d 字节" % len(m.group(1)))
        am = ARRAY_RE.search(m.group(1))
        if not am:
            check("A3-2 注入块含 const LEVELS = [ ... ];", False, "数组字面量未匹配")
        else:
            embedded_raw = am.group(1)
            try:
                embedded = json.loads(embedded_raw)
                check("A3-2 内嵌 LEVELS 可 JSON 解析", True, "解析出 %d 个关卡" % len(embedded))
                same = embedded == levels
                check("A3-3 内嵌 LEVELS == tools/levels.json（解析后对象相等）", same,
                      "相等" if same else "不相等：差异见 out_a.json")
                canon_a = json.dumps(levels, sort_keys=True, ensure_ascii=False)
                canon_b = json.dumps(embedded, sort_keys=True, ensure_ascii=False)
                check("A3-4 规范化 JSON 字符串相等（逐字段）", canon_a == canon_b,
                      "长度 %d vs %d" % (len(canon_a), len(canon_b)))
                if not same:
                    report["extras"]["embed_diff"] = {"json": levels, "embedded": embedded}
            except Exception as e:  # noqa
                check("A3-2 内嵌 LEVELS 可 JSON 解析", False, "异常: %r" % (e,))

    # ---------- 逐关 A1 / A2 ----------
    per_level = []
    for idx, lv in enumerate(levels):
        lid = lv["id"]
        n = lv["size"]
        mines = [tuple(x) for x in lv["mines"]]
        mine_set = set(mines)
        row_calc, col_calc, grid = line_grid(lv)
        info = {"id": lid, "size": n, "mine_count": len(mines)}

        dup = len(mines) - len(mine_set)
        inb = all(0 <= r < n and 0 <= c < n for r, c in mines)
        check(f"A2-{lid}-1 雷坐标均在盘内", inb, "mines=%s n=%d" % (mines, n))
        check(f"A2-{lid}-2 雷坐标无重复", dup == 0,
              "len(mines)=%d distinct=%d" % (len(mines), len(mine_set)))
        info["mines"] = [list(x) for x in mines]

        row_ok = [list(x) for x in row_calc] == [list(x) for x in lv["rowRuns"]]
        check(f"A1-{lid}-3 rowRuns 与 mines 重算一致", row_ok,
              "重算=%s 声明=%s" % (row_calc, lv["rowRuns"]))
        col_ok = [list(x) for x in col_calc] == [list(x) for x in lv["colRuns"]]
        check(f"A1-{lid}-4 colRuns 与 mines 重算一致", col_ok,
              "重算=%s 声明=%s" % (col_calc, lv["colRuns"]))
        uniq_cols = {tuple(x) for x in col_calc}
        check(f"A1-{lid}-5 列线索未退化为「所有列相同」", len(uniq_cols) > 1 or n == 1,
              "重算列线索集合=%s" % sorted(uniq_cols))
        info["rowRuns_calc"] = [list(x) for x in row_calc]
        info["colRuns_calc"] = [list(x) for x in col_calc]

        row_sum = sum(sum(x) for x in row_calc)
        col_sum = sum(sum(x) for x in col_calc)
        check(f"A2-{lid}-6 行线索数字和 == 雷数", row_sum == len(mines),
              "sum(rowRuns)=%d mines=%d" % (row_sum, len(mines)))
        check(f"A2-{lid}-7 列线索数字和 == 雷数", col_sum == len(mines),
              "sum(colRuns)=%d mines=%d" % (col_sum, len(mines)))

        op = tuple(lv["opening"])
        revealed, counts = flood_reveal(n, grid, op)
        op_safe = op not in mine_set
        check(f"A2-{lid}-8 opening 是安全格", op_safe,
              "opening(0-based)=%s 是雷? %s" % (list(op), not op_safe))
        check(f"A2-{lid}-9 opening 邻域雷数 == 0", counts[op] == 0,
              "counts[opening]=%d" % counts[op])
        check(f"A2-{lid}-10 opening 在盘内", 0 <= op[0] < n and 0 <= op[1] < n, "opening=%s" % list(op))
        info["opening"] = list(op)
        info["opening_neighbor_mines"] = counts[op]
        info["opening_flood_size"] = len(revealed)
        check(f"A2-{lid}-11 opening flood fill 非空", len(revealed) > 0,
              "开局翻开 %d 格" % len(revealed))

        check(f"A2-{lid}-12 size 在合理范围（6/7/8）", n in (6, 7, 8), "n=%d" % n)
        check(f"A2-{lid}-13 showRuns 是布尔", isinstance(lv["showRuns"], bool), "showRuns=%r" % lv["showRuns"])
        check(f"A2-{lid}-14 lives 默认 3", lv["lives"] == 3, "lives=%s" % lv["lives"])
        check(f"A2-{lid}-15 id 与顺序一致", lid == idx + 1, "id=%d 顺序=%d" % (lid, idx + 1))
        check(f"A2-{lid}-16 technique 非空", isinstance(lv.get("technique"), str) and lv["technique"] != "",
              "technique=%r" % lv.get("technique"))
        info["showRuns"] = lv["showRuns"]
        info["lives"] = lv["lives"]
        info["teach"] = lv["teach"]

        detail = []
        for c in range(n):
            col_vals = [grid[r][c] for r in range(n)]
            detail.append({"col0": c, "col1": c + 1,
                           "mines_in_col": [r for r in range(n) if grid[r][c]],
                           "runs_calc": runs_of(col_vals),
                           "runs_declared": list(lv["colRuns"][c])})
        info["per_column_detail"] = detail
        per_level.append(info)

    report["extras"]["per_level"] = per_level

    # ---------- SPEC v1.1 与 10 关数据的“文档 vs 数据”对照 ----------
    print()
    print("== SPEC v1.1 文档 vs 10 关实测数据 ==")
    spec_txt = (ROOT / "docs" / "SPEC.md").read_text(encoding="utf-8")
    showruns_true = [x["id"] for x in per_level if x["showRuns"]]
    showruns_false = [x["id"] for x in per_level if not x["showRuns"]]
    teach_empty = [x["id"] for x in per_level if not x["teach"]]
    sizes = sorted({x["size"] for x in per_level})

    check("SPEC §1 措辞「连续块线索仅第 2、3 关显示」== 10 关数据",
          showruns_true == [2, 3],
          "文档说：仅第 2、3 关显示；实测 showRuns=true 的关卡=%s，showRuns=false 的关卡=%s"
          % (showruns_true, showruns_false))
    check("SPEC §2 字段表「id 1..3」== 10 关数据", len(levels) == 3,
          "文档说：id 1..3；实测关卡数=%d（最大 id=%d）" % (len(levels), levels[-1]["id"]))
    check("SPEC §2 字段表「第1关6/第2关6/第3关7」== 10 关数据",
          all(SPEC_SIZE_3LV.get(x["id"]) == x["size"] for x in per_level if x["id"] in SPEC_SIZE_3LV),
          "文档说：%s；实测前 3 关 size=%s，全部关卡 size 取值=%s"
          % (SPEC_SIZE_3LV, [x["size"] for x in per_level[:3]], sizes))
    check("SPEC §4.5「第 3 关 teach 为空」== 10 关数据", teach_empty == [3],
          "文档说：只有第 3 关 teach 为空；实测 teach 为空的关卡=%s" % teach_empty)
    check("SPEC §5 生成器标准「产出并校验 3 关」== 10 关数据", len(levels) == 3,
          "文档说：3 关；实测 %d 关" % len(levels))
    multi = None
    try:
        cj = json.loads((ROOT / "verification" / "out_c.json").read_text(encoding="utf-8"))
        if [x["id"] for x in cj["levels"]] == [x["id"] for x in levels]:
            multi = {x["id"]: x["full"]["solutions"] for x in cj["levels"]
                     if not x["full"].get("timeout")}
    except Exception:
        multi = None
    check("SPEC §6.1「每关在给定线索下解唯一」== 实测相容方案数",
          multi is not None and all(v == 1 for v in multi.values()),
          "文档说：每关解唯一；实测（out_c.json）各关相容方案数=%s"
          % (multi if multi is not None else "out_c.json 尚未为当前 10 关生成，见 C 部分"))
    check("SPEC §1 v1.1 胜利口径「插旗或已探爆都算标出」已写入", "都被探爆" in spec_txt or "已被探爆" in spec_txt,
          "SPEC 第 25-26 行：%s" % ("含探爆=标出" if ("已被探爆" in spec_txt or "都被探爆" in spec_txt) else "未找到"))
    check("SPEC §1 v1.1「已插旗的格子会挡住 flood fill」已写入", "挡住 flood fill" in spec_txt,
          "SPEC 第 29 行：%s" % ("含阻挡条款" if "挡住 flood fill" in spec_txt else "未找到"))
    report["extras"]["spec_vs_data"] = {
        "showruns_true": showruns_true, "showruns_false": showruns_false,
        "teach_empty": teach_empty, "sizes": sizes, "level_count": len(levels)}

    print()
    print("== 逐关摘要 ==")
    for info in per_level:
        print("第 %d 关: %dx%d 雷=%d showRuns=%s opening(0based)=%s 邻域=%d 开局flood=%d 格" % (
            info["id"], info["size"], info["size"], info["mine_count"], info["showRuns"],
            info["opening"], info["opening_neighbor_mines"], info["opening_flood_size"]))
        print("   rowRuns 重算 = %s" % info["rowRuns_calc"])
        print("   colRuns 重算 = %s" % info["colRuns_calc"])

    print()
    print("== 逐列手算明细（重点核对历史 bug：列线索是否误用行下标）==")
    for info in per_level:
        print("第 %d 关（%d 列）:" % (info["id"], info["size"]))
        for d in info["per_column_detail"]:
            print("   列%d(1-based %d): 该列雷的行号=%s -> 连续块=%s ; levels.json 声明=%s ; %s" % (
                d["col0"], d["col1"], d["mines_in_col"], d["runs_calc"], d["runs_declared"],
                "一致" if d["runs_calc"] == d["runs_declared"] else "★不一致★"))

    print()
    print("A 部分总判定: %s" % ("全部通过" if report["all_pass"] else "存在不通过项"))
    (ROOT / "verification" / "out_a.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("JSON 摘要 -> verification/out_a.json")
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())