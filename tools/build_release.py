#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T10 发布打包：把 UI 外壳（game/index.html）+ 关卡数据（tools/levels.json）
打成比赛要求的形式：

  dist/冉政-游戏本体/index.html      ← 单文件、自包含
  冉政-游戏本体.zip                   ← ZIP 根目录直接是 index.html（比赛要求）
  dist/build_manifest.json            ← 构建清单（输入 sha256 / 关数 / 体积），供迭代文档引用

用法： python tools/build_release.py
"""
import hashlib, json, os, re, shutil, subprocess, sys, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "game", "index.html")
LEVELS = os.path.join(ROOT, "tools", "levels.json")
SKY = os.path.join(ROOT, "tools", "sky.json")
DIST = os.path.join(ROOT, "dist")
PKG_DIR = os.path.join(DIST, "星织-游戏本体")
ZIP_PATH = os.path.join(ROOT, "星织-游戏本体.zip")
NODE = shutil.which("node") or r"D:\develop\NodeJS\node.exe"

fail = []


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


README_SRC = os.path.join(ROOT, "tools", "README_source.txt")


def _assert_consistency(out_path, zip_path, root_index, manifest):
    """硬断言：manifest 记录的三方 sha 必须与磁盘实测一致，否则构建失败。
    （复核曾遇到"复核窗口内被重建、zip 与 manifest 对不上"的情况，这里把一致性钉死在构建里。）"""
    bad = []

    def sha(p):
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 16), b""):
                h.update(b)
        return h.hexdigest()

    if manifest.get("build_sha256") != sha(out_path):
        bad.append("dist index.html sha 与 manifest 不一致")
    if manifest.get("zip_sha256") != sha(zip_path):
        bad.append("ZIP sha 与 manifest 不一致")
    if os.path.exists(root_index) and sha(root_index) != sha(out_path):
        bad.append("根目录 index.html 与 dist 不一致（Pages 会发旧版）")
    with zipfile.ZipFile(zip_path) as z:
        if hashlib.sha256(z.read("index.html")).hexdigest() != sha(out_path):
            bad.append("ZIP 内 index.html 与 dist 不一致")
        if z.namelist() != ["index.html", "README.txt"]:
            bad.append(f"ZIP 根目录条目异常: {z.namelist()}")
    return bad


def readme_text():
    """ZIP 里的 README.txt：源文件用 LF，打包时转 CRLF（Windows 记事本友好）"""
    with open(README_SRC, encoding="utf-8") as f:
        return f.read().replace("\n", "\r\n")


def _retitle(html, n):
    """标题里的关数由数据决定，避免文档/标题与实际关数不一致"""
    return re.sub(r"<title>[^<]*</title>", f"<title>星织 Asterweave · {n} 关</title>", html, count=1)


def _check_bindings(html):
    """闸门：交互按钮的 click 监听必须写在顶层（不得缩进进别的回调里）"""
    bad = []
    for m in re.finditer(r"^[ \t]+document\.getElementById\('(\w+)'\)\.addEventListener", html, re.M):
        bad.append(m.group(1))
    return bad


def main():
    if not os.path.exists(UI):
        print("!! 缺少 game/index.html"); sys.exit(1)
    html = open(UI, encoding="utf-8").read()
    levels = json.load(open(LEVELS, encoding="utf-8"))
    sky = json.load(open(SKY, encoding="utf-8"))
    # 意见箱：先离线生成二维码（内联 data URI），再读取配置注入
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_feedback.py")],
                   check=True, cwd=ROOT)
    fb = json.load(open(os.path.join(ROOT, "tools", "feedback_qr.json"), encoding="utf-8"))
    # 星名专名表（没有专名的暗星保留编号）
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "build_star_names.py")],
                   check=True, cwd=ROOT)
    proper = json.load(open(os.path.join(ROOT, "tools", "star_proper_names.json"), encoding="utf-8"))
    print(f"UI 外壳 {len(html)} 字节；关卡 {len(levels)} 关")

    # 1) 注入关卡块（只替换两个注释标记之间的内容）
    #    关卡数据改为紧凑编码（位图 + 常量池），运行期由 game/index.html 里的
    #    expandLevelsPacked() 展开；编码/解码等价性由 tools/compact_levels.py verify 保证。
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import compact_levels
    import compact_sky
    import json as _json
    block = compact_levels.build_block(levels)
    pat = re.compile(r"/\* LEVELS_INJECT_START \*/.*?/\* LEVELS_INJECT_END \*/", re.S)
    if not pat.search(html):
        print("!! UI 外壳里找不到 LEVELS_INJECT 标记"); sys.exit(1)
    out_html = pat.sub(lambda m: block, html, count=1)
    print("关卡块（紧凑编码 CONST + LEVELS_PACKED）：%d 字节（旧缩进 JSON 为 %d 字节）"
          % (len(block.encode("utf-8")), len(compact_levels.legacy_block(levels).encode("utf-8"))))
    # 标题里的关数由数据决定
    out_html = _retitle(out_html, len(levels))
    # 闸门：按钮监听必须在顶层（曾被误插进 resetBtn 回调）
    bad_bind = _check_bindings(out_html)
    if bad_bind:
        fail.append("按钮监听写进了别的回调里: " + ", ".join(bad_bind))

    # 1a2) 注入无尽题库（紧凑块，与关卡共享常量池）
    bank_path = os.path.join(ROOT, "tools", "endless_bank_packed.json")
    if os.path.exists(bank_path):
        _b = _json.load(open(bank_path, encoding="utf-8"))
        bank_block = ("/* BANK_INJECT_START */\n"
                      "const BANK_CONST_EXTRA = " + compact_levels.js_literal(_b["extra"]) + ";\n"
                      "const BANK_PACKED = " + compact_levels.js_literal(_b["packed"]) + ";\n"
                      "/* BANK_INJECT_END */")
        bank_pat = re.compile(r"/\* BANK_INJECT_START \*/.*?/\* BANK_INJECT_END \*/", re.S)
        if not bank_pat.search(out_html):
            fail.append("UI 外壳里找不到 BANK_INJECT 标记")
        else:
            out_html = bank_pat.sub(lambda _m: bank_block, out_html, count=1)
            print("无尽题库块：%d 题｜%d 字节（常量池复用关卡 %d 条 + extras %d 条）"
                  % (len(_b["packed"]), len(bank_block.encode("utf-8")),
                     len(_b["poolSize"]) if isinstance(_b.get("poolSize"), list) else 0,
                     len(_b["extra"])))

    # 1b) 注入图鉴数据
    #     也是紧凑编码：数据只存 id/中英拉丁缩写/赤经赤纬/面积排名/最亮星/相邻星座槽位；
    #     raText、decText、season、zone、level、neighbors 的 id/level/zh、inGameNeighbors
    #     全部在 game/index.html 的 expandSkyPacked() 里现算（level 由 LEVELS 反查，
    #     levels.json 改了运行期自动同步）。等价性由 tools/compact_sky.py verify 保证。
    try:
        sky_block = compact_sky.build_block(sky, levels)
    except Exception as exc:                       # noqa: BLE001 —— 构建期任何编码异常都必须让构建失败
        print("!! 图鉴紧凑编码失败：" + repr(exc))
        sys.exit(1)
    sky_pat = compact_sky.BLOCK_RE
    if not sky_pat.search(out_html):
        fail.append("UI 外壳里找不到 SKY_INJECT 标记")
    else:
        out_html = sky_pat.sub(lambda m: sky_block, out_html, count=1)
        print("图鉴块（紧凑编码 SKY_NB_EXTRA + SKY_PACKED）：%d 字节（旧缩进 JSON 为 %d 字节）"
              % (len(sky_block.encode("utf-8")), len(compact_sky.legacy_block(sky).encode("utf-8"))))

    # 1c) 注入意见箱（邮箱 / 内联二维码；二维码是 data URI，不产生外部引用）
    fb_block = ("/* FEEDBACK_INJECT_START */\n"
                "const FEEDBACK = " + json.dumps(fb, ensure_ascii=False) + ";\n"
                "/* FEEDBACK_INJECT_END */")
    fb_pat = re.compile(r"/\* FEEDBACK_INJECT_START \*/.*?/\* FEEDBACK_INJECT_END \*/", re.S)
    if not fb_pat.search(out_html):
        fail.append("UI 外壳里找不到 FEEDBACK_INJECT 标记")
    else:
        out_html = fb_pat.sub(lambda m: fb_block, out_html, count=1)
        qr = fb.get("qr", "")
        if qr and "data:image/png;base64," not in qr:
            fail.append("意见箱二维码不是内联 data URI")
        elif qr:
            print(f"意见箱注入：通过（内联二维码 {fb.get('modules', '?')}×{fb.get('modules', '?')} 模块，"
                  f"{len(qr)//1024} KB）")
        else:
            print(f"意见箱注入：通过（邮箱 {fb.get('show') or fb.get('email')}；未使用二维码）")

    # 1d) 注入星名专名表（海报标注优先用专名）
    pr_block = ("/* PROPER_INJECT_START */\n"
                "const PROPER_NAMES = " + json.dumps(proper, ensure_ascii=False) + ";\n"
                "/* PROPER_INJECT_END */")
    pr_pat = re.compile(r"/\* PROPER_INJECT_START \*/.*?/\* PROPER_INJECT_END \*/", re.S)
    if not pr_pat.search(out_html):
        fail.append("UI 外壳里找不到 PROPER_INJECT 标记")
    else:
        out_html = pr_pat.sub(lambda m: pr_block, out_html, count=1)
        print("星名专名表注入：通过（%d 条专名，其余用编号）" % len(proper))

    # 1z) 题库回读校验：从注入后的 HTML 取回 BANK 块 → 用「关卡池 + extras」展开 →
    #     与 tools/endless_bank_full.json（应用同一套传统星名）逐字段比较
    bm = re.search(r"/\* BANK_INJECT_START \*/(.*?)/\* BANK_INJECT_END \*/", out_html, re.S)
    if bm:
        try:
            txt = bm.group(1)
            extra_txt = re.search(r"BANK_CONST_EXTRA\s*=\s*(\[.*?\]);", txt, re.S).group(1)
            pack_txt = re.search(r"BANK_PACKED\s*=\s*(\[.*?\]);", txt, re.S).group(1)
            _bc = _json.loads(extra_txt)
            _bp = _json.loads(pack_txt)
            _lm = compact_levels.BLOCK_RE.search(out_html)
            _const, _ = compact_levels.decode_block(_lm.group(0)) if _lm else ([], [])
            _pool = list(_const) + list(_bc)
            _bank_back = compact_levels.unpack(_pool, _bp)
            _bank_src = _json.load(open(os.path.join(ROOT, "tools", "endless_bank_full.json"),
                                        encoding="utf-8"))
            sys.path.insert(0, os.path.join(ROOT, "tools"))
            from star_proper_zh import PROPER
            bank_bad = []
            for a, b in zip(_bank_src, _bank_back):
                for s in (a.get("theme") or {}).get("stars") or []:
                    nm = PROPER.get(s.get("en"))
                    if nm:
                        s["name"] = nm
                n = a["size"]
                # runs_from_mines 收的是**扁平格号**（i = r*n + c），不是 (r,c) 元组
                mine_set = {r * n + c for r, c in a["mines"]}
                b2 = dict(b)
                b2["rowRuns"] = [compact_levels.runs_from_mines(mine_set, n, True, r) for r in range(n)]
                b2["colRuns"] = [compact_levels.runs_from_mines(mine_set, n, False, c) for c in range(n)]
                compact_levels.deep_eq(a, b2, "bank[%s]" % a["id"], bank_bad)
            if bank_bad or len(_bank_back) != len(_bank_src):
                fail.append("题库块回读校验失败：%s" % (bank_bad[:3] or "条数 %d≠%d"
                            % (len(_bank_back), len(_bank_src))))
            else:
                print("无尽题库块回读校验：通过（%d 题逐字段等价）" % len(_bank_back))
        except Exception as e:
            fail.append("题库块回读校验异常：%s: %s" % (type(e).__name__, e))

    # 2) 回读校验：从**注入后的 HTML** 里取回紧凑块 → JSON 回读 → 按运行期同一套规则展开
    #    → 与 levels.json 逐字段等价（rowRuns/colRuns 不在数据里，按 startBoard 的现算规则补上后比较）
    expanded = None
    lm = compact_levels.BLOCK_RE.search(out_html)
    if not lm:
        fail.append("注入后的 HTML 里找不到 LEVELS_INJECT 块")
    else:
        try:
            _const, _packed = compact_levels.decode_block(lm.group(0))
            expanded = compact_levels.unpack(_const, _packed)
        except Exception as exc:                   # noqa: BLE001 —— 构建期任何解码异常都必须让构建失败
            fail.append("紧凑关卡块回读失败：" + repr(exc))
    if expanded is not None:
        if len(expanded) != len(levels):
            fail.append("紧凑关卡块关数不一致：%d != %d" % (len(expanded), len(levels)))
        deep_bad = []
        for a, b in zip(levels, expanded):
            n = b["size"]
            mine_set = set()
            for r, c in b["mines"]:
                mine_set.add(r * n + c)
            for r, c in b["noise"]:
                mine_set.add(r * n + c)
            b2 = dict(b)
            b2["rowRuns"] = [compact_levels.runs_from_mines(mine_set, n, True, r) for r in range(n)]
            b2["colRuns"] = [compact_levels.runs_from_mines(mine_set, n, False, c) for c in range(n)]
            compact_levels.deep_eq(a, b2, "level[%s]" % a["id"], deep_bad)
        if deep_bad:
            fail.append("紧凑关卡块展开后与 levels.json 不等：" + "; ".join(deep_bad[:6]))
        else:
            print("紧凑关卡块回读校验：通过（%d 关逐字段等价；rowRuns/colRuns 按现算规则补全）"
                  % len(expanded))

    # 2b) 回读校验：图鉴块 → JSON 回读 → 按 expandSkyPacked() 的同一套规则展开
    #     → 与 sky.json 逐字段等价（raText/decText/season/zone/level/相邻关系全是现算的）
    sky_expanded = None
    sm = compact_sky.BLOCK_RE.search(out_html)
    if not sm:
        fail.append("注入后的 HTML 里找不到 SKY_INJECT 块")
    else:
        try:
            _extra, _packed = compact_sky.decode_block(sm.group(0))
            sky_expanded = compact_sky.unpack(_extra, _packed, levels)
        except Exception as exc:                   # noqa: BLE001
            fail.append("紧凑图鉴块回读失败：" + repr(exc))
    if sky_expanded is not None:
        if len(sky_expanded) != len(sky):
            fail.append("紧凑图鉴块条数不一致：%d != %d" % (len(sky_expanded), len(sky)))
        sky_bad = []
        for a, b in zip(sky, sky_expanded):
            compact_sky.deep_eq(a, b, "sky[%s]" % a["id"], sky_bad)
        if sky_bad:
            fail.append("紧凑图鉴块展开后与 sky.json 不等：" + "; ".join(sky_bad[:6]))
        else:
            print("紧凑图鉴块回读校验：通过（%d 条星座逐字段等价；raText/decText/season/zone/"
                  "level/相邻关系现算）" % len(sky_expanded))

    # 3) 离线自包含校验
    #    意见箱配置块里可能出现邮箱/表单 URL（那是数据，不是资源引用），先剔除再扫；
    #    <img> 只允许内联 data URI。
    scan = fb_pat.sub("", out_html) if "fb_pat" in dir() else out_html
    hits = [p for p in ("http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket",
                        "<link", "import(") if p in scan]
    if hits:
        fail.append(f"存在外部引用 {hits}")
    bad_img = [m.group(0)[:60] for m in re.finditer(r"<img[^>]*>", out_html)
               if 'src="data:' not in m.group(0)]
    if bad_img:
        fail.append(f"存在非内联 <img>：{bad_img}")
    n_img = len(re.findall(r"<img[^>]*>", out_html))
    if not fail:
        print(f"离线自包含校验：通过（零外部引用；{n_img} 个 <img> 均为内联 data URI）")

    # 4) 脚本语法校验（node --check）
    scripts = re.findall(r"<script>(.*?)</script>", out_html, re.S)
    js_tmp = os.path.join(DIST, "_syntax_check.js")
    os.makedirs(DIST, exist_ok=True)
    open(js_tmp, "w", encoding="utf-8").write("\n".join(scripts))
    node_ok = None
    if os.path.exists(NODE):
        r = subprocess.run([NODE, "--check", js_tmp], capture_output=True, text=True)
        node_ok = (r.returncode == 0)
        if not node_ok:
            fail.append("node --check 失败：" + (r.stderr or r.stdout)[:400])
        else:
            print(f"JS 语法校验：通过（{len(scripts)} 段 <script>）")
    else:
        print("!! 未找到 node，跳过语法校验")
    os.remove(js_tmp)

    # 5) 线索自洽（独立复算，不信任生成器）
    def runs(bools):
        out, cur = [], 0
        for b in bools:
            if b:
                cur += 1
            elif cur:
                out.append(cur); cur = 0
        if cur:
            out.append(cur)
        return out

    for d in levels:
        n = d["size"]; mines = {tuple(x) for x in d["mines"]}
        exp_r = [runs([(r, c) in mines for c in range(n)]) for r in range(n)]
        exp_c = [runs([(r, c) in mines for r in range(n)]) for c in range(n)]
        if d["rowRuns"] != exp_r or d["colRuns"] != exp_c:
            fail.append(f"第{d['id']}关 行列线索与雷位置不一致")
        r0, c0 = d["opening"]
        if (r0, c0) in mines:
            fail.append(f"第{d['id']}关 开局格是雷")
    print("线索自洽校验：" + ("通过" if not fail else "不通过"))

    if fail:
        print("\n!! 构建失败：")
        for x in fail:
            print("   -", x)
        sys.exit(1)

    # 6) 落盘：dist 目录 + ZIP（根目录 index.html）
    shutil.rmtree(PKG_DIR, ignore_errors=True)
    os.makedirs(PKG_DIR, exist_ok=True)
    out_path = os.path.join(PKG_DIR, "index.html")
    open(out_path, "w", encoding="utf-8", newline="\n").write(out_html)
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)
    # 确定性打包：固定的时间戳与属性，使同样输入每次都产出**逐字节相同**的 ZIP
    # （否则仅时间戳变化就会让 sha256 每跑一次都不同，难以对账）。
    FIXED = (2026, 10, 21, 0, 0, 0)
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
        zi = zipfile.ZipInfo("index.html", date_time=FIXED)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, open(out_path, "rb").read())
        zr = zipfile.ZipInfo("README.txt", date_time=FIXED)
        zr.compress_type = zipfile.ZIP_DEFLATED
        zr.external_attr = 0o644 << 16
        zr = zr
        z.writestr(zr, readme_text())

    with zipfile.ZipFile(ZIP_PATH) as z:
        names = z.namelist()
    if "index.html" not in names:
        print("!! ZIP 根目录缺少 index.html"); sys.exit(1)
    print(f"ZIP 根目录条目：{names}")

    # 6.5) 同步仓库根目录的 index.html（GitHub Pages 用的发布副本）
    root_index = os.path.join(ROOT, "index.html")
    if os.path.exists(root_index):
        shutil.copyfile(out_path, root_index)
        print(f"已同步根目录 index.html（{os.path.getsize(root_index)} 字节，Pages 用）")

    manifest = {
        "ui_source": os.path.relpath(UI, ROOT),
        "ui_sha256": sha256_file(UI),
        "levels_source": os.path.relpath(LEVELS, ROOT),
        "levels_sha256": sha256_file(LEVELS),
        "level_count": len(levels),
        "sky_source": os.path.relpath(SKY, ROOT),
        "sky_sha256": sha256_file(SKY),
        "sky_count": len(sky),
        "build_output": os.path.relpath(out_path, ROOT),
        "build_sha256": sha256_file(out_path),
        "zip": os.path.relpath(ZIP_PATH, ROOT),
        "zip_sha256": sha256_file(ZIP_PATH),
        "zip_bytes": os.path.getsize(ZIP_PATH),
        "html_bytes": os.path.getsize(out_path),
        "zip_root_entries": names,
        "checks": {"levels_roundtrip": True, "sky_roundtrip": True, "offline_selfcontained": True,
                   "node_syntax": node_ok, "clue_selfconsistent": True,
                   "zip_root_index": True},
    }
    json.dump(manifest, open(os.path.join(DIST, "build_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    bad = _assert_consistency(out_path, ZIP_PATH, os.path.join(ROOT, "index.html"), manifest)
    if bad:
        print("\n!! 一致性断言失败：")
        for x in bad:
            print("   -", x)
        sys.exit(1)
    print("一致性断言：dist / ZIP / 根目录 / manifest 四方 sha 全一致")

    print(f"\n✅ 已产出 {os.path.relpath(out_path, ROOT)}（{manifest['html_bytes']} 字节）")
    print(f"✅ 已产出 {os.path.relpath(ZIP_PATH, ROOT)}（{manifest['zip_bytes']} 字节）")
    print(f"   关卡数 {len(levels)}｜UI sha256 {manifest['ui_sha256'][:12]}…")


if __name__ == "__main__":
    main()