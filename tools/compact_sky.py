#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图鉴（SKY）注入数据压缩（构建期编码 / 运行期展开）。

把 tools/sky.json 里"每个数字单独一行"的冗长 JSON，换成一条紧凑 JS 字面量块：

    /* SKY_INJECT_START */
    const SKY_NB_EXTRA = [["Bootes","牧夫座"]];
    const SKY_PACKED = [
      [id, zh, en, latin, abbr, ra, dec, areaRank, bzh, ben, bmag, [相邻槽位, ...]],
      ...
    ];
    const SKY = expandSkyPacked();
    /* SKY_INJECT_END */

设计要点（与 game/index.html 里的 expandSkyPacked() 严格对应）：
  * 不存 raText / decText —— 运行期按 tools/build_sky.py 的 fmt_ra / fmt_dec 现算
    （含 U+2212 负号、° / ′ 三个字符，以及"四舍六入五成双"的取整；
     88 条数据里实测没有任何一条落在 .5 边界上，仍按 CPython round() 语义实现）。
  * 不存 season / zone —— 运行期按 build_sky.py 的 season_of / zone_of 现算
    （赤经边界 9/15/21/3，赤纬边界 ±30）。
  * 不存 level —— 运行期用 LEVELS 的 theme.id 反查关卡号（= build_sky.level_map() 的规则），
    **因此 levels.json 变化后运行期自动同步**；若某个 id 不在 levels.json 里会展开成 null，
    compact_sky verify / build_release 的往返深比较会立刻报错。
  * neighbors 只存"槽位号"：拉丁名在 88 条里唯一，
      j < 88  → 就是 SKY_PACKED[j] 本身（latin/zh/id/level 全部现算，等价于 build_sky.py 的 by_latin 反查）
      j >= 88 → SKY_NB_EXTRA[j-88]（不在游戏 88 星座里的邻居，只有拉丁名 + 中文名，id/level 为 null）
  * inGameNeighbors / neighbors[].zh 全部现算，不单独存。

子命令：
    python tools/compact_sky.py verify    # pack→unpack→与 sky.json 逐字段深比较 + 现算字段独立复算
    python tools/compact_sky.py size      # 压缩前后注入数据字节数 + 预估单文件大小
    python tools/compact_sky.py inject    # 打印注入块（--limit N 可只取前 N 条，做源码样例）
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKY_PATH = os.path.join(ROOT, "tools", "sky.json")
LEVELS_PATH = os.path.join(ROOT, "tools", "levels.json")

# 复用 compact_levels 的通用工具：deep_eq()（严格深比较：bool/int 不混同，int/float 不混同）
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import compact_levels  # noqa: E402

# 注入块定位（替换进 HTML 时请用函数式替换 re.sub(lambda m: block, ...)，
# 否则替换串里的反斜杠会被 re 当转义处理）。
BLOCK_RE = re.compile(r"/\* SKY_INJECT_START \*/.*?/\* SKY_INJECT_END \*/", re.S)
START_MARK = "/* SKY_INJECT_START */"
END_MARK = "/* SKY_INJECT_END */"


# ---------------------------------------------------------------- 通用

def deep_eq(a, b, path="root", bad=None):
    """严格深比较：bool 与 int 不混同（True != 1），int 与 float 也不混同。
    与 tools/compact_levels.py 的同名函数是同一实现（复用，避免两份实现漂移）。"""
    return compact_levels.deep_eq(a, b, path, bad)


def level_map(levels):
    """星座 id -> 关卡号；与 tools/build_sky.py 的 level_map() 同一规则（后出现的覆盖先出现的）。"""
    m = {}
    for x in levels:
        tid = (x.get("theme") or {}).get("id")
        if tid:
            m[tid] = x["id"]
    return m


# ---------------------------------------------------------------- 现算规则（照抄 build_sky.py）

def fmt_ra(ra):
    h = int(ra)
    m = int(round((ra - h) * 60))
    if m == 60:
        h, m = h + 1, 0
    return f"{h}h{m:02d}m"


