#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T13 独立复核 · 发布包层：ZIP 根 index.html / ZIP 内容与 dist 逐字节一致 /
零外部引用 / build_manifest 全字段与实测一致（含 zip_sha256） / 确定性打包复现。
自写实现，不 import tools/build_release.py。
"""
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST_HTML = ROOT / "dist" / "冉政-游戏本体" / "index.html"
ZIP_PATH = ROOT / "冉政-游戏本体.zip"
MANIFEST = ROOT / "dist" / "build_manifest.json"
LEVELS = ROOT / "tools" / "levels.json"
GAME = ROOT / "game" / "index.html"

results = []


def check(cid, ok, detail):
    results.append({"id": cid, "ok": bool(ok), "detail": str(detail)})
    print(("[PASS] " if ok else "[FAIL] ") + cid + " :: " + str(detail))
    return bool(ok)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    html_bytes = DIST_HTML.read_bytes()
    zip_bytes = ZIP_PATH.read_bytes()
    levels = json.loads(LEVELS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    print("== 发布包层 ==")
    check("Z1 被复核 ZIP 存在", ZIP_PATH.is_file(), str(ZIP_PATH))
    check("Z1 dist HTML 字节数", len(html_bytes) == 48555, "实测 %d B" % len(html_bytes))

    # ---- ZIP 结构 ----
    zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
    names = zf.namelist()
    check("Z2 ZIP 根目录含 index.html（无目录前缀）", "index.html" in names,
          "namelist=%s" % names)
    check("Z2 ZIP 无目录条目", all(not n.endswith("/") for n in names), "namelist=%s" % names)
    entry = zf.read("index.html")
    check("Z3 ZIP 内 index.html 与 dist 版本 sha256 一致",
          sha(entry) == sha(html_bytes), "zip=%s dist=%s" % (sha(entry)[:16], sha(html_bytes)[:16]))
    check("Z3 ZIP 内 index.html 字节数一致", len(entry) == len(html_bytes),
          "zip=%d dist=%d" % (len(entry), len(html_bytes)))
    if "README.txt" in names:
        check("Z3 README.txt 存在且非空", len(zf.read("README.txt")) > 0,
              "%d B" % len(zf.read("README.txt")))

    # ---- 零外部引用 ----
    text = html_bytes.decode("utf-8")
    pats = ["http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket", "<img", "<link", "import("]
    for p in pats:
        n = text.count(p)
        check("Z4 零外部引用 %r" % p, n == 0, "出现次数=%d" % n)
    check("Z4 只有 1 段内联 <script> 且无 src",
          len(re.findall(r"<script\b[^>]*>", text)) == 1 and not re.search(r"<script[^>]*\bsrc=", text),
          "script 标签=%d" % len(re.findall(r"<script\b[^>]*>", text)))

    # ---- 构建可复现：dist == game 外壳 + levels.json 注入 ----
    block = ("/* LEVELS_INJECT_START */\n"
             "const LEVELS = " + json.dumps(levels, ensure_ascii=False, indent=2) + ";\n"
             "/* LEVELS_INJECT_END */")
    shell = GAME.read_text(encoding="utf-8")
    pat = re.compile(r"/\*\s*LEVELS_INJECT_START\s*\*/.*?/\*\s*LEVELS_INJECT_END\s*\*/", re.S)
    rebuilt = pat.sub(lambda m: block, shell, count=1)
    # build_release.py 在 Windows 上用默认文本模式写盘（\n -> \r\n），故复现字节时需做同样换行转换
    rebuilt_bytes = rebuilt.replace("\n", "\r\n").encode("utf-8")
    check("Z5 dist HTML == 当前 game 外壳 + 当前 levels.json 注入（逐字节可复现）",
          rebuilt_bytes == html_bytes,
          "rebuild=%s dist=%s" % (sha(rebuilt_bytes)[:16], sha(html_bytes)[:16]))

    # ---- 确定性打包复现（固定时间戳/属性，只有内容影响字节） ----
    buf = io.BytesIO()
    FIXED = (2026, 10, 21, 0, 0, 0)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("index.html", date_time=FIXED)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, html_bytes)
        if "README.txt" in names:
            zr = zipfile.ZipInfo("README.txt", date_time=FIXED)
            zr.compress_type = zipfile.ZIP_DEFLATED
            zr.external_attr = 0o644 << 16
            z.writestr(zr, zf.read("README.txt"))
    rebuilt_zip = buf.getvalue()
    check("Z6 确定性打包：同内容+固定元数据重打包，sha256 与实测 ZIP 一致",
          sha(rebuilt_zip) == sha(zip_bytes),
          "rebuild=%s actual=%s" % (sha(rebuilt_zip)[:16], sha(zip_bytes)[:16]))

    # ---- manifest 对账 ----
    check("Z7 manifest.level_count == 实测关数",
          manifest.get("level_count") == len(levels), "manifest=%s 实测=%d" %
          (manifest.get("level_count"), len(levels)))
    check("Z7 manifest.html_bytes == 实测 dist 字节数",
          manifest.get("html_bytes") == len(html_bytes),
          "manifest=%s 实测=%d" % (manifest.get("html_bytes"), len(html_bytes)))
    check("Z7 manifest.zip_bytes == 实测 ZIP 字节数",
          manifest.get("zip_bytes") == len(zip_bytes),
          "manifest=%s 实测=%d" % (manifest.get("zip_bytes"), len(zip_bytes)))
    check("Z7 manifest.build_sha256 == 实测 dist sha256",
          manifest.get("build_sha256") == sha(html_bytes),
          "manifest=%s 实测=%s" % (str(manifest.get("build_sha256"))[:16], sha(html_bytes)[:16]))
    check("Z7 manifest.zip_sha256 == 实测 ZIP sha256",
          manifest.get("zip_sha256") == sha(zip_bytes),
          "manifest=%s 实测=%s" % (str(manifest.get("zip_sha256"))[:16], sha(zip_bytes)[:16]))
    check("Z7 manifest.levels_sha256 == 实测 levels.json sha256",
          manifest.get("levels_sha256") == sha(LEVELS.read_bytes()),
          "manifest=%s 实测=%s" % (str(manifest.get("levels_sha256"))[:16], sha(LEVELS.read_bytes())[:16]))
    check("Z7 manifest.ui_sha256 == 实测 game/index.html sha256",
          manifest.get("ui_sha256") == sha(GAME.read_bytes()),
          "manifest=%s 实测=%s" % (str(manifest.get("ui_sha256"))[:16], sha(GAME.read_bytes())[:16]))
    check("Z7 manifest.zip_root_entries == 实测 namelist",
          manifest.get("zip_root_entries") == names,
          "manifest=%s 实测=%s" % (manifest.get("zip_root_entries"), names))
    checks = manifest.get("checks") or {}
    check("Z7 manifest.checks 全为 true",
          bool(checks) and all(bool(v) for v in checks.values()), json.dumps(checks, ensure_ascii=False))
    expected_checks = {"levels_roundtrip", "offline_selfcontained", "node_syntax",
                       "clue_selfconsistent", "zip_root_index"}
    check("Z7 manifest.checks 键齐全", expected_checks.issubset(set(checks.keys())),
          "keys=%s" % sorted(checks.keys()))
    check("Z7 manifest 路径字段指向真实文件",
          (ROOT / manifest.get("build_output", "")).is_file() and
          (ROOT / manifest.get("zip", "")).is_file(),
          json.dumps({"build_output": manifest.get("build_output"), "zip": manifest.get("zip")}))

    failed = [r for r in results if not r["ok"]]
    print("\n== Z 汇总：%d/%d 通过 ==" % (len(results) - len(failed), len(results)))
    out = {"zip": str(ZIP_PATH), "zip_sha256": sha(zip_bytes), "html_sha256": sha(html_bytes),
           "total_checks": len(results), "passed": len(results) - len(failed),
           "failed": [{"id": r["id"], "detail": r["detail"]} for r in failed], "results": results}
    (ROOT / "verification" / "t13_out_z.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("JSON -> verification/t13_out_z.json")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())