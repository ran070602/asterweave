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
    print(f"UI 外壳 {len(html)} 字节；关卡 {len(levels)} 关")

    # 1) 注入关卡块（只替换两个注释标记之间的内容）
    block = ("/* LEVELS_INJECT_START */\n"
             "const LEVELS = " + json.dumps(levels, ensure_ascii=False, indent=2) + ";\n"
             "/* LEVELS_INJECT_END */")
    pat = re.compile(r"/\* LEVELS_INJECT_START \*/.*?/\* LEVELS_INJECT_END \*/", re.S)
    if not pat.search(html):
        print("!! UI 外壳里找不到 LEVELS_INJECT 标记"); sys.exit(1)
    out_html = pat.sub(lambda m: block, html, count=1)
    # 标题里的关数由数据决定
    out_html = _retitle(out_html, len(levels))
    # 闸门：按钮监听必须在顶层（曾被误插进 resetBtn 回调）
    bad_bind = _check_bindings(out_html)
    if bad_bind:
        fail.append("按钮监听写进了别的回调里: " + ", ".join(bad_bind))

    # 1b) 注入图鉴数据
    sky_block = ("/* SKY_INJECT_START */\n"
                 "const SKY = " + json.dumps(sky, ensure_ascii=False, indent=2) + ";\n"
                 "/* SKY_INJECT_END */")
    sky_pat = re.compile(r"/\* SKY_INJECT_START \*/.*?/\* SKY_INJECT_END \*/", re.S)
    if not sky_pat.search(out_html):
        fail.append("UI 外壳里找不到 SKY_INJECT 标记")
    else:
        out_html = sky_pat.sub(lambda m: sky_block, out_html, count=1)
        m2 = re.search(r"/\* SKY_INJECT_START \*/\s*const SKY = (\[.*?\]);\s*/\* SKY_INJECT_END \*/", out_html, re.S)
        if not m2 or json.loads(m2.group(1)) != sky:
            fail.append("SKY 注入回读不一致")
        else:
            print("图鉴数据注入：通过（%d 个星座）" % len(sky))

    # 2) 回读校验：注入后的 LEVELS 必须与 levels.json 完全一致
    m = re.search(r"/\* LEVELS_INJECT_START \*/\s*const LEVELS = (\[.*?\]);\s*/\* LEVELS_INJECT_END \*/",
                  out_html, re.S)
    if not m or json.loads(m.group(1)) != levels:
        fail.append("注入回读不一致")
    else:
        print("注入回读校验：通过")

    # 3) 离线自包含校验
    hits = [p for p in ("http://", "https://", "fetch(", "XMLHttpRequest", "WebSocket",
                        "<img", "<link", "import(") if p in out_html]
    if hits:
        fail.append(f"存在外部引用 {hits}")
    else:
        print("离线自包含校验：通过（零外部引用）")

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
    open(out_path, "w", encoding="utf-8").write(out_html)
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
        "build_output": os.path.relpath(out_path, ROOT),
        "build_sha256": sha256_file(out_path),
        "zip": os.path.relpath(ZIP_PATH, ROOT),
        "zip_sha256": sha256_file(ZIP_PATH),
        "zip_bytes": os.path.getsize(ZIP_PATH),
        "html_bytes": os.path.getsize(out_path),
        "zip_root_entries": names,
        "checks": {"levels_roundtrip": True, "offline_selfcontained": True,
                   "node_syntax": node_ok, "clue_selfconsistent": True,
                   "zip_root_index": True},
    }
    json.dump(manifest, open(os.path.join(DIST, "build_manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"\n✅ 已产出 {os.path.relpath(out_path, ROOT)}（{manifest['html_bytes']} 字节）")
    print(f"✅ 已产出 {os.path.relpath(ZIP_PATH, ROOT)}（{manifest['zip_bytes']} 字节）")
    print(f"   关卡数 {len(levels)}｜UI sha256 {manifest['ui_sha256'][:12]}…")


if __name__ == "__main__":
    main()