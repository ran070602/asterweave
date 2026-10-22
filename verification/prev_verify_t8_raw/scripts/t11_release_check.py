# -*- coding: utf-8 -*-
"""
T11 · 发布包结构与文档事实核对（独立复核）。

1) ZIP 结构：根目录条目、是否含 index.html、内层 index.html 与 dist 版本 sha256 是否一致、路径安全性
2) build_manifest.json 与实测 sha256/字节数是否一致
3) dist HTML 离线自包含扫描
4) tools/report.md / 两份交付文档 的关键数字与实测对照（尺寸/雷数/步数/探格/相容方案数/接受率）
5) “可靠规则能推完全盘 ⇒ 唯一确定”这条错误推论是否彻底删除（区分“残留断言”与“作为已修正错误被引用”）
6) 迭代文档是否如实标注“10 关发布包尚未独立复核”

用法：
    python verification/t11_release_check.py
输出：
    stdout + verification/out_t11_release.json
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FROZEN = ROOT / "verification" / "frozen10"
ZIP = FROZEN / "release.zip"
DIST_HTML = FROZEN / "dist_index_snapshot.html"
LEVELS = FROZEN / "levels_10levels.json"
REPORT = FROZEN / "report_10levels.md"
MANIFEST = FROZEN / "build_manifest.json"
SPEC = FROZEN / "SPEC_v1.1.md"
DESIGN = FROZEN / "design_doc.md"
ITER = FROZEN / "iteration_doc.md"

checks = []


def check(cid, ok, detail):
    checks.append({"id": cid, "ok": bool(ok), "detail": str(detail)})
    print(("[PASS] " if ok else "[FAIL] ") + cid + " :: " + detail)
    return bool(ok)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    dist_sha = sha(DIST_HTML)
    levels_sha = sha(LEVELS)
    zip_sha = sha(ZIP)

    print("== 1. ZIP 结构 ==")
    with zipfile.ZipFile(ZIP) as z:
        infos = z.infolist()
        names = [i.filename for i in infos]
        roots = [n for n in names if "/" not in n.rstrip("/")]
        print("  ZIP 条目（%d 个）: %s" % (len(names), names))
        print("  根目录条目: %s" % roots)
        check("ZIP 根目录含 index.html", "index.html" in roots,
              "根条目=%s" % roots)
        check("ZIP 无目录前缀（提交平台要求根目录即 index.html）",
              all(not n.startswith("/") and ".." not in n.split("/") for n in names),
              "全部条目均为相对路径")
        inner = z.read("index.html")
        inner_sha = hashlib.sha256(inner).hexdigest()
        check("ZIP 内 index.html == dist/冉政-游戏本体/index.html（sha256）",
              inner_sha == dist_sha, "zip 内 sha256=%s / dist sha256=%s" % (inner_sha[:16], dist_sha[:16]))
        check("ZIP 内 index.html 与冻结副本逐字节一致", inner == DIST_HTML.read_bytes(),
              "字节数=%d vs %d" % (len(inner), DIST_HTML.stat().st_size))
        others = [n for n in roots if n != "index.html"]
        if "README.txt" in names:
            txt = z.read("README.txt").decode("utf-8", "replace")
            print("  README.txt 前 200 字: %s" % txt[:200].replace("\n", " / "))
        check("ZIP 根目录条目 == manifest.zip_root_entries",
              sorted(roots) == sorted(manifest["zip_root_entries"]),
              "实测=%s 声明=%s" % (sorted(roots), sorted(manifest["zip_root_entries"])))

    print("== 2. build_manifest.json 与实测 ==")
    check("manifest.build_sha256 == dist index.html 实测 sha256",
          manifest["build_sha256"] == dist_sha, "%s vs %s" % (manifest["build_sha256"][:16], dist_sha[:16]))
    check("manifest.levels_sha256 == tools/levels.json 实测 sha256",
          manifest["levels_sha256"] == levels_sha, "%s vs %s" % (manifest["levels_sha256"][:16], levels_sha[:16]))
    check("manifest.html_bytes == dist HTML 实测字节数",
          manifest["html_bytes"] == DIST_HTML.stat().st_size,
          "%s vs %d" % (manifest["html_bytes"], DIST_HTML.stat().st_size))
    check("manifest.zip_bytes == ZIP 实测字节数",
          manifest["zip_bytes"] == ZIP.stat().st_size,
          "%s vs %d" % (manifest["zip_bytes"], ZIP.stat().st_size))
    check("manifest 记录了 ZIP 的 sha256（任务书称『sha256 见 build_manifest.json』）",
          "zip_sha256" in manifest,
          "manifest 字段=%s ；实测 ZIP sha256=%s" % (sorted(manifest.keys()), zip_sha))
    check("manifest.level_count == 10", manifest["level_count"] == 10, "level_count=%s" % manifest["level_count"])
    check("manifest.ui_sha256 指向的 game/index.html 仍存在且一致",
          (ROOT / "game" / "index.html").exists() and sha(ROOT / "game" / "index.html") == manifest["ui_sha256"],
          "ui_sha256=%s / 当前 game/index.html=%s" % (
              manifest["ui_sha256"][:16], sha(ROOT / "game" / "index.html")[:16]
              if (ROOT / "game" / "index.html").exists() else "(缺失)"))

    print("== 3. dist HTML 离线自包含 ==")
    html = DIST_HTML.read_text(encoding="utf-8")
    for pat in ["http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "<img", "<link", "import("]:
        hits = len(html.split(pat)) - 1
        check("dist HTML 不含 %r" % pat, hits == 0, "出现次数=%d" % hits)
    n_script = len(re.findall(r"<script", html))
    check("dist HTML 只有 1 个 <script>", n_script == 1, "<script 数=%d" % n_script)

    print("== 4. 文档数字 vs 实测 ==")
    levels = json.loads(LEVELS.read_text(encoding="utf-8"))
    out_b = json.loads((ROOT / "verification" / "out_b.json").read_text(encoding="utf-8"))
    out_a = json.loads((ROOT / "verification" / "out_a.json").read_text(encoding="utf-8"))
    out_c = json.loads((ROOT / "verification" / "out_c.json").read_text(encoding="utf-8"))
    b = {x["id"]: x for x in out_b["levels"]}
    a = {x["id"]: x for x in out_a["extras"]["per_level"]}
    c = {x["id"]: x for x in out_c["levels"]}
    rep = REPORT.read_text(encoding="utf-8")

    # 4a 报告 §0 表：尺寸/雷数/显示连续块/只用邻域/连续块判定/邻域判定/探格/相容方案数
    rows = {}
    for line in rep.splitlines():
        if re.match(r"^\|\s*\d+\s*\|", line):
            cells = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(cells) >= 10 and cells[0].isdigit():
                rows[int(cells[0])] = cells
    check("报告 §0 验收表覆盖全部 10 关", len(rows) == 10, "表行数=%d" % len(rows))
    for lid in sorted(rows):
        cells = rows[lid]
        lv = levels[lid - 1]
        size_doc = cells[1].replace("×", "x")
        size_meas = "%dx%d" % (lv["size"], lv["size"])
        mine_ok = cells[2] == str(len(lv["mines"]))
        runs_ok = (cells[3] == "是") == bool(lv["showRuns"])
        a_only_ok = (cells[4].find("能") >= 0) == b[lid]["verdict"]["a_only_solves"]
        digs_ok = cells[8] == str(b[lid]["a_plus_b"]["explicit_reveals"])
        check("文档数字 L%d 尺寸/雷数/显示连续块/只用邻域/探格 与实测一致" % lid,
              size_doc == size_meas and mine_ok and runs_ok and a_only_ok and digs_ok,
              "文档=%s/%s/%s/%s/探格%s ｜ 实测=%s/%d/%s/%s/探格%d" % (
                  size_doc, cells[2], cells[3], cells[4], cells[8],
                  size_meas, len(lv["mines"]), "是" if lv["showRuns"] else "否",
                  "能" if b[lid]["verdict"]["a_only_solves"] else "会卡住",
                  b[lid]["a_plus_b"]["explicit_reveals"]))

    # 4b 相容方案数
    doc_sol = {}
    for lid, cells in rows.items():
        m = re.match(r"^(\d+)", cells[9])
        doc_sol[lid] = int(m.group(1)) if m else None
    meas_sol = {lid: (None if c[lid]["full"].get("timeout") else c[lid]["full"]["solutions"]) for lid in c}
    for lid in sorted(rows):
        if doc_sol[lid] is not None:
            check("文档相容方案数 L%d == 独立实测" % lid, doc_sol[lid] == meas_sol.get(lid),
                  "文档=%s 实测=%s" % (doc_sol[lid], meas_sol.get(lid)))
        else:
            check("文档相容方案数 L%d 标注'未判定'，但独立实测可判定" % lid, False,
                  "文档=未判定 ｜ 实测=%s（报告未声称的数字，独立算出来了）" % meas_sol.get(lid))

    # 4c 报告未测的唯一性：与实测对照
    nonunique = [lid for lid in meas_sol if meas_sol[lid] not in (None, 1)]
    check("报告是否披露了所有 >1 解的关卡（L1-L3 之外）", False,
          "实测 >1 解的关卡=%s（报告 §0 仅披露 L1/L2/L3；L7=%s、L10=%s 未被披露）"
          % (nonunique, meas_sol.get(7), meas_sol.get(10)))

    # 4d 生成尝试/接受率（不可独立复现）
    gen = re.findall(r"生成尝试 \*\*(\d+)\*\* 次，接受 \*\*(\d+)\*\* 次", rep)
    check("报告已列出 10 关的生成尝试/接受（自述，未独立复现）", len(gen) == 10,
          "条目数=%d；例：%s" % (len(gen), gen[:3]))

    print("== 5. '可靠规则能推完全盘 ⇒ 唯一确定' 错误推论的残留检查 ==")
    pat_err = re.compile(r"唯一确定|被唯一|即可唯一")
    pat_ctx = re.compile(r"错误|纠正|不成立|已改正|反例|不能")
    for label, path in (("tools/report.md", REPORT), ("冉政-设计思路文档.md", DESIGN),
                        ("冉政-迭代优化过程文档.md", ITER), ("docs/SPEC.md", SPEC)):
        txt = path.read_text(encoding="utf-8")
        hits = [(i + 1, l.strip()) for i, l in enumerate(txt.splitlines())
                if pat_err.search(l) and "可靠规则" in l or pat_err.search(l) and "推完全盘" in l]
        residual = [h for h in hits if not pat_ctx.search(h[1])]
        check("%s 无残留的错误推论（作为已修正错误引用不算残留）" % label, not residual,
              "命中行=%s ；判为残留=%s" % ([h[0] for h in hits], [h[0] for h in residual]))

    print("== 6. 迭代文档是否如实标注发布包未独立复核 ==")
    itxt = ITER.read_text(encoding="utf-8")
    check("迭代文档写明 10 关发布包尚未独立复核",
          "尚未独立复核" in itxt or "待独立复核" in itxt or "待执行" in itxt,
          str([l.strip() for l in itxt.splitlines() if "尚未独立复核" in l or "待执行" in l][:3]))
    check("迭代文档 §3.4 已记录 5 条不通过与处理", "5 条" in itxt and "26" in itxt,
          "含『5 条』与『26』：%s" % ("是" if ("5 条" in itxt and "26" in itxt) else "否"))
    check("迭代文档仍称第 7 关唯一性未判定（实测 L7 有 2 个相容方案）",
          "7 关的静态唯一解未判定" in itxt or ("7 关" in itxt and "未判定" in itxt),
          str([l.strip()[:90] for l in itxt.splitlines() if "未判定" in l][:3]))

    out = {"checks": checks,
           "all_pass": all(x["ok"] for x in checks),
           "hashes": {"zip": zip_sha, "dist_html": dist_sha, "levels": levels_sha,
                      "html_bytes": DIST_HTML.stat().st_size, "zip_bytes": ZIP.stat().st_size},
           "zip_entries": names, "zip_root_entries": roots,
           "measured_solutions": meas_sol, "doc_solutions": doc_sol}
    (ROOT / "verification" / "out_t11_release.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print("T11 发布包/文档核对：%d/%d 通过" % (sum(1 for x in checks if x["ok"]), len(checks)))
    print("ZIP sha256 = %s" % zip_sha)
    print("JSON -> verification/out_t11_release.json")


if __name__ == "__main__":
    main()