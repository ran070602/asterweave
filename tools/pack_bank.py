#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把无尽题库打包成与关卡共享常量池的紧凑块。

- 先给题库的星名应用 tools/star_proper_zh.py 的传统中文名（与闯关 51–88 关一致）
- 用 tools/compact_levels.py 的编码器打包，并把「与关卡常量池完全相同的条目」复用关卡池下标，
  只有真正不同的条目才进 BANK_CONST_EXTRA（目标：extras 尽量少甚至为 0）
- 自检：解包回来与题库 JSON 逐字段深比较

用法：python tools/pack_bank.py scan   # 只看池复用率
      python tools/pack_bank.py pack   # 生成 tools/endless_bank_packed.json 并自检
"""
import importlib.util, io, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))

def load_mod(name, path):
    sp = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

CL = load_mod("cl", "tools/compact_levels.py")
from star_proper_zh import PROPER

BANK = os.path.join(ROOT, "tools", "endless_bank_full.json")
LEVELS = os.path.join(ROOT, "tools", "levels.json")
OUT = os.path.join(ROOT, "tools", "endless_bank_packed.json")


def named(bank):
    """给题库星名应用传统中文名（深拷贝，不改原文件）"""
    out = json.loads(json.dumps(bank))
    n = 0
    for d in out:
        for s in (d.get("theme") or {}).get("stars") or []:
            nm = PROPER.get(s.get("en"))
            if nm and s.get("name") != nm:
                s["name"] = nm; n += 1
    return out, n


def _eq(a, b):
    """CL.deep_eq 返回的是差异列表（空列表才是相等），别当布尔用。"""
    return not CL.deep_eq(a, b)


def pack_any(levels, pool):
    """按「完整元数据」去重打包（题库里同一星座有 2 块盘面，选星可能不同，
    而 compact_levels.pack() 假定同一星座元数据唯一，故这里用自己的实现）。
    pool 会被就地扩展；返回 (pool, packed)。"""
    packed = []
    for d in levels:
        th = d.get("theme") or {}
        star_meta = [[s["name"], s["en"], s["mag"]] for s in th.get("stars") or []]
        meta = [th.get("id"), th.get("name"), th.get("nameEn"), th.get("fact"),
                star_meta, [list(x) for x in th.get("lines") or []]]
        ci = None
        for j, e in enumerate(pool):
            if _eq(e, meta):
                ci = j; break
        if ci is None:
            ci = len(pool); pool.append(meta)
        sels = []
        for s in th.get("stars") or []:
            si = None
            for k, st in enumerate(star_meta):
                if st[0] == s["name"] and st[1] == s["en"]:
                    si = k; break
            assert si is not None, "星不在池条目里: %s %s" % (s["name"], s["en"])
            sels.append([si, s["rc"][0], s["rc"][1]])
        n = d["size"]
        packed.append([d["id"], d["name"], n,
                       CL.pack_bits(n, d["mines"]), CL.pack_bits(n, d["noise"]),
                       d["opening"][0], d["opening"][1], d.get("lives", 3),
                       d.get("teach", ""), d.get("technique", ""),
                       1 if d.get("showRuns") else 0,
                       d.get("timeK") if isinstance(d.get("timeK"), (int, float)) else None,
                       ci, sels])
    return pool, packed


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "scan"
    lv = json.load(io.open(LEVELS, encoding="utf-8"))
    bank_raw = json.load(io.open(BANK, encoding="utf-8"))
    bank, renamed = named(bank_raw)
    print("题库 %d 题；应用传统中文星名 %d 处" % (len(bank), renamed))

    lconst, lpacked = CL.pack(lv)
    pool = list(lconst)
    pool, remapped = pack_any(bank, pool)
    reuse = len(lconst)
    extras = len(pool) - len(lconst)
    print("常量池：关卡 %d 条 → 合并后 %d 条（题库复用关卡池，新增 extras %d 条）"
          % (len(lconst), len(pool), extras))

    # 自检：解包回来与题库（已改名）逐字段比较
    back = CL.unpack(pool, remapped)
    bad = []
    for a, b in zip(bank, back):
        for k in ("id", "name", "size", "mines", "noise", "opening", "lives", "teach",
                  "technique", "showRuns", "theme"):
            if not _eq(a.get(k), b.get(k)):
                bad.append((a["id"], k)); break
    print("解包往返：%d/%d 题全等%s" % (len(bank) - len(bad), len(bank),
          ("  不一致: " + str(bad[:5])) if bad else ""))

    extra_js = "\nconst BANK_CONST_EXTRA = " + CL.js_literal(pool[len(lconst):]) + ";\n"
    pack_js = "const BANK_PACKED = " + CL.js_literal(remapped) + ";\n"
    print("BANK_CONST_EXTRA %d 字节｜BANK_PACKED %d 字节｜合计 %d 字节"
          % (len(extra_js.encode("utf-8")), len(pack_js.encode("utf-8")),
             len((extra_js + pack_js).encode("utf-8"))))
    if mode == "pack":
        io.open(OUT, "w", encoding="utf-8").write(json.dumps(
            {"extra": pool[len(lconst):], "packed": remapped, "poolSize": len(pool)}, ensure_ascii=False))
        print("已写出", OUT)


if __name__ == "__main__":
    main()