def fmt_dec(dec):
    d = int(abs(dec))
    m = int(round((abs(dec) - d) * 60))
    if m == 60:
        d, m = d + 1, 0
    return ("+" if dec >= 0 else "−") + f"{d}°{m:02d}′"


def season_of(ra):
    if 9 <= ra < 15: return "春季"
    if 15 <= ra < 21: return "夏季"
    if ra >= 21 or ra < 3: return "秋季"
    return "冬季"


def zone_of(dec):
    if dec >= 30: return "北天"
    if dec <= -30: return "南天"
    return "赤道带"


# ---------------------------------------------------------------- 编码 / 解码

def pack(sky):
    """sky(list) -> (extra, packed)：两个纯 Python 结构（可 json.dumps 成 JS 字面量）。"""
    slot_of = {}
    for i, s in enumerate(sky):
        key = s["latin"]
        if key in slot_of:
            raise ValueError("拉丁名重复，无法用槽位号寻址: %r（%s / %s）"
                             % (key, sky[slot_of[key]]["id"], s["id"]))
        slot_of[key] = i
    n = len(sky)
    extra, extra_slot = [], {}
    packed = []
    for s in sky:
        nbr = []
        for nb in s["neighbors"]:
            j = slot_of.get(nb["latin"])
            if j is None:
                # 不在 88 星座里的邻居：只在 extra 里存一次（拉丁名 + 中文名）
                j = extra_slot.get(nb["latin"])
                if j is None:
                    j = n + len(extra)
                    extra_slot[nb["latin"]] = j
                    extra.append([nb["latin"], nb["zh"]])
                elif extra[j - n][1] != nb["zh"]:
                    raise ValueError("同一个邻居拉丁名 %r 出现不同中文名: %r / %r"
                                     % (nb["latin"], extra[j - n][1], nb["zh"]))
            nbr.append(j)
        b = s["brightest"]
        packed.append([s["id"], s["zh"], s["en"], s["latin"], s["abbr"],
                       s["ra"], s["dec"], s["areaRank"],
                       b["zh"], b["en"], b["mag"], nbr])
    return extra, packed


def unpack(extra, packed, levels):
    """(extra, packed, levels) -> sky；字段与 tools/sky.json **逐字段等价**。"""
    lm = level_map(levels)
    n = len(packed)
    out = []
    for p in packed:
        ra, dec = p[5], p[6]
        nbr = []
        in_game = []
        for j in p[11]:
            if j < n:
                q = packed[j]
                nbr.append({"latin": q[3], "zh": q[1], "id": q[0], "level": lm.get(q[0])})
                in_game.append(q[0])
            else:
                e = extra[j - n]
                nbr.append({"latin": e[0], "zh": e[1], "id": None, "level": None})
        if p[0] not in lm:
            raise ValueError("星座 %r 不在 levels.json 的 theme.id 里，无法现算关卡号"
                             "（先跑 python tools/build_sky.py 重建 tools/sky.json）" % p[0])
        out.append({
            "id": p[0], "zh": p[1], "en": p[2], "latin": p[3], "abbr": p[4],
            "level": lm[p[0]],
            "ra": ra, "dec": dec,
            "raText": fmt_ra(ra), "decText": fmt_dec(dec),
            "areaRank": p[7], "season": season_of(ra), "zone": zone_of(dec),
            "brightest": {"zh": p[8], "en": p[9], "mag": p[10]},
            "neighbors": nbr,
            "inGameNeighbors": in_game,
        })
    return out


# ---------------------------------------------------------------- JS 字面量

def js_literal(obj):
    """json.dumps 的紧凑形式即合法 JS 字面量（数组/字符串/数字/null）。
    额外把 U+2028/U+2029 转义，避免个别引擎把行分隔符当语句终止。"""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _rows(arr):
    return ",\n".join("  " + js_literal(x) for x in arr)


