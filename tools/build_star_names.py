"""把 tools/star_name_needed.json 里已补的专名汇总成注入用的小表。

用法：python tools/build_star_names.py
产物：tools/star_proper_names.json  {"<关卡号>|<拜耳编号>": "专名", ...}
说明：标注时优先用专名（如 Tejat Posterior），没有专名的暗星继续用编号（如 Mu Gem）。
     tools/star_proper_overrides.json 为人工纠正表，优先级最高；值为 null 表示退回编号。
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "tools", "star_name_needed.json")
OVR = os.path.join(ROOT, "tools", "star_proper_overrides.json")
OUT = os.path.join(ROOT, "tools", "star_proper_names.json")


def load_overrides():
    """人工纠正表：非 "_" 开头的键生效；null = 退回编号。"""
    if not os.path.exists(OVR):
        return {}
    try:
        raw = json.load(open(OVR, encoding="utf-8"))
    except Exception as e:
        print("!! 专名纠正表解析失败（忽略）：%s" % e)
        return {}
    return {k: v for k, v in raw.items() if not k.startswith("_")}


def main():
    if not os.path.exists(SRC):
        print("!! 缺少 tools/star_name_needed.json，写入空表")
        json.dump({}, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
        return
    rows = json.load(open(SRC, encoding="utf-8"))
    out = {}
    for r in rows:
        p = (r.get("proper") or "").strip()
        if not p:
            continue
        key = "%s|%s" % (r.get("level"), r.get("en"))
        out[key] = p

    ovr = load_overrides()
    fixed = dropped = 0
    for k, v in ovr.items():
        if v is None:
            if out.pop(k, None) is not None:
                dropped += 1
        elif str(v).strip() and out.get(k) != v:
            out[k] = str(v).strip()
            fixed += 1

    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    total = len(rows)
    filled = len(out)
    print("专名表：%d / %d 条已补（其余暗星保留编号）" % (filled, total))
    if fixed or dropped:
        print("   人工纠正：改写 %d 条、退回编号 %d 条（见 tools/star_proper_overrides.json）" % (fixed, dropped))
    if filled == 0:
        print("   （暂无专名：海报仍用编号，如 Mu Gem；补齐后自动升级）")


if __name__ == "__main__":
    main()
