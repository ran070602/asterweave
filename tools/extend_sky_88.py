#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图鉴 88 星表扩展：把 tools/constellations88.json 里新增的 38 个星座并入 build_sky.py 的 RAW 与 CN_NAMES，
并把 38 条科普写入 fit_constellation_levels.py 的 FACTS；同时修正两处已核实的旧数据错误。

用法：python tools/extend_sky_88.py [--write]
不加 --write 只做预演（打印将要写入的内容摘要与差异）。
注意：写入后请**在 levels.json 合并完 51–88 关之后**再跑 `python tools/build_sky.py` 重建 sky.json。
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from star_proper_zh import PROPER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
C88 = os.path.join(ROOT, "tools", "constellations88.json")
SKY = os.path.join(ROOT, "tools", "build_sky.py")
FIT = os.path.join(ROOT, "tools", "fit_constellation_levels.py")
LEVELS = os.path.join(ROOT, "tools", "levels.json")

# 已核实的旧数据修正（来源：HYG v41 + d3-celestial 边界实算；详见 HANDOFF）
FIXES = {
    # 巨爵座最亮星应为 δ Crt（3.56），原 RAW 记的是 α Crt（Alkes，4.08，实为第二亮）
    "crater": {"brightest": ("巨爵δ", "Delta Crt", 3.56)},
    # 大熊座邻居漏了狮子座（边界数据证明二者相邻；狮子座那侧已含大熊座）
    "ursa-major": {"add_neighbor": "Leo"},
}


def load_c88():
    data = json.load(io.open(C88, encoding="utf-8"))
    return {x["id"]: x for x in data}


def tuple_line(x, level=0):
    neigh = ", ".join('"%s"' % n for n in x["neighbours"])
    b = dict(x["brightest"])
    b["zh"] = PROPER.get(b["en"], b["zh"])      # 知名星用传统中文名
    return ('    ("%s", "%s", "%s", "%s", "%s", %d, %s, %s, %d, "%s", "%s", %s,\n     [%s]),'
            % (x["id"], x["zh"], x["en"], x["en"], x["desig"], level,
               round(x["raH"], 2), round(x["decDeg"], 1), x["rank"],
               b["zh"], b["en"], b["mag"], neigh))


def main():
    write = "--write" in sys.argv
    c88 = load_c88()
    src = io.open(SKY, encoding="utf-8").read()
    fit = io.open(FIT, encoding="utf-8").read()
    lv = json.load(io.open(LEVELS, encoding="utf-8"))

    have = re.findall(r'^\s*\("([a-z0-9-]+)",', src, re.M)
    have_set = set(have)
    print("build_sky.py RAW 现有 %d 条" % len(have_set))
    missing = [x["id"] for x in json.load(io.open(C88, encoding="utf-8")) if x["id"] not in have_set]
    print("需新增 %d 条: %s" % (len(missing), ", ".join(missing)))

    in_levels = {((x.get("theme") or {}).get("id")) for x in lv}
    print("levels.json 现有星座 %d 个；新增里已在关卡中的: %s"
          % (len(in_levels), ", ".join([m for m in missing if m in in_levels]) or "（无，符合预期：51–88 尚未合并）"))

    add_lines = "\n".join(tuple_line(c88[m]) for m in missing)
    # 追加到 RAW 列表末尾（在最后一个元素的 ")]" 之后、"]" 之前）
    m = re.search(r"RAW\s*=\s*\[", src)
    end = src.find("\n]", m.start())
    if end < 0:
        print("FAIL 找不到 RAW 结束位置"); return
    print("\n将要追加的 RAW 片段（前 3 行）:")
    print("\n".join(add_lines.split("\n")[:3]))

    # CN_NAMES：补全 88 个拉丁名 → 中文
    cn_missing = [x for x in c88.values() if ('"%s":' % x["en"]) not in src]
    print("\nCN_NAMES 需补 %d 个（示例）: %s" % (len(cn_missing), ", ".join(x["en"] for x in cn_missing[:6])))

    # FACTS：补 38 条（键为英文名）
    facts_missing = [x for x in c88.values() if ('"%s":' % x["en"]) not in fit]
    print("FACTS 需补 %d 条（示例）: %s" % (len(facts_missing), ", ".join(x["en"] for x in facts_missing[:6])))

    if not write:
        print("\n（未加 --write，未改动任何文件）")
        return

    # 1) RAW 追加
    src = src[:end] + "\n" + add_lines + src[end:]
    # 2) CN_NAMES 追加（在 CN_NAMES 字典末尾）
    cnm = src.find("CN_NAMES")
    cend = src.find("\n}", cnm)
    cn_add = "".join('    "%s": "%s",\n' % (x["en"], x["zh"]) for x in cn_missing)
    src = src[:cend] + "\n" + cn_add.rstrip("\n") + src[cend:]
    # 3) 两处数据修正
    for sid, fix in FIXES.items():
        if "brightest" in fix:
            bzh, ben, bmag = fix["brightest"]
            pat = re.compile(r'(\("%s",[^\n]*?\n?\s*"[^"]*",\s*"[^"]*",\s*)([0-9.]+)(,\s*\n?\s*\[)' % sid)
            def _fix(mm):
                return mm.group(1) + str(bmag) + mm.group(3)
            src2 = pat.sub(_fix, src, count=1)
            if src2 != src:
                print("已修正 %s 最亮星视星等 → %s" % (sid, bmag))
                src = src2
            else:
                print("!! %s 视星等未改（锚点未匹配），请手动核对" % sid)
        if "add_neighbor" in fix:
            nb = fix["add_neighbor"]
            # 在该星座元组的邻居列表里追加
            pat = re.compile(r'(\("%s",[\s\S]{0,400}?\[)([^\]]*)(\]\),)' % sid)
            def _nb(mm):
                return mm.group(1) + mm.group(2).rstrip() + (', ' if mm.group(2).strip() else '') + '"%s"' % nb + mm.group(3)
            src3 = pat.sub(_nb, src, count=1)
            if src3 != src:
                print("已在 %s 邻居里补上 %s" % (sid, nb))
                src = src3
            else:
                print("!! %s 邻居未改（锚点未匹配），请手动核对" % sid)
    io.open(SKY, "w", encoding="utf-8").write(src)
    print("已写入 build_sky.py")

    # 4) FACTS 追加
    fkey = fit.find("FACTS")
    fend = fit.find("\n}", fkey)
    f_add = "".join('    "%s": "%s",\n' % (x["en"], x["fact"]) for x in facts_missing)
    fit = fit[:fend] + "\n" + f_add.rstrip("\n") + fit[fend:]
    io.open(FIT, "w", encoding="utf-8").write(fit)
    print("已写入 fit_constellation_levels.py（新增 %d 条 FACTS）" % len(facts_missing))


if __name__ == "__main__":
    main()