def build_block(sky, levels):
    """生成（含注入标记的）注入块文本。build_release.py 直接调用本函数。
    levels 只用于校验（level 本身是运行期现算的，不进数据）。"""
    extra, packed = pack(sky)
    lm = level_map(levels)
    missing = [s["id"] for s in sky if s["id"] not in lm]
    if missing:
        raise ValueError("这些星座不在 levels.json 的 theme.id 里，图鉴关卡号无法现算: %s" % missing[:8])
    return (START_MARK + "\n"
            "const SKY_NB_EXTRA = " + js_literal(extra) + ";\n"
            "const SKY_PACKED = [\n" + _rows(packed) + "\n];\n"
            "const SKY = expandSkyPacked();\n"
            + END_MARK)


def _grab(text, name):
    """从注入块里取出 `const <name> = <纯 JSON>;` 的值（raw_decode，字符串里的分号/方括号都不怕）。"""
    key = "const %s = " % name
    i = text.index(key)
    return json.JSONDecoder().raw_decode(text, i + len(key))[0]


def decode_block(text):
    """注入块文本 -> (extra, packed)；纯 JSON 回读（用于构建期/测试期独立解码）。"""
    return _grab(text, "SKY_NB_EXTRA"), _grab(text, "SKY_PACKED")


def legacy_block(sky):
    """旧格式注入块（逐数字缩进 JSON），仅用于体积对比。"""
    return (START_MARK + "\n"
            "const SKY = " + json.dumps(sky, ensure_ascii=False, indent=2) + ";\n"
            + END_MARK)


# ---------------------------------------------------------------- 校验

