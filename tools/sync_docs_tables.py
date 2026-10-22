#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把两份交付文档里的「关卡表」按 tools/levels.json 的真实数据重写（幂等）。

用法：python tools/sync_docs_tables.py [--dry]

做法：在文档里找出「最长的、以 | 数字 | 开头的连续表格块」当作关卡表，
      与按 levels.json + 求解器生成的内容逐行比对；一致就跳过，不一致才整块替换。
（旧版本用固定正则匹配首行/末行，遇到文档里有多张表时会重复插入，已修正。）
"""
import importlib.util, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRY = "--dry" in sys.argv

sp = importlib.util.spec_from_file_location("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
gl = importlib.util.module_from_spec(sp); sp.loader.exec_module(gl)

lv = json.load(open(os.path.join(ROOT, "tools", "levels.json"), encoding="utf-8"))
N = len(lv)

rows_design, rows_iter = [], []
for x in lv:
    ok, _p, info = gl.check_level(x, static=False)
    if not ok:
        print(f"!! 第 {x['id']} 关不可解，先修关卡再同步文档"); sys.exit(2)
    must = not info["nb_only_ok"]
    head = (f"| {x['id']} | {x['theme']['name']} | {x['size']}×{x['size']} | {len(x['theme']['stars'])} | "
            f"{len(x.get('noise', []))} | {len(x['mines'])} | {info['reveal_actions']} | {info['runs_cells']} | ")
    if not x.get("showRuns"):
        rows_design.append(head + "是（本关不显示数织） |")
        rows_iter.append(head + "—（第 1 关无数织） |")
    else:
        rows_design.append(head + ("否（要用星图线索） |" if must else "是 |"))
        rows_iter.append(head + ("是 |" if must else "否（数字即可解） |"))


def find_level_table(lines):
    """返回 (start, end) —— 最长的连续「| 数字 |」表格块"""
    best, i = None, 0
    while i < len(lines):
        if re.match(r"^\| \d+ \| ", lines[i]):
            j = i
            while j < len(lines) and re.match(r"^\| \d+ \| ", lines[j]):
                j += 1
            if best is None or (j - i) > (best[1] - best[0]):
                best = (i, j)
            i = j
        else:
            i += 1
    return best


changed = 0
for rel, rows in (("冉政-设计思路文档.md", rows_design),
                  ("冉政-迭代优化过程文档.md", rows_iter)):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print(f"跳过（不存在）：{rel}"); continue
    lines = open(p, encoding="utf-8").read().split("\n")
    span = find_level_table(lines)
    if not span:
        print(f"!! {rel}：找不到关卡表"); continue
    s, e = span
    cur = lines[s:e]
    if cur == rows:
        print(f"= {rel}：关卡表已是最新（{len(cur)} 行），无需修改")
        continue
    print(f"~ {rel}：将把 {len(cur)} 行表格替换为 {len(rows)} 行")
    if not DRY:
        lines[s:e] = rows
        open(p, "w", encoding="utf-8").write("\n".join(lines))
    changed += 1

print(f"\n完成：{changed} 份文档{'待更新（dry 未写入）' if DRY else '已更新'}；当前 {N} 关")