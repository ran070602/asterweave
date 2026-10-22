# -*- coding: utf-8 -*-
"""
T8 独立复核 · B 附加：把 tools/report.md 自述的推理序列/统计表与独立求解结果逐条对照。

用法：
    python verification/b2_compare_report.py
输出：
    stdout 对照表 + verification/out_b2.json
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = Path(os.environ.get("T8_REPORT", ROOT / "tools" / "report.md"))
OUT_B = ROOT / "verification" / "out_b.json"

STEP_RE = re.compile(r"^\s*-\s*(\d+)\.\s*\[(邻域|连续块)\]\s*(判定雷|探开安全格)\s*\((\d+),(\d+)\)\s*$")
SEC_RE = re.compile(r"^###\s*第\s*(\d+)\s*关")
NUM_RE = re.compile(r"生成尝试\s*\*\*(\d+)\*\*\s*次，接受\s*\*\*(\d+)\*\*\s*次")
FLOOD_RE = re.compile(r"开局 flood fill 自动翻开\s*\*\*(\d+)\*\*\s*格")
OPEN_RE = re.compile(r"opening\s*=\s*\*\*\((\d+),(\d+)\)\*\*")
TABLE_ROW = re.compile(r"^\|\s*(\d)\s*\|")


def parse_report(text):
    sections = {}
    cur = None
    for line in text.splitlines():
        m = SEC_RE.match(line)
        if m:
            cur = int(m.group(1))
            sections[cur] = {"steps": [], "raw": []}
            continue
        if cur is None:
            continue
        sections[cur]["raw"].append(line)
        m = STEP_RE.match(line)
        if m:
            sections[cur]["steps"].append({
                "n": int(m.group(1)), "rule": m.group(2), "kind": m.group(3),
                "r": int(m.group(4)), "c": int(m.group(5))})
    for lid, sec in sections.items():
        body = "\n".join(sec["raw"])
        m = NUM_RE.search(body)
        sec["gen_attempts"] = int(m.group(1)) if m else None
        sec["gen_accepted"] = int(m.group(2)) if m else None
        m = FLOOD_RE.search(body)
        sec["flood_size"] = int(m.group(1)) if m else None
        m = OPEN_RE.search(body)
        sec["opening_1based"] = [int(m.group(1)), int(m.group(2))] if m else None
        m = re.search(r"求解器模拟结果：邻域判定\s*\*\*(\d+)\*\*\s*格，连续块判定\s*\*\*(\d+)\*\*\s*格，玩家手动探格\s*\*\*(\d+)\*\*\s*次", body)
        if m:
            sec["tbl"] = {"a": int(m.group(1)), "b": int(m.group(2)), "digs": int(m.group(3))}
        m = re.search(r"解数：\*\*([^*]+)\*\*", body)
        sec["static_solutions"] = m.group(1) if m else None
        m = re.search(r"搜索节点\s*(\d+)", body)
        sec["static_nodes"] = int(m.group(1)) if m else None
    return sections


def parse_main_table(text):
    rows = {}
    for line in text.splitlines():
        if not TABLE_ROW.match(line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        # | 关 | 尺寸 | 雷数 | 显示连续块 | 只用邻域推理能通关？ | 需要连续块线索？ | 连续块判定格数 | 邻域判定格数 | 探格次数 | 静态线索解数 | 结论 |
        if len(cells) >= 10 and cells[0].isdigit():
            rows[int(cells[0])] = cells
    return rows


def main():
    rep = parse_report(REPORT.read_text(encoding="utf-8"))
    table = parse_main_table(REPORT.read_text(encoding="utf-8"))
    mine = {r["id"]: r for r in json.loads(OUT_B.read_text(encoding="utf-8"))["levels"]}
    a = json.loads((ROOT / "verification" / "out_a.json").read_text(encoding="utf-8"))
    a_flood = {x["id"]: x["opening_flood_size"] for x in a["extras"]["per_level"]}
    a_open = {x["id"]: [x["opening"][0] + 1, x["opening"][1] + 1] for x in a["extras"]["per_level"]}

    out = {"levels": [], "diffs": []}
    for lid in sorted(rep.keys()):
        if lid not in mine:
            continue
        sec = rep[lid]
        m = mine[lid]
        aplus = m["a_plus_b"]
        mine_steps = [{"rule": ("邻域" if s["rule"] == "a" else "连续块"),
                       "kind": ("判定雷" if s["kind"] == "mine" else "探开安全格"),
                       "r": s["rc"][0], "c": s["rc"][1]} for s in aplus["steps_seq"]]
        rep_steps = sec["steps"]
        mine_set = sorted((s["kind"], s["r"], s["c"]) for s in mine_steps)
        rep_set = sorted((s["kind"], s["r"], s["c"]) for s in rep_steps)
        same_steps = mine_set == rep_set
        mine_by_rule = {"邻域": sum(1 for s in mine_steps if s["rule"] == "邻域"),
                        "连续块": sum(1 for s in mine_steps if s["rule"] == "连续块")}
        rep_by_rule = {"邻域": sum(1 for s in rep_steps if s["rule"] == "邻域"),
                       "连续块": sum(1 for s in rep_steps if s["rule"] == "连续块")}
        mine_digs = sum(1 for s in mine_steps if s["kind"] == "探开安全格")
        print("=" * 78)
        print("第 %d 关" % lid)
        print("  报告步骤数=%d ｜ 独立求解步骤数=%d ｜ (动作,坐标) 集合完全相同=%s" % (
            len(rep_steps), len(mine_steps), same_steps))
        print("  报告 邻域/连续块 = %d/%d ｜ 独立 邻域/连续块 = %d/%d ｜ %s" % (
            rep_by_rule["邻域"], rep_by_rule["连续块"], mine_by_rule["邻域"], mine_by_rule["连续块"],
            "一致" if (rep_by_rule == mine_by_rule) else "★不一致（归属类别不同，步数总数相同）★"))
        print("  报告 探格次数=%s ｜ 独立 显式探格=%d ｜ %s" % (
            sec.get("tbl", {}).get("digs"), mine_digs,
            "一致" if sec.get("tbl", {}).get("digs") == mine_digs else "★不一致★"))
        print("  报告 开局 flood=%s ｜ 独立(A部分)=%s ｜ 报告 opening(1based)=%s ｜ 数据 opening(1based)=%s" % (
            sec["flood_size"], a_flood[lid], sec["opening_1based"], a_open[lid]))
        print("  报告 静态解数=%s ｜ 独立(out_c.json)=见 C 部分" % sec["static_solutions"])
        print("  报告 生成尝试=%s 接受=%s（自述，未独立复现）" % (sec["gen_attempts"], sec["gen_accepted"]))
        if not same_steps:
            only_rep = [x for x in rep_set if x not in mine_set]
            only_mine = [x for x in mine_set if x not in rep_set]
            print("    仅在报告中: %s" % only_rep[:10])
            print("    仅在独立结果中: %s" % only_mine[:10])
            out["diffs"].append({"level": lid, "only_report": only_rep, "only_independent": only_mine})
        out["levels"].append({
            "id": lid, "report_steps": len(rep_steps), "independent_steps": len(mine_steps),
            "same_action_set": same_steps,
            "report_by_rule": rep_by_rule, "independent_by_rule": mine_by_rule,
            "report_digs": sec.get("tbl", {}).get("digs"), "independent_digs": mine_digs,
            "report_flood_size": sec["flood_size"], "report_static_solutions": sec["static_solutions"],
            "report_static_nodes": sec["static_nodes"],
            "report_gen_attempts": sec["gen_attempts"], "report_gen_accepted": sec["gen_accepted"],
        })

    print()
    print("== 报告 §0 验收表 vs 独立实测 ==")
    for lid in sorted(table.keys()):
        cells = table.get(lid)
        m = mine.get(lid)
        if not cells or not m:
            continue
        print("第 %d 关: 表|雷数=%s 显示连续块=%s 只用邻域能通关=%s 需要连续块=%s 连续块判定=%s 邻域判定=%s 探格=%s 静态解数=%s" % (
            lid, cells[2], cells[3], cells[4], cells[5], cells[6], cells[7], cells[8], cells[9]))
        print("        实测|雷数=%d showRuns=%s a_only通关=%s 需b=%s b步数=%d a步数=%d 显式探格=%d" % (
            len(m["mines_true"]), m.get("showRuns", "?"), m["a_only"]["complete"],
            m["verdict"]["b_needed"], m["a_plus_b"]["steps_b"], m["a_plus_b"]["steps_a"],
            m["a_plus_b"]["explicit_reveals"]))
    out["main_table"] = {str(k): v for k, v in table.items()}
    (ROOT / "verification" / "out_b2.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("JSON -> verification/out_b2.json")


if __name__ == "__main__":
    main()