def cmd_verify():
    sky = json.load(open(SKY_PATH, encoding="utf-8"))
    levels = json.load(open(LEVELS_PATH, encoding="utf-8"))
    fail, notes = [], []

    # 1) pack -> JS 字面量 -> 独立 JSON 回读 -> unpack -> 逐字段深比较
    block = build_block(sky, levels)
    extra, packed = decode_block(block)
    got = unpack(extra, packed, levels)
    if len(got) != len(sky):
        fail.append("条数不一致 %d != %d" % (len(got), len(sky)))
    n_nb = 0
    for a, b in zip(sky, got):
        if set(a) != set(b):
            fail.append("%s 字段集合不一致：多了 %s / 少了 %s"
                        % (a["id"], sorted(set(b) - set(a)), sorted(set(a) - set(b))))
        deep_eq(a, b, "sky[%s]" % a["id"], fail)
        if [n["latin"] for n in a["neighbors"]] != [n["latin"] for n in b["neighbors"]]:
            fail.append("%s 相邻星座顺序/内容不一致" % a["id"])
        n_nb += len(a["neighbors"])
    print("pack→JS 字面量→回读→unpack：%d 条星座逐字段深比较（含 %d 条相邻关系、%d 条 inGameNeighbors）—— %s"
          % (len(got), n_nb, sum(len(x["inGameNeighbors"]) for x in got),
             "全等" if not fail else "不等"))

    # 2) 现算 raText / decText / season / zone（证明"不存这四个字段"安全）
    diff = []
    for s in sky:
        if fmt_ra(s["ra"]) != s["raText"]:
            diff.append("%s raText 现算 %r != 存表 %r" % (s["id"], fmt_ra(s["ra"]), s["raText"]))
        if fmt_dec(s["dec"]) != s["decText"]:
            diff.append("%s decText 现算 %r != 存表 %r" % (s["id"], fmt_dec(s["dec"]), s["decText"]))
        if season_of(s["ra"]) != s["season"]:
            diff.append("%s season 现算 %r != 存表 %r" % (s["id"], season_of(s["ra"]), s["season"]))
        if zone_of(s["dec"]) != s["zone"]:
            diff.append("%s zone 现算 %r != 存表 %r" % (s["id"], zone_of(s["dec"]), s["zone"]))
    print("现算 raText/decText/season/zone：%d 条 × 4 字段 —— %s"
          % (len(sky), "完全一致（现算安全）" if not diff else "不一致 %d 处" % len(diff)))
    if diff:
        fail.append("现算坐标文本/季节/天区与存表不一致：" + "; ".join(diff[:6]))
        for x in diff[:12]:
            print("   !! " + x)

    # 2b) 取整边界：JS Math.round（四舍五入）与 CPython round（四舍六入五成双）会在 .5 上分叉
    risky = []
    for s in sky:
        for tag, v in (("ra", s["ra"]), ("dec", abs(s["dec"]))):
            frac = (v - int(v)) * 60
            if abs(frac - round(frac)) == 0.5:
                risky.append("%s %s=%r → 分钟数 %.1f 正好是 .5" % (s["id"], tag, v, frac))
    print("取整边界（.5 半整数）：%d 处 —— %s"
          % (len(risky), "无（运行期仍按 CPython round 的 half-even 实现，双保险）"
             if not risky else "有，需逐条复核: " + "; ".join(risky[:4])))

    # 3) 现算 level（LEVELS 反查）vs sky.json 里的 level
    lm = level_map(levels)
    bad_lv = ["%s (存表 %r / levels.json 反查 %r)" % (s["id"], s["level"], lm.get(s["id"]))
              for s in sky if lm.get(s["id"]) != s["level"]]
    print("现算 level（levels.json 反查）：%d 条 —— %s"
          % (len(sky), "完全一致" if not bad_lv else "不一致 " + "; ".join(bad_lv[:6])))
    if bad_lv:
        fail.append("level 现算与 sky.json 不一致：" + "; ".join(bad_lv[:6]))

    # 4) 现算 neighbors[].id / level / zh、inGameNeighbors vs 存表
    by_latin = {s["latin"]: s for s in sky}
    bad_nb, bad_zh, bad_ing = [], [], []
    for s in sky:
        for nb in s["neighbors"]:
            own = by_latin.get(nb["latin"])
            eid = own["id"] if own else None
            elv = lm.get(eid) if eid else None
            ezh = own["zh"] if own else None
            if nb["id"] != eid or nb["level"] != elv:
                bad_nb.append("%s→%s (存表 id=%r/level=%r，现算 id=%r/level=%r)"
                              % (s["id"], nb["latin"], nb["id"], nb["level"], eid, elv))
            if ezh is not None and nb["zh"] != ezh:
                bad_zh.append("%s→%s (存表 %r != 该星座自身 zh %r)" % (s["id"], nb["latin"], nb["zh"], ezh))
        exp_ing = [n["id"] for n in s["neighbors"] if n["id"]]
        if exp_ing != s["inGameNeighbors"]:
            bad_ing.append(s["id"])
    print("现算 neighbors[].id/level：%d 条 —— %s"
          % (n_nb, "完全一致" if not bad_nb else "不一致 " + "; ".join(bad_nb[:6])))
    print("现算 neighbors[].zh（用 88 条自身的中文名）：—— %s"
          % ("完全一致（524 条里只有不在游戏内的邻居走 SKY_NB_EXTRA）" if not bad_zh
             else "不一致 " + "; ".join(bad_zh[:6])))
    print("现算 inGameNeighbors：%d 条 —— %s"
          % (len(sky), "完全一致" if not bad_ing else "不一致 " + ", ".join(bad_ing[:6])))
    if bad_nb:
        fail.append("neighbors 的 id/level 现算与存表不一致：" + "; ".join(bad_nb[:6]))
    if bad_zh:
        fail.append("neighbors 的 zh 现算与存表不一致：" + "; ".join(bad_zh[:6]))
    if bad_ing:
        fail.append("inGameNeighbors 现算与存表不一致：" + ", ".join(bad_ing[:6]))

    # 4b) 不在 88 星座里的邻居（只报告，不改数值）
    pool = sorted({n["latin"] for s in sky for n in s["neighbors"]})
    out_of_game = [x for x in pool if x not in by_latin]
    if out_of_game:
        cnt = {}
        for s in sky:
            for n in s["neighbors"]:
                if n["latin"] in out_of_game:
                    cnt[n["latin"]] = cnt.get(n["latin"], 0) + 1
        extra, _p = pack(sky)
        notes.append("不在 88 星座（latin 字段）里的邻居拉丁名 %d 个：%s；其中 %s —— "
                     "它们的 id/level 存表就是 null，运行期也现算成 null（见 SKY_NB_EXTRA=%s）"
                     % (len(out_of_game), out_of_game,
                        ", ".join("%s 出现 %d 次" % (k, v) for k, v in sorted(cnt.items())),
                        js_literal(extra)))
    print("\n常量/相邻关系：%d 条星座｜相邻关系 %d 条｜其中游戏内可跳转 %d 条｜额外拉丁名槽位 %d 个"
          % (len(sky), n_nb, sum(len(s["inGameNeighbors"]) for s in sky), len(extra)))
    for x in notes:
        print("  · " + x)

    if fail:
        print("\n!! verify 失败：")
        for x in fail[:40]:
            print("   -", x)
        return 1
    print("\n✅ verify 全部通过：编码无损，展开后与 tools/sky.json 逐字段等价")
    return 0


