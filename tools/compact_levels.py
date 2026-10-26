#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""关卡注入数据压缩（构建期编码 / 运行期展开）。

把 tools/levels.json 里"每个数字单独一行"的冗长 JSON，换成两个紧凑 JS 字面量块：

    /* LEVELS_INJECT_START */
    const CONST = [ [id, zh, nameEn, fact, [[starName, starEn, mag], ...], [[a,b], ...]], ... ];
    const LEVELS_PACKED = [ [id, name, n, mineB64, noiseB64, openingR, openingC, lives,
                             teach, technique, showRuns, timeK, constIdx, [[starIdx, r, c], ...]], ... ];
    /* LEVELS_INJECT_END */

设计要点（与 game/index.html 里的 expandLevelPacked() 严格对应）：
  * mines / noise 各编码成一张 n*n 的位图：行优先 i = r*n + c，每字节从**高位到低位**填格，
    最后不足 8 位补 0，整体 base64（JS 端 atob + charCodeAt 取值）。
  * 不存 rowRuns / colRuns —— startBoard() 缺字段时会用 runsFromMines() 现算（等价性由 verify 证明）。
  * 不存 theme.stars[].tint —— 运行期按生成器的原始规则从中文星名推导：
      tools/fit_constellation_levels.py:464-465 与 tools/gen_difficulty_first.py:416-417
        warm  ← 参宿四 / 心宿二
        cool  ← 参宿七 / 天津四
        其余 neutral
  * 88 关共用 88 个星座（每关星座不同），星名/星等/连线在 CONST 里只存一份，
    逐关只存"第 k 颗星落在盘面的哪一格"（[[starIdx, r, c], ...]）。

子命令：
    python tools/compact_levels.py verify    # pack→unpack→与 levels.json 逐字段深比较 + 位图往返
    python tools/compact_levels.py size      # 压缩前后注入数据字节数 + 预估单文件大小
    python tools/compact_levels.py inject    # 打印注入块（--limit N 可只取前 N 关，做源码样例）
