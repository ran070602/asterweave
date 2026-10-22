#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把两份交付文档里的「关卡表」按 tools/levels.json 的真实数据重写。

用法：python tools/sync_docs_tables.py [--dry]

会做的事：
  1. 用求解器算出每关的「探格次数 / 数织线索贡献 / 是否必须用星图线索」；
  2. 按固定列格式生成 23（或任意关数）行表格；
  3. 替换《设计思路文档》与《迭代优化过程文档》里已有的关卡表；
  4. 把两份文档里的「N 关」数字改成实际关数（只改已知的固定搭配，避免误伤）。

为什么需要它：关卡一扩张，两份文档的表格就会和 levels.json 脱节；手工改容易漏行/错列。
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
rows_design = "\n".join(rows_design) + "\n"
rows_iter = "\n".join(rows_iter) + "\n"

# 匹配「从第 1 行南十字座到最后一行的表格块」（任意行数）
pat = re.compile(r"\| 1 \| 南十字座[^\n]*\n(?:\| \d+ \|[^\n]*\n)*?\| \d+ \|[^\n]*\n")

targets = [
    ("冉政-设计思路文档.md", rows_design),
    ("冉政-迭代优化过程文档.md", rows_iter),
]
changed = 0
for rel, rows in targets:
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        print(f"跳过（不存在）：{rel}"); continue
    s = open(p, encoding="utf-8").read()
    s2, k = pat.subn(rows, s, count=1)
    if k == 0:
        print(f"!! {rel}：没找到关卡表（格式变了？）"); continue
    # 关数文案同步
    s2 = re.sub(r"\d+ 关（目标 50 关）", f"{N} 关（目标 50 关）", s2)
    s2 = re.sub(r"\*\*20 关", f"**{N} 关", s2)
    s2 = re.sub(r"\*\*23 关", f"**{N} 关", s2)
    if DRY:
        print(f"[dry] {rel}：将替换 {len(rows.splitlines())} 行表格")
    else:
        open(p, "w", encoding="utf-8").write(s2)
        print(f"✅ {rel}：表格已同步为 {len(rows.splitlines())} 行")
    changed += 1

print(f"\n完成：{changed} 份文档{'（dry 模式未写入）' if DRY else '已更新'}；当前 {N} 关")