def cmd_size():
    sky = json.load(open(SKY_PATH, encoding="utf-8"))
    levels = json.load(open(LEVELS_PATH, encoding="utf-8"))
    old = legacy_block(sky).encode("utf-8")
    new = build_block(sky, levels).encode("utf-8")
    print("注入数据（SKY 块，UTF-8 字节）")
    print("  旧（indent=2 JSON）：%8d 字节 / %.1f KB" % (len(old), len(old) / 1024))
    print("  新（SKY_NB_EXTRA + SKY_PACKED + 展开调用）：%8d 字节 / %.1f KB" % (len(new), len(new) / 1024))
    print("  省下：%d 字节 / %.1f KB（%.1f%%）"
          % (len(old) - len(new), (len(old) - len(new)) / 1024,
             100.0 * (len(old) - len(new)) / len(old)))
    extra, packed = pack(sky)
    print("  其中 SKY_PACKED 数据行 = %d 字节，SKY_NB_EXTRA = %d 字节"
          % (len(_rows(packed).encode("utf-8")), len(js_literal(extra).encode("utf-8"))))
    dist = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")
    if os.path.exists(dist):
        cur = os.path.getsize(dist)
        html = open(dist, encoding="utf-8").read()
        compact_now = "const SKY_PACKED" in html
        print("单文件（dist/星织-游戏本体/index.html）")
        if compact_now:
            print("  当前实测（紧凑注入）：%d 字节 / %.1f KB" % (cur, cur / 1024))
            print("  同一份源码按旧编码重建的预估：%d 字节 / %.1f KB（−%.1f KB）"
                  % (cur - len(new) + len(old), (cur - len(new) + len(old)) / 1024,
                     (len(old) - len(new)) / 1024))
        else:
            print("  当前实测（旧编码）：%d 字节 / %.1f KB" % (cur, cur / 1024))
            est = cur - len(old) + len(new)
            print("  预估构建后（紧凑编码）：%d 字节 / %.1f KB（−%.1f KB）"
                  % (est, est / 1024, (cur - est) / 1024))
        print("  注：单文件差值 = 注入块差值 + UI 源码差值（本次新增了运行期展开函数）。")
    else:
        print("（dist 尚未构建，无法给出单文件预估）")
    return 0


def cmd_inject(argv):
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    sky = json.load(open(SKY_PATH, encoding="utf-8"))
    levels = json.load(open(LEVELS_PATH, encoding="utf-8"))
    sub = sky[:limit] if limit else sky
    # 只取前 N 条时，落在子集之外的邻居会自动进 SKY_NB_EXTRA，块本身仍然自洽（可解码可展开）
    sys.stdout.write(build_block(sub, levels) + "\n")
    return 0


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else "verify"
    if cmd == "verify":
        return cmd_verify()
    if cmd == "size":
        return cmd_size()
    if cmd == "inject":
        return cmd_inject(argv[1:])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