"""
import base64
import json
import os
import random
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEVELS_PATH = os.path.join(ROOT, "tools", "levels.json")

BLOCK_RE = re.compile(r"/\* LEVELS_INJECT_START \*/(.*?)/\* LEVELS_INJECT_END \*/", re.S)
CONST_RE = re.compile(r"const CONST = (\[.*?\]);\s*const LEVELS_PACKED = (\[.*?\]);", re.S)

# 星色推导（生成器原文规则见模块 docstring）
TINT_WARM = ("参宿四", "心宿二")
TINT_COOL = ("参宿七", "天津四")


# ---------------------------------------------------------------- 位图

def pack_bits(n, cells):
    """cells: [(r, c), ...] -> base64(str)。逐格置位，MSB 优先，行优先。"""
    nbytes = (n * n + 7) // 8
    buf = bytearray(nbytes)
    for rc in cells:
        r, c = int(rc[0]), int(rc[1])
        i = r * n + c
        buf[i >> 3] |= 1 << (7 - (i & 7))
    return base64.b64encode(bytes(buf)).decode("ascii")


def unpack_bits(b64, n):
    """base64 -> [[r, c], ...]（按行优先升序，与 levels.json 中的既有顺序一致）。"""
    raw = base64.b64decode(b64)
    out = []
    for i in range(n * n):
        if raw[i >> 3] & (1 << (7 - (i & 7))):
            out.append([i // n, i % n])
    return out


# ---------------------------------------------------------------- 编码 / 解码

def tint_for(zh):
    if zh in TINT_WARM:
        return "warm"
    if zh in TINT_COOL:
        return "cool"
    return "neutral"


def pack(levels):
    """levels(list) -> (const, packed)：两个纯 Python 结构（可 json.dumps 成 JS 字面量）。"""
    const = []
    index_of = {}
    packed = []
    for d in levels:
        t = d["theme"]
        cid = t["id"]
        meta = (t["name"], t["nameEn"], t["fact"],
                tuple((s["name"], s["en"], s["mag"]) for s in t["stars"]),
                tuple((int(a), int(b)) for a, b in t["lines"]))
        if cid in index_of:
            ci = index_of[cid]
            assert const[ci][1:] == list(meta), "同一星座在不同关里的元数据不一致: " + str(cid)
        else:
            ci = len(const)
            index_of[cid] = ci
            const.append([cid, meta[0], meta[1], meta[2],
                          [[s[0], s[1], s[2]] for s in meta[3]],
                          [[a, b] for a, b in meta[4]]])
        stars = [[k, int(s["rc"][0]), int(s["rc"][1])] for k, s in enumerate(t["stars"])]
        packed.append([
            int(d["id"]), d["name"], int(d["size"]),
            pack_bits(int(d["size"]), d["mines"]),
            pack_bits(int(d["size"]), d["noise"]),
            int(d["opening"][0]), int(d["opening"][1]),
            int(d["lives"]), d["teach"], d["technique"], bool(d["showRuns"]),
            (d["timeK"] if isinstance(d.get("timeK"), (int, float)) else None),
            ci, stars,
        ])
    return const, packed


def unpack(const, packed):
    """(const, packed) -> levels；字段与 levels.json **逐字段等价**（不含 rowRuns/colRuns）。"""
    out = []
    for p in packed:
        c = const[p[12]]
        n = int(p[2])
        stars = []
        for s in p[13]:
            m = c[4][s[0]]
            stars.append({"name": m[0], "en": m[1], "rc": [int(s[1]), int(s[2])],
                          "mag": m[2], "tint": tint_for(m[0])})
        lv = {
            "id": p[0], "name": p[1], "size": n,
            "mines": unpack_bits(p[3], n), "noise": unpack_bits(p[4], n),
            "showRuns": bool(p[10]),
            "opening": [p[5], p[6]],
            "lives": p[7], "teach": p[8], "technique": p[9],
            "theme": {"id": c[0], "name": c[1], "nameEn": c[2], "fact": c[3],
                      "stars": stars, "lines": [[int(a), int(b)] for a, b in c[5]]},
        }
        if isinstance(p[11], (int, float)) and not isinstance(p[11], bool):
            lv["timeK"] = p[11]
        out.append(lv)
    return out


# ---------------------------------------------------------------- JS 字面量

def js_literal(obj):
    """json.dumps 的紧凑形式即合法 JS 字面量（数组/字符串/数字/null）。
    额外把 U+2028/U+2029 转义，避免个别引擎把行分隔符当语句终止。"""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def _rows(arr):
    return ",\n".join("  " + js_literal(x) for x in arr)


def build_block(levels):
    """生成（含注入标记的）注入块文本。build_release.py 直接调用本函数。"""
    const, packed = pack(levels)
    return ("/* LEVELS_INJECT_START */\n"
            "const CONST = [\n" + _rows(const) + "\n];\n"
            "const LEVELS_PACKED = [\n" + _rows(packed) + "\n];\n"
            "/* LEVELS_INJECT_END */")


def decode_block(text):
    """注入块文本 -> (const, packed)；纯 JSON 回读（用于构建期/测试期独立解码）。"""
    m = CONST_RE.search(text)
    if not m:
        raise ValueError("注入块里找不到 const CONST / const LEVELS_PACKED")
    return json.loads(m.group(1)), json.loads(m.group(2))


def legacy_block(levels):
    """旧格式注入块（逐数字缩进 JSON），仅用于体积对比。"""
    return ("/* LEVELS_INJECT_START */\n"
            "const LEVELS = " + json.dumps(levels, ensure_ascii=False, indent=2) + ";\n"
            "/* LEVELS_INJECT_END */")


# ---------------------------------------------------------------- 校验

def deep_eq(a, b, path="root", bad=None):
    """严格深比较：bool 与 int 不混同（True != 1）。返回不一致清单。"""
    if bad is None:
        bad = []
    if isinstance(a, bool) or isinstance(b, bool):
        if a is not b:
            bad.append("%s: %r != %r" % (path, a, b))
        return bad
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a or k not in b:
                bad.append("%s.%s: 仅一侧存在 (%r / %r)" % (path, k, k in a, k in b))
            else:
                deep_eq(a[k], b[k], "%s.%s" % (path, k), bad)
        return bad
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            bad.append("%s: 长度 %d != %d" % (path, len(a), len(b)))
            return bad
        for i, (x, y) in enumerate(zip(a, b)):
            deep_eq(x, y, "%s[%d]" % (path, i), bad)
        return bad
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a != b or (isinstance(a, float) != isinstance(b, float)):
            bad.append("%s: %r != %r" % (path, a, b))
        return bad
    if a != b:
        bad.append("%s: %r != %r" % (path, a, b))
    return bad


def runs_from_mines(mine_set, n, by_row, k):
    """与 game/index.html runsFromMines() 同一算法（用于验证"现算 == 存表"）。"""
    runs, cur = [], 0
    for t in range(n):
        i = k * n + t if by_row else t * n + k
        if i in mine_set:
            cur += 1
        else:
            if cur > 0:
                runs.append(cur)
            cur = 0
    if cur > 0:
        runs.append(cur)
    return runs


def cmd_verify():
    levels = json.load(open(LEVELS_PATH, encoding="utf-8"))
    fail = []

    # 1) 位图往返：全部 88 关的 mines / noise
    rt = 0
    for d in levels:
        n = d["size"]
        for f in ("mines", "noise"):
            if unpack_bits(pack_bits(n, d[f]), n) != [list(x) for x in d[f]]:
                fail.append("第%d关 %s 位图往返不一致" % (d["id"], f))
            rt += 1

    # 2) 位图往返：随机样本（确定性种子）
    rnd = random.Random(20261026)
    for t in range(2000):
        n = rnd.randint(1, 16)
        cells = sorted({(rnd.randrange(n), rnd.randrange(n)) for _ in range(rnd.randint(0, n * n))})
        got = unpack_bits(pack_bits(n, cells), n)
        if got != [[r, c] for r, c in cells]:
            fail.append("随机位图样本 #%d (n=%d) 不一致" % (t, n))
            break
    print("位图往返：88 关 × 2 张（mines/noise）= %d 张 + 2000 组随机样本 —— %s"
          % (rt, "全部无损" if not fail else "有损"))

    # 3) pack -> JS 字面量 -> 独立 JSON 回读 -> unpack -> 逐字段深比较
    block = build_block(levels)
    const, packed = decode_block(block)
    got = unpack(const, packed)
    if len(got) != len(levels):
        fail.append("关数不一致 %d != %d" % (len(got), len(levels)))

    n_cmp = 0
    for a, b in zip(levels, got):
        # b 里不含 rowRuns/colRuns：按 startBoard 的现算规则补上后比较
        n = b["size"]
        mine_set = set()
        for r, c in b["mines"]:
            mine_set.add(r * n + c)
        for r, c in b["noise"]:
            mine_set.add(r * n + c)
        b2 = dict(b)
        b2["rowRuns"] = [runs_from_mines(mine_set, n, True, r) for r in range(n)]
        b2["colRuns"] = [runs_from_mines(mine_set, n, False, c) for c in range(n)]
        # 键集合必须与原始一致（即：只少 rowRuns/colRuns 两个键，不多不少）
        if set(b2) != set(a):
            fail.append("第%d关 字段集合不一致：多了 %s / 少了 %s"
                        % (a["id"], sorted(set(b2) - set(a)), sorted(set(a) - set(b2))))
        deep_eq(a, b2, "level[%s]" % a["id"], fail)
        n_cmp += 1
    print("pack→JS 字面量→回读→unpack：%d 关逐字段深比较 —— %s"
          % (n_cmp, "全等" if not fail else "不等"))

    # 4) 现算线索 vs levels.json 里存的线索（证明"不存 rowRuns/colRuns"是安全的）
    diff = []
    for d in levels:
        n = d["size"]
        mine_set = set()
        for r, c in d["mines"]:
            mine_set.add(r * n + c)
        for r, c in d["noise"]:
            mine_set.add(r * n + c)
        if [runs_from_mines(mine_set, n, True, r) for r in range(n)] != d["rowRuns"]:
            diff.append("第%d关 rowRuns" % d["id"])
        if [runs_from_mines(mine_set, n, False, c) for c in range(n)] != d["colRuns"]:
            diff.append("第%d关 colRuns" % d["id"])
    print("现算线索 vs 存表线索：%d 关 × (rowRuns+colRuns) —— %s"
          % (len(levels), "完全一致（现算安全）" if not diff else "不一致: " + ", ".join(diff[:8])))
    if diff:
        fail.append("现算线索与存表不一致：" + ", ".join(diff[:8]))

    # 5) 常量池去重数量
    print("常量池：%d 个星座（88 关）｜星点元数据 %d 条｜连线 %d 段"
          % (len(const), sum(len(c[4]) for c in const), sum(len(c[5]) for c in const)))

    if fail:
        print("\n!! verify 失败：")
        for x in fail[:40]:
            print("   -", x)
        return 1
    print("\n✅ verify 全部通过：编码无损，展开后与 tools/levels.json 逐字段等价")
    return 0


def cmd_size():
    levels = json.load(open(LEVELS_PATH, encoding="utf-8"))
    old = legacy_block(levels).encode("utf-8")
    new = build_block(levels).encode("utf-8")
    print("注入数据（LEVELS 块，UTF-8 字节）")
    print("  旧（indent=2 JSON）：%8d 字节 / %.1f KB" % (len(old), len(old) / 1024))
    print("  新（CONST + LEVELS_PACKED）：%8d 字节 / %.1f KB" % (len(new), len(new) / 1024))
    print("  省下：%d 字节 / %.1f KB（%.1f%%）"
          % (len(old) - len(new), (len(old) - len(new)) / 1024,
             100.0 * (len(old) - len(new)) / len(old)))
    const, packed = pack(levels)
    print("  其中 CONST = %d 字节，LEVELS_PACKED = %d 字节"
          % (len(_rows(const).encode("utf-8")), len(_rows(packed).encode("utf-8"))))
    dist = os.path.join(ROOT, "dist", "星织-游戏本体", "index.html")
    if os.path.exists(dist):
        cur = os.path.getsize(dist)
        compact_now = "const LEVELS_PACKED" in open(dist, encoding="utf-8").read()
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
        print("  注：与历史实测对账时，若同时改了 UI 源码（本次新增了运行期展开函数），")
        print("      单文件差值 = 注入块差值 + UI 源码差值，两个方向都能对上。")
    else:
        print("（dist 尚未构建，无法给出单文件预估）")
    return 0


def cmd_inject(argv):
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    levels = json.load(open(LEVELS_PATH, encoding="utf-8"))
    if limit:
        levels = levels[:limit]
    sys.stdout.write(build_block(levels) + "\n")
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
