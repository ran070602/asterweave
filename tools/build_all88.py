#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 tools/constellations88.json —— 全天 88 个星座的构建期数据。

数据源（本机直连外网不通，统一走 https://ghproxy.net/ 代理前缀）：
  1. HYG v41 星表                hygdata_v41.csv
        - 赤经 ra(小时)/赤纬 dec(度)/视星等 mag/编号 bf/专名 proper/星座 con
  2. d3-celestial constellations.json        —— 英文名 name / 三字母 desig
  3. d3-celestial constellations.lines.json  —— 星座连线（映射到所选星 -> lines）
  4. d3-celestial constellations.borders.json —— 星座边界（-> neighbours + 面积排名 rank）

缓存放在系统临时目录 %TEMP%\\astro_cache\\（不进仓库）。每个 URL 最多重试 8 次
（指数退避 2s→60s），支持 Range 断点续传；校验失败则删档重下。

用法：
  python tools/build_all88.py                 # 生成 tools/constellations88.json
  python tools/build_all88.py --verify        # 只校验产物
  python tools/build_all88.py --group bf      # 用 bf 缩写归组中心（备选，见下）
  python tools/build_all88.py --rank d3       # 用 d3 的 rank 字段（备选，见下）

与任务书的偏差（均为数据源事实，非算法迁就）：
  * HYG v41 **有** con 列（119625/119626 行已填、恰好 88 个取值），且与 bf 缩写 100% 一致。
    任务书假设"HYG 没有星座归属列"，故默认按 con 归组（= "该星座所有 HYG 星"）。
    --group bf 可切回"只用带编号的星归组"，供对比。
  * d3-celestial 的 properties.rank **不是面积排名**：88 个 feature 只有 1/2/3 三个取值
    （显示优先级）。故 rank 默认由 borders.json 的边界多边形**实算球面面积**再排名
    （自检：88 星座面积和 = 41253 平方度）。--rank d3 可切回那个三值字段。
  * d3 的 name 有 3 处与权威英译名不符（Boötes / Corona Austrina / Serpens Cauda），
    d3 的 zh 是繁体且多处别名，故 zh/en 一律取任务书给的权威名单。
"""
import argparse
import ast
import collections
import csv
import json
import math
import os
import re
import ssl
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "tools", "constellations88.json")
RAW_SRC = os.path.join(ROOT, "tools", "build_sky.py")
CACHE = os.path.join(tempfile.gettempdir(), "astro_cache")

PROXY = "https://ghproxy.net/"
BASE = PROXY + "https://raw.githubusercontent.com/"
URLS = {
    "hygdata_v41.csv": BASE + "astronexus/HYG-Database/main/hyg/CURRENT/hygdata_v41.csv",
    "constellations.json": BASE + "ofrohn/d3-celestial/master/data/constellations.json",
    "constellations.lines.json": BASE + "ofrohn/d3-celestial/master/data/constellations.lines.json",
    "constellations.borders.json": BASE + "ofrohn/d3-celestial/master/data/constellations.borders.json",
}

# 权威名单（任务书给定，88 条）：(中文名, 英文名, 三字母缩写)
AUTH = [
    ("仙女座", "Andromeda", "And"), ("唧筒座", "Antlia", "Ant"), ("天燕座", "Apus", "Aps"),
    ("宝瓶座", "Aquarius", "Aqr"), ("天鹰座", "Aquila", "Aql"), ("天坛座", "Ara", "Ara"),
    ("白羊座", "Aries", "Ari"), ("御夫座", "Auriga", "Aur"), ("牧夫座", "Bootes", "Boo"),
    ("雕具座", "Caelum", "Cae"), ("鹿豹座", "Camelopardalis", "Cam"), ("巨蟹座", "Cancer", "Cnc"),
    ("猎犬座", "Canes Venatici", "CVn"), ("大犬座", "Canis Major", "CMa"),
    ("小犬座", "Canis Minor", "CMi"), ("摩羯座", "Capricornus", "Cap"),
    ("船底座", "Carina", "Car"), ("仙后座", "Cassiopeia", "Cas"),
    ("半人马座", "Centaurus", "Cen"), ("仙王座", "Cepheus", "Cep"), ("鲸鱼座", "Cetus", "Cet"),
    ("蝘蜓座", "Chamaeleon", "Cha"), ("圆规座", "Circinus", "Cir"), ("天鸽座", "Columba", "Col"),
    ("后发座", "Coma Berenices", "Com"), ("南冕座", "Corona Australis", "CrA"),
    ("北冕座", "Corona Borealis", "CrB"), ("乌鸦座", "Corvus", "Crv"),
    ("巨爵座", "Crater", "Crt"), ("南十字座", "Crux", "Cru"), ("天鹅座", "Cygnus", "Cyg"),
    ("海豚座", "Delphinus", "Del"), ("剑鱼座", "Dorado", "Dor"), ("天龙座", "Draco", "Dra"),
    ("小马座", "Equuleus", "Equ"), ("波江座", "Eridanus", "Eri"), ("天炉座", "Fornax", "For"),
    ("双子座", "Gemini", "Gem"), ("天鹤座", "Grus", "Gru"), ("武仙座", "Hercules", "Her"),
    ("时钟座", "Horologium", "Hor"), ("长蛇座", "Hydra", "Hya"), ("水蛇座", "Hydrus", "Hyi"),
    ("印第安座", "Indus", "Ind"), ("蝎虎座", "Lacerta", "Lac"), ("狮子座", "Leo", "Leo"),
    ("小狮座", "Leo Minor", "LMi"), ("天兔座", "Lepus", "Lep"), ("天秤座", "Libra", "Lib"),
    ("豺狼座", "Lupus", "Lup"), ("天猫座", "Lynx", "Lyn"), ("天琴座", "Lyra", "Lyr"),
    ("山案座", "Mensa", "Men"), ("显微镜座", "Microscopium", "Mic"),
    ("麒麟座", "Monoceros", "Mon"), ("苍蝇座", "Musca", "Mus"), ("矩尺座", "Norma", "Nor"),
    ("南极座", "Octans", "Oct"), ("蛇夫座", "Ophiuchus", "Oph"), ("猎户座", "Orion", "Ori"),
    ("孔雀座", "Pavo", "Pav"), ("飞马座", "Pegasus", "Peg"), ("英仙座", "Perseus", "Per"),
    ("凤凰座", "Phoenix", "Phe"), ("绘架座", "Pictor", "Pic"), ("双鱼座", "Pisces", "Psc"),
    ("南鱼座", "Piscis Austrinus", "PsA"), ("船尾座", "Puppis", "Pup"),
    ("罗盘座", "Pyxis", "Pyx"), ("网罟座", "Reticulum", "Ret"), ("天箭座", "Sagitta", "Sge"),
    ("人马座", "Sagittarius", "Sgr"), ("天蝎座", "Scorpius", "Sco"),
    ("玉夫座", "Sculptor", "Scl"), ("盾牌座", "Scutum", "Sct"), ("巨蛇座", "Serpens", "Ser"),
    ("六分仪座", "Sextans", "Sex"), ("金牛座", "Taurus", "Tau"),
    ("望远镜座", "Telescopium", "Tel"), ("三角座", "Triangulum", "Tri"),
    ("南三角座", "Triangulum Australe", "TrA"), ("杜鹃座", "Tucana", "Tuc"),
    ("大熊座", "Ursa Major", "UMa"), ("小熊座", "Ursa Minor", "UMi"), ("船帆座", "Vela", "Vel"),
    ("室女座", "Virgo", "Vir"), ("飞鱼座", "Volans", "Vol"), ("狐狸座", "Vulpecula", "Vul"),
]
assert len(AUTH) == 88 and len({a[2] for a in AUTH}) == 88, "权威名单必须是 88 条且缩写唯一"

# ---------------------------------------------------------------------------
# 星名：拜耳编号 -> 希腊字母
# ---------------------------------------------------------------------------
BAYER_FULL = {
    "Alp": "Alpha", "Bet": "Beta", "Gam": "Gamma", "Del": "Delta", "Eps": "Epsilon",
    "Zet": "Zeta", "Eta": "Eta", "The": "Theta", "Iot": "Iota", "Kap": "Kappa",
    "Lam": "Lambda", "Mu": "Mu", "Nu": "Nu", "Xi": "Xi", "Omi": "Omicron", "Pi": "Pi",
    "Rho": "Rho", "Sig": "Sigma", "Tau": "Tau", "Ups": "Upsilon", "Phi": "Phi",
    "Chi": "Chi", "Psi": "Psi", "Ome": "Omega",
}
BAYER_CHAR = {
    "Alp": "α", "Bet": "β", "Gam": "γ", "Del": "δ", "Eps": "ε", "Zet": "ζ", "Eta": "η",
    "The": "θ", "Iot": "ι", "Kap": "κ", "Lam": "λ", "Mu": "μ", "Nu": "ν", "Xi": "ξ",
    "Omi": "ο", "Pi": "π", "Rho": "ρ", "Sig": "σ", "Tau": "τ", "Ups": "υ", "Phi": "φ",
    "Chi": "χ", "Psi": "ψ", "Ome": "ω",
}
SUP = {"1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"}
BAYER_RE = re.compile(r"^(?P<flam>\d+)?(?P<bayer>%s)?(?P<sup>\d)?(?P<con>[A-Z][a-zA-Z]{2})$"
                      % ("(?:" + "|".join(BAYER_FULL) + ")"))
CONS = {a[2] for a in AUTH}

# ---------------------------------------------------------------------------
# fact：一句中文科普（20–40 字）。orig=命名/神话由来；obj=著名天体（可空）
# ---------------------------------------------------------------------------
FACTS = {
    "And": ("希腊神话中的公主星座", "仙女座大星系"),
    "Ant": ("拉卡伊命名的南天小星座", None),
    "Aps": ("普朗修斯命名的南天星座", None),
    "Aqr": ("黄道十二星座中的宝瓶", "螺旋星云"),
    "Aql": ("希腊神话中宙斯的神鹰", None),
    "Ara": ("希腊神话中的祭坛", None),
    "Ari": ("黄道十二星座中的金羊", None),
    "Aur": ("希腊神话中的御者", None),
    "Boo": ("希腊神话中的牧人", "牧夫座空洞"),
    "Cae": ("拉卡伊命名的南天小星座", None),
    "Cam": ("普朗修斯命名的北天星座", None),
    "Cnc": ("黄道十二星座中的巨蟹", "鬼宿星团"),
    "CVn": ("赫维留命名的猎犬星座", "涡状星系"),
    "CMa": ("希腊神话中猎户的猎犬", None),
    "CMi": ("希腊神话中的小猎犬", None),
    "Cap": ("黄道十二星座中的海山羊", None),
    "Car": ("南船座拆分出的船底", "船底座大星云"),
    "Cas": ("希腊神话中的王后", "仙后座A射电源"),
    "Cen": ("希腊神话中的马人", "半人马ω星团"),
    "Cep": ("希腊神话中的国王", "造父变星的原型星"),
    "Cet": ("希腊神话中的海怪", None),
    "Cha": ("普朗修斯命名的南天星座", None),
    "Cir": ("拉卡伊命名的南天小星座", None),
    "Col": ("普朗修斯命名的天鸽", None),
    "Com": ("希腊神话中王后的长发", "后发座星系团"),
    "CrA": ("托勒密记载的南天王冠", None),
    "CrB": ("希腊神话中的王冠", None),
    "Crv": ("希腊神话中阿波罗的乌鸦", None),
    "Crt": ("希腊神话中的酒杯", None),
    "Cru": ("南天著名的十字星座", "煤袋星云"),
    "Cyg": ("希腊神话中的天鹅", "天鹅座X-1"),
    "Del": ("希腊神话中的海豚", None),
    "Dor": ("普朗修斯命名的南天星座", "大麦哲伦云"),
    "Dra": ("希腊神话中的巨龙", None),
    "Equ": ("希腊神话中的小马", None),
    "Eri": ("希腊神话中的天河", None),
    "For": ("拉卡伊命名的南天小星座", "天炉座矮星系"),
    "Gem": ("黄道十二星座中的双生子", "双子座流星雨"),
    "Gru": ("普朗修斯命名的南天星座", None),
    "Her": ("希腊神话中的大力士", "武仙座球状星团"),
    "Hor": ("拉卡伊命名的南天小星座", None),
    "Hya": ("希腊神话中的水蛇", None),
    "Hyi": ("普朗修斯命名的南天星座", None),
    "Ind": ("普朗修斯命名的南天星座", None),
    "Lac": ("赫维留命名的北天星座", None),
    "Leo": ("黄道十二星座中的雄狮", None),
    "LMi": ("赫维留命名的北天小星座", None),
    "Lep": ("托勒密记载的南天兔子", None),
    "Lib": ("黄道十二星座中的天秤", None),
    "Lup": ("托勒密记载的南天野兽", None),
    "Lyn": ("赫维留命名的北天星座", None),
    "Lyr": ("希腊神话中俄耳甫斯的竖琴", "环状星云"),
    "Men": ("拉卡伊命名的南天小星座", None),
    "Mic": ("拉卡伊命名的南天小星座", None),
    "Mon": ("普朗修斯命名的麒麟", "玫瑰星云"),
    "Mus": ("普朗修斯命名的南天星座", None),
    "Nor": ("拉卡伊命名的南天小星座", None),
    "Oct": ("拉卡伊命名的南天小星座", "南天极"),
    "Oph": ("希腊神话中的医神", "巴纳德星"),
    "Ori": ("希腊神话中的猎人", "猎户座大星云"),
    "Pav": ("普朗修斯命名的南天星座", None),
    "Peg": ("希腊神话中的飞马", "飞马座大四边形"),
    "Per": ("希腊神话中的英雄珀耳修斯", "英仙座流星雨"),
    "Phe": ("普朗修斯命名的凤凰", None),
    "Pic": ("拉卡伊命名的南天小星座", None),
    "Psc": ("黄道十二星座中的双鱼", None),
    "PsA": ("托勒密记载的南天鱼", None),
    "Pup": ("南船座拆分出的船尾", None),
    "Pyx": ("拉卡伊命名的南天小星座", None),
    "Ret": ("拉卡伊命名的南天小星座", None),
    "Sge": ("托勒密记载的南天箭", None),
    "Sgr": ("黄道十二星座中的射手", "礁湖星云"),
    "Sco": ("黄道十二星座中的天蝎", None),
    "Scl": ("拉卡伊命名的南天小星座", "玉夫座星系"),
    "Sct": ("赫维留命名的盾牌星座", "野鸭星团"),
    "Ser": ("希腊神话中的巨蛇", "鹰状星云"),
    "Sex": ("赫维留命名的六分仪星座", None),
    "Tau": ("黄道十二星座中的公牛", "昴星团"),
    "Tel": ("拉卡伊命名的南天小星座", None),
    "Tri": ("托勒密记载的三角星座", "三角座星系"),
    "TrA": ("普朗修斯命名的南天三角", None),
    "Tuc": ("普朗修斯命名的南天星座", "小麦哲伦云"),
    "UMa": ("希腊神话中的大熊", "北斗七星"),
    "UMi": ("希腊神话中的小熊", None),
    "Vel": ("南船座拆分出的船帆", None),
    "Vir": ("黄道十二星座中的丰收女神", "室女座星系团"),
    "Vol": ("普朗修斯命名的南天星座", None),
    "Vul": ("赫维留命名的北天小星座", "哑铃星云"),
}
assert set(FACTS) == CONS, "FACTS 必须覆盖全部 88 个缩写"

SQDEG = (180.0 / math.pi) ** 2          # 1 球面度 = 3282.8 平方度
SPHERE = 4 * math.pi * SQDEG            # 41252.96 平方度


# ---------------------------------------------------------------------------
# 下载
# ---------------------------------------------------------------------------
def _validate(name, path):
    """校验缓存文件完整性；返回 (ok, 说明)。"""
    if not os.path.exists(path):
        return False, "文件不存在"
    size = os.path.getsize(path)
    if name == "hygdata_v41.csv":
        if size < 30_000_000:
            return False, "仅 %d 字节" % size
        with open(path, encoding="utf-8", newline="") as f:
            head = f.readline()
        if not head.startswith('"id","hip","hd"'):
            return False, "表头异常"
        return True, "%d 字节" % size
    if size < 5_000:
        return False, "仅 %d 字节" % size
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:                                    # noqa: BLE001
        return False, "JSON 解析失败: %s" % e
    n = len(d.get("features", []))
    want = {"constellations.json": 88, "constellations.lines.json": 88,
            "constellations.borders.json": 250}
    if n < want[name]:
        return False, "features=%d < %d" % (n, want[name])
    return True, "%d 字节, features=%d" % (size, n)


def fetch(name, url, max_retries=8, log=print):
    """带重试/指数退避/Range 续传的下载。返回 (ok, 尝试次数, 说明)。"""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    ok, why = _validate(name, path)
    if ok:
        log("  [%s] 缓存命中（%s）" % (name, why))
        return True, 0, why
    last = ""
    for attempt in range(1, max_retries + 1):
        try:
            existing = os.path.getsize(path) if os.path.exists(path) else 0
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
            if existing:
                headers["Range"] = "bytes=%d-" % existing
            resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=180)
            status = resp.status
            total = None
            cr = resp.headers.get("Content-Range")
            if cr and "/" in cr:
                total = int(cr.rsplit("/", 1)[1])
            if status == 200:
                if existing:
                    log("  [%s] 服务端忽略 Range，从头重下" % name)
                    existing = 0
                mode = "wb"
                if resp.headers.get("Content-Length"):
                    total = int(resp.headers["Content-Length"])
            elif status == 206:
                mode = "ab"
            else:
                raise IOError("HTTP %s" % status)
            with open(path, mode) as f:
                while True:
                    chunk = resp.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            resp.close()
            size = os.path.getsize(path)
            if total is not None and size != total:
                raise IOError("传输不完整：%d/%d 字节" % (size, total))
            ok, why = _validate(name, path)
            if not ok:
                raise IOError("校验失败：%s" % why)
            log("  [%s] 下载成功（第 %d 次尝试，%s）" % (name, attempt, why))
            return True, attempt, why
        except Exception as e:                                # noqa: BLE001
            last = "%s: %s" % (type(e).__name__, e)
            if os.path.exists(path):                          # 坏档一律删掉重下，避免 416 死循环
                try:
                    os.remove(path)
                except OSError:
                    pass
            wait = min(2 ** attempt, 60)
            log("  [%s] 第 %d/%d 次失败：%s；%ds 后重试" % (name, attempt, max_retries, last, wait))
            if attempt < max_retries:
                time.sleep(wait)
    log("  [%s] !! 放弃：%s" % (name, last))
    return False, max_retries, last


# ---------------------------------------------------------------------------
# 几何
# ---------------------------------------------------------------------------
def unit(ra_h, dec_deg):
    ra, dec = math.radians(ra_h * 15.0), math.radians(dec_deg)
    return (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))


def sep_deg(a, b):
    d = max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b))))
    return math.degrees(math.acos(d))


def ra_span_h(ras):
    """赤经跨度（小时，环形）。"""
    if len(ras) < 2:
        return 0.0
    s = sorted(ras)
    gaps = [(s[(i + 1) % len(s)] - s[i]) % 24.0 for i in range(len(s))]
    return 24.0 - max(gaps)


def unwrap_ra(ring):
    """把跨 ±180° 的环解开成连续经度（否则球面面积公式会算错）。"""
    out = [ring[0]]
    off = 0.0
    for i in range(1, len(ring)):
        d = ring[i][0] - ring[i - 1][0]
        if d > 180:
            off -= 360
        elif d < -180:
            off += 360
        out.append((ring[i][0] + off, ring[i][1]))
    d = ring[0][0] - ring[-1][0]
    if d > 180:
        off -= 360
    elif d < -180:
        off += 360
    out.append((ring[0][0] + off, ring[0][1]))
    return out


def ring_area_deg2(ring):
    """环的球面面积（平方度）。(λ, sinφ) 是等面积投影，IAU 边界为等赤经/赤纬线，
    在该平面内是直线，故鞋带公式精确。"""
    ur = unwrap_ra(ring)
    a = 0.0
    for i in range(len(ur) - 1):
        x1, y1 = ur[i]
        x2, y2 = ur[i + 1]
        a += (x2 - x1) * (math.sin(math.radians(y1)) + math.sin(math.radians(y2)))
    a = abs(a) / 2.0 * (math.pi / 180.0)          # 平方度 -> 球面度
    # 环极（把极点圈在里面）的环绕柱面一圈，鞋带给的是"半球 − 真实面积"，
    # 需翻回来。正常星座最大 1302 平方度 ≈ 0.40 sr，判据 π/2 sr 非常安全。
    if a > math.pi / 2:
        a = 2 * math.pi - a
    return a * SQDEG


def _bearing(node, toward):
    u = unit(node[0] / 15.0, node[1])
    e1 = (u[1], -u[0], 0.0)
    n1 = math.hypot(*e1)
    if n1 < 1e-12:
        e1 = (1.0, 0.0, 0.0)
    else:
        e1 = (e1[0] / n1, e1[1] / n1, e1[2] / n1)
    e2 = (u[1] * e1[2] - u[2] * e1[1], u[2] * e1[0] - u[0] * e1[2], u[0] * e1[1] - u[1] * e1[0])
    v = unit(toward[0] / 15.0, toward[1])
    d = (v[0] - u[0], v[1] - u[1], v[2] - u[2])
    dd = sum(x * y for x, y in zip(d, u))
    d = (d[0] - dd * u[0], d[1] - dd * u[1], d[2] - dd * u[2])
    return math.atan2(sum(x * y for x, y in zip(d, e2)), sum(x * y for x, y in zip(d, e1))) \
        % (2 * math.pi)


# ---------------------------------------------------------------------------
# borders.json -> neighbours + 面积排名
# ---------------------------------------------------------------------------
def derive_borders(path, log=print):
    d = json.load(open(path, encoding="utf-8"))
    edges = []
    for f in d["features"]:
        ids = tuple(sorted(x.strip() for x in f["ids"].split(",")))
        for line in f["geometry"]["coordinates"]:
            edges.append((ids, [(round(float(p[0]), 4), round(float(p[1]), 4)) for p in line]))

    inc = collections.defaultdict(list)
    for ei, (ids, pts) in enumerate(edges):
        inc[pts[0]].append((ei, +1))
        inc[pts[-1]].append((ei, -1))

    visited, faces = set(), []
    for ei0 in range(len(edges)):
        for sgn0 in (+1, -1):
            if (ei0, sgn0) in visited:
                continue
            ring, used, cur = [], set(), (ei0, sgn0)
            while cur not in visited:
                ei, sgn = cur
                visited.add(cur)
                used.add(ei)
                pts = edges[ei][1]
                p = pts if sgn > 0 else pts[::-1]
                ring.extend(p[:-1])
                node, prev = p[-1], p[-2]
                back, best = _bearing(node, prev), None
                for ej, sj in inc[node]:
                    q = edges[ej][1]
                    nxt = q[1] if sj > 0 else q[-2]
                    delta = (back - _bearing(node, nxt)) % (2 * math.pi)
                    if delta <= 1e-12:
                        delta = 2 * math.pi
                    if best is None or delta < best[0]:
                        best = (delta, (ej, sj))
                if best is None:
                    break
                cur = best[1]
            if len(ring) >= 3:
                common = None
                for ei in used:
                    s = set(edges[ei][0])
                    common = s if common is None else (common & s)
                faces.append((ring, sorted(common) if common else []))

    area = collections.defaultdict(float)
    for ring, lab in faces:
        if len(lab) != 1:
            log("  !! 边界环标签异常：%s" % lab)
            continue
        area[lab[0]] += ring_area_deg2(ring)

    nb = collections.defaultdict(set)
    for ids, _ in edges:
        if len(ids) == 2:
            nb[ids[0]].add(ids[1])
            nb[ids[1]].add(ids[0])

    order = sorted(area, key=lambda c: (-area[c], c))
    rank = {c: i + 1 for i, c in enumerate(order)}
    log("  边界：%d 条线段 -> %d 个面（%d 个星座，Serpens 分 2 片）"
        % (len(edges), len(faces), len(area)))
    log("  面积总和 %.1f 平方度（整球 %.1f，误差 %.3f%%）"
        % (sum(area.values()), SPHERE, abs(sum(area.values()) - SPHERE) / SPHERE * 100))
    return rank, dict(area), {k: sorted(v) for k, v in nb.items()}, len(faces)


# ---------------------------------------------------------------------------
# HYG
# ---------------------------------------------------------------------------
def load_hyg(path):
    """返回 (按 con 归组的星表, 统计)。每条星：dict(raH, decDeg, mag, bayer, sup, flam, proper)。"""
    by_con = collections.defaultdict(list)
    unnamed = 0
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            con = (row.get("con") or "").strip()
            if con not in CONS:
                continue
            try:
                mag = float(row["mag"]), float(row["ra"]), float(row["dec"])
            except (TypeError, ValueError):
                continue
            mag, ra, dec = mag
            rec = {"raH": ra % 24.0, "decDeg": dec, "mag": mag,
                   "proper": (row.get("proper") or "").strip()}
            bf = (row.get("bf") or "").strip()
            m = BAYER_RE.match(bf.replace(" ", "")) if bf else None
            if m and (m.group("bayer") or m.group("flam")):
                rec["bayer"], rec["sup"], rec["flam"] = \
                    m.group("bayer"), m.group("sup"), m.group("flam")
            else:
                if bf:
                    unnamed += 1
                rec["bayer"] = rec["sup"] = rec["flam"] = None
            by_con[con].append(rec)
    return by_con, unnamed


def bf_group(by_con):
    """--group bf：只按带编号的星归组（任务书原方案）。"""
    out = collections.defaultdict(list)
    for con, stars in by_con.items():
        for s in stars:
            if s["bayer"] or s["flam"]:
                out[con].append(s)
    return out


def centroid(stars):
    """质心：赤经用圆均值，赤纬用算术均值。"""
    if not stars:
        return None, None
    x = sum(math.cos(math.radians(s["raH"] * 15.0)) for s in stars)
    y = sum(math.sin(math.radians(s["raH"] * 15.0)) for s in stars)
    ra = math.degrees(math.atan2(y, x)) % 360.0 / 15.0
    dec = sum(s["decDeg"] for s in stars) / len(stars)
    return ra, dec


def star_name(con_zh, desig, s):
    """(中文名, 英文名)。拜耳优先，其次弗兰斯蒂德编号式。"""
    base = con_zh[:-1] if con_zh.endswith("座") else con_zh
    if s["bayer"]:
        sup = SUP.get(s["sup"] or "", "")
        return base + BAYER_CHAR[s["bayer"]] + sup, "%s%s %s" % (BAYER_FULL[s["bayer"]], s["sup"] or "", desig)
    return "%s%s" % (base, s["flam"]), "%s %s" % (s["flam"], desig)


def pick_stars(con_zh, desig, stars):
    """按 mag 升序取前 4–7 颗（优先 6–7），去重后返回。"""
    seen, uniq = set(), []
    for s in sorted(stars, key=lambda x: (x["mag"], x["raH"])):
        if not (s["bayer"] or s["flam"]):
            continue
        key = (s["bayer"], s["sup"]) if s["bayer"] else (s["flam"],)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(s)
    sel = uniq[:7]
    out = []
    for s in sel:
        zh, en = star_name(con_zh, desig, s)
        out.append({"zh": zh, "en": en, "mag": round(s["mag"], 2),
                    "raH": round(s["raH"], 3), "decDeg": round(s["decDeg"], 3),
                    "_u": unit(s["raH"], s["decDeg"])})
    return out, len(uniq)


# ---------------------------------------------------------------------------
# lines
# ---------------------------------------------------------------------------
def fallback_chain(stars):
    """降级：以最亮星起，按最近邻把所选星串成链。"""
    n = len(stars)
    if n < 2:
        return []
    left = set(range(1, n))
    pairs, cur = [], 0
    while left:
        nxt = min(left, key=lambda j: sep_deg(stars[cur]["_u"], stars[j]["_u"]))
        pairs.append([cur, nxt])
        left.discard(nxt)
        cur = nxt
    return pairs


def map_lines(lines_json, stars_by_desig, tol_deg=1.0, max_pair_deg=30.0):
    """d3 连线顶点 -> 所选星下标；连不上的顶点丢掉，相邻已映射顶点连成边。"""
    src = collections.defaultdict(list)
    for f in lines_json["features"]:
        for line in f["geometry"]["coordinates"]:
            src[f["id"]].append(line)
    real, fallback, stats = {}, [], []
    for desig, stars in stars_by_desig.items():
        pairs, kept, dropped = set(), 0, 0
        for line in src.get(desig, []):
            idxs = []
            for ra_deg, dec in line:
                u = unit((ra_deg % 360.0) / 15.0, dec)
                best, bd = None, 1e9
                for i, s in enumerate(stars):
                    d = sep_deg(u, s["_u"])
                    if d < bd:
                        best, bd = i, d
                if bd <= tol_deg:
                    idxs.append(best)
                    kept += 1
                else:
                    dropped += 1
            for a, b in zip(idxs, idxs[1:]):
                if a == b:
                    continue
                if sep_deg(stars[a]["_u"], stars[b]["_u"]) > max_pair_deg:
                    continue
                pairs.add((min(a, b), max(a, b)))
        stats.append((desig, len(stars), kept, dropped, len(pairs)))
        if pairs:
            real[desig] = [list(p) for p in sorted(pairs)]
        else:
            fallback.append(desig)
    return real, fallback, stats


# ---------------------------------------------------------------------------
# RAW 对照
# ---------------------------------------------------------------------------
def load_raw():
    tree = ast.parse(open(RAW_SRC, encoding="utf-8").read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "RAW":
            return ast.literal_eval(node.value)
    raise RuntimeError("未在 %s 找到 RAW" % RAW_SRC)


def slug(en):
    s = unicodedata.normalize("NFKD", en)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def make_fact(desig, zh, brightest_zh):
    origin, obj = FACTS[desig]
    if obj:
        return "%s是%s，%s是它最亮的星，座内有%s。" % (zh, origin, brightest_zh, obj)
    return "%s是%s，%s是它最亮的星。" % (zh, origin, brightest_zh)


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def build(args):
    print("== 1/6 取数据（缓存目录 %s）" % CACHE)
    got, fetch_log = {}, {}
    for name, url in URLS.items():
        ok, tries, why = fetch(name, url, log=print)
        got[name] = ok
        fetch_log[name] = (tries, why)
    for name in ("hygdata_v41.csv", "constellations.json"):
        if not got[name]:
            print("!! 必需数据源 %s 不可用，退出" % name)
            return 2
    p = lambda n: os.path.join(CACHE, n)
    d3 = json.load(open(p("constellations.json"), encoding="utf-8"))
    d3_by = {f["id"]: f["properties"] for f in d3["features"]}
    lines_json = json.load(open(p("constellations.lines.json"), encoding="utf-8")) \
        if got["constellations.lines.json"] else None

    print("\n== 2/6 解析 HYG v41")
    by_con, unnamed_bf = load_hyg(p("hygdata_v41.csv"))
    print("  88 个星座共 %d 颗星；bf 有值但解析不出编号的 %d 条"
          % (sum(len(v) for v in by_con.values()), unnamed_bf))
    group = by_con if args.group == "con" else bf_group(by_con)

    print("\n== 3/6 边界 -> neighbours + 面积排名")
    rank, area, nb, nfaces = (None, None, None, 0)
    if got["constellations.borders.json"]:
        rank, area, nb, nfaces = derive_borders(p("constellations.borders.json"), log=print)
    else:
        print("  !! borders.json 不可用：neighbours=[] 且 rank 退化为 d3 三值字段")

    print("\n== 4/6 选星 + 连线")
    stars_by_desig, starwise = {}, {}
    for zh, en, desig in AUTH:
        stars, navail = pick_stars(zh, desig, by_con.get(desig, []))
        stars_by_desig[desig] = stars
        starwise[desig] = (navail, len(stars))
    real, fallback, lstats = ({}, [], [])
    if lines_json:
        real, fallback, lstats = map_lines(lines_json, stars_by_desig)

    print("\n== 5/6 组装产物")
    out = []
    for zh, en, desig in AUTH:
        stars = stars_by_desig[desig]
        cra, cdec = centroid(group.get(desig) or by_con.get(desig, []))
        if args.rank == "d3":
            rk = int(d3_by[desig]["rank"])
        else:
            rk = (rank or {}).get(desig)
        lines = real.get(desig) or fallback_chain(stars)
        neigh = sorted({name_of(x) for x in (nb or {}).get(desig, [])})
        out.append({
            "id": slug(en), "zh": zh, "en": en, "desig": desig, "rank": rk,
            "raH": round(cra, 3) if cra is not None else None,
            "decDeg": round(cdec, 3) if cdec is not None else None,
            "brightest": {"zh": stars[0]["zh"], "en": stars[0]["en"], "mag": stars[0]["mag"]},
            "stars": [{k: s[k] for k in ("zh", "en", "mag", "raH", "decDeg")} for s in stars],
            "lines": [list(x) for x in lines],
            "neighbours": neigh,
            "fact": make_fact(desig, zh, stars[0]["zh"]),
        })
    out.sort(key=lambda x: x["en"])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("  已写出 %s（%d 条，%d 字节）" % (OUT, len(out), os.path.getsize(OUT)))

    report(args, out, by_con, group, area, rank, nb, real, fallback, lstats,
           starwise, d3_by, fetch_log, nfaces, unnamed_bf)
    return 0


def name_of(desig):
    return EN_OF.get(desig, desig)


EN_OF = {a[2]: a[1] for a in AUTH}


def report(args, out, by_con, group, area, rank, nb, real, fallback, lstats,
           starwise, d3_by, fetch_log, nfaces, unnamed_bf):
    print("\n== 6/6 报告")
    print("\n-- 数据源 --")
    for n, (tries, why) in fetch_log.items():
        print("  %-28s %s（重试 %d 次）%s" % (n, "OK" if os.path.exists(os.path.join(CACHE, n)) else "FAIL", tries, why))
    print("  lines 来源：%s" % ("d3-celestial constellations.lines.json（真实）"
                                if real else "降级（无真实连线）"))
    print("  neighbours 来源：%s" % ("d3-celestial borders.json（真实边界，%d 个面）" % nfaces
                                     if nb else "无（borders 不可用）"))
    print("  rank 来源：%s" % ("borders.json 实算球面面积排名" if args.rank != "d3"
                                else "d3 properties.rank（仅 1/2/3 三档，非面积排名）"))
    if area and rank:
        top = sorted(area, key=lambda c: -area[c])[:3]
        bot = sorted(area, key=lambda c: -area[c])[-3:]
        print("  面积排名首尾：%s … %s"
              % ("，".join("%s(%.0f,#%d)" % (EN_OF[c], area[c], rank[c]) for c in top),
                 "，".join("%s(%.0f,#%d)" % (EN_OF[c], area[c], rank[c]) for c in bot)))

    print("\n-- 新增星座（原本不在 build_sky.py RAW 里的）--")
    raw = load_raw()
    have = {r[0] for r in raw}
    new = [x for x in out if x["id"] not in have]
    print("  共 %d 个：" % len(new))
    for i in range(0, len(new), 6):
        print("   " + "  ".join("%s(%s)" % (x["id"], x["zh"]) for x in new[i:i + 6]))

    print("\n-- lines 真实/降级 --")
    nreal = len(real)
    print("  真实连线 %d 个星座；降级最近邻链 %d 个：%s"
          % (nreal, len(fallback), " ".join(fallback) if fallback else "无"))
    if lstats:
        kept = sum(s[2] for s in lstats)
        dropped = sum(s[3] for s in lstats)
        print("  d3 连线顶点：映射上 %d 个，落在所选星之外丢弃 %d 个（容差 1.0°）"
              % (kept, dropped if kept or dropped else 0))
        thin = [(s[0], s[4]) for s in lstats if 0 < s[4] <= 1]
        if thin:
            print("  边数≤1（图很稀疏）：%s" % " ".join("%s:%d" % t for t in thin))

    print("\n-- 异常 --")
    few = [(d, n) for d, (navail, n) in sorted(starwise.items()) if n < 4]
    print("  stars 少于 4 颗：%s" % (few if few else "无"))
    six = sorted("%s:%d" % (d, n) for d, (navail, n) in starwise.items() if n < 7)
    print("  stars 不足 7 颗（候选不够）：%s" % (" ".join(six) if six else "无"))
    # 延展性
    bad_span = []
    for x in out:
        rs = [s["raH"] for s in x["stars"]]
        ds = [s["decDeg"] for s in x["stars"]]
        if ra_span_h(rs) < 0.4 and (max(ds) - min(ds)) < 8.0:
            bad_span.append((x["desig"], round(ra_span_h(rs), 2), round(max(ds) - min(ds), 1)))
    print("  延展不足（赤经跨度<0.4h 且 赤纬跨度<8°）：%s" % (bad_span if bad_span else "无"))
    # 最亮星与"编号星之外的真最亮星"是否一致
    off = []
    for x in out:
        allmag = min(s["mag"] for s in by_con.get(x["desig"], []))
        if x["brightest"]["mag"] - allmag > 0.5:
            off.append((x["desig"], x["brightest"]["mag"], round(allmag, 2)))
    print("  最亮星比该星座真最亮星暗 0.5 等以上（真最亮星无编号）：%s" % (off if off else "无"))
    bad_fact = [(x["desig"], len(x["fact"])) for x in out if not 20 <= len(x["fact"]) <= 40]
    print("  fact 字数不在 20–40：%s" % (bad_fact if bad_fact else "无"))
    print("  bf 有值但无编号的星：%d 条（未参与选星）" % unnamed_bf)

    print("\n-- 与 build_sky.py RAW（50 个）逐项对照 --")
    mine = {x["id"]: x for x in out}
    hdr = "%-16s %-7s %-5s %5s %5s %6s | %6s %6s %5s %5s | %6s %6s"
    print(hdr % ("id", "zh", "desig", "Rrank", "rank", "Δ", "RraH", "raH", "Δh", "Δdec", "Rmag", "mag"))
    nrank = ncen = nmag = 0
    cen_rows = []
    for sid, zh, en, latin, abbr, lvl, ra, dec, arank, bzh, ben, bmag, _n in raw:
        x = mine.get(sid)
        if x is None:
            print("  !! RAW 的 %s(%s) 不在产物里" % (sid, abbr))
            continue
        if x["desig"] != abbr:
            print("  !! desig 不一致：%s RAW=%s mine=%s" % (sid, abbr, x["desig"]))
        dra = (x["raH"] - ra + 12) % 24 - 12
        ddec = x["decDeg"] - dec
        dmag = x["brightest"]["mag"] - bmag
        rdiff = x["rank"] != arank
        cdiff = abs(dra) > 0.3 or abs(ddec) > 3.0
        mdiff = abs(dmag) > 0.1
        nrank += rdiff
        ncen += cdiff
        nmag += mdiff
        if rdiff or cdiff or mdiff:
            cen_rows.append((sid, zh, abbr, arank, x["rank"], rdiff, ra, x["raH"], dra, ddec,
                             bmag, x["brightest"]["mag"], mdiff))
        print(hdr % (sid, zh, abbr, arank, x["rank"], ("%+d" % (x["rank"] - arank)) if x["rank"] else "NA",
                     "%.2f" % ra, "%.3f" % x["raH"], "%+.2f" % dra, "%+.2f" % ddec,
                     "%.2f" % bmag, "%.2f" % x["brightest"]["mag"]))
    print("\n  汇总：50 个中 rank 不一致 %d 个、中心差 >0.3h 或 >3° %d 个、最亮星 mag 差 >0.1 有 %d 个"
          % (nrank, ncen, nmag))
    if cen_rows:
        print("  差异清单（rank / 中心 / mag）：")
        for sid, zh, abbr, ar, mr, rd, ra, mra, dra, ddec, bm, mm, md in cen_rows:
            bits = []
            if rd:
                bits.append("rank %d→%d(%+d)" % (ar, mr, mr - ar))
            if abs(dra) > 0.3:
                bits.append("ΔraH %+.2f" % dra)
            if abs(ddec) > 3.0:
                bits.append("Δdec %+.2f" % ddec)
            if md:
                bits.append("mag %.2f→%.2f(%+.2f)" % (bm, mm, mm - bm))
            print("    %-16s %-7s %s" % (sid, zh, "，".join(bits)))
    # 名称一致性
    nm = [(sid, zh, en, x["zh"], x["en"]) for sid, zh, en, latin, abbr, lvl, *_ in raw
          for x in [mine[sid]] if x["zh"] != zh or x["en"] != en]
    print("  中/英文名与 RAW 不一致：%s" % (nm if nm else "无"))
    # d3 的三处别名
    alias = [(a[2], a[1], d3_by[a[2]]["name"]) for a in AUTH if d3_by[a[2]]["name"] != a[1]]
    print("  d3 的 name 与权威英译名不同：%s" % alias)

    if args.group == "bf":
        print("\n-- 归组方式对照（con vs bf）--")
        dif = []
        for zh, en, desig in AUTH:
            a = centroid(by_con.get(desig, []))
            b = centroid(bf_group(by_con).get(desig, []))
            if a[0] is None or b[0] is None:
                continue
            dra = (a[0] - b[0] + 12) % 24 - 12
            ddec = a[1] - b[1]
            if abs(dra) > 0.2 or abs(ddec) > 3.0:
                dif.append((desig, round(dra, 2), round(ddec, 1)))
        print("  两种归组中心差 >0.2h 或 >3° 的星座数：%d" % len(dif))
        print("  %s" % " ".join("%s(%+.2fh,%+.1f°)" % t for t in dif))


# ---------------------------------------------------------------------------
# 校验
# ---------------------------------------------------------------------------
def verify():
    data = json.load(open(OUT, encoding="utf-8"))
    errs = []

    def chk(c, msg):
        if not c:
            errs.append(msg)

    chk(len(data) == 88, "条目数 %d != 88" % len(data))
    chk(len({x["id"] for x in data}) == 88, "id 有重复")
    chk({x["zh"] for x in data} == {a[0] for a in AUTH}, "中文名集合与权威名单不一致")
    chk({x["desig"] for x in data} == CONS, "desig 集合与权威名单不一致")
    chk({x["en"] for x in data} == {a[1] for a in AUTH}, "英文名集合与权威名单不一致")
    chk(sorted(x["rank"] for x in data) == list(range(1, 89)), "rank 不是 1..88 的排列")
    ids = {x["en"] for x in data}
    for x in data:
        d, z = x["desig"], x["zh"]
        chk(4 <= len(x["stars"]) <= 7, "%s stars 数 %d" % (z, len(x["stars"])))
        mags = [s["mag"] for s in x["stars"]]
        chk(mags == sorted(mags), "%s stars mag 非单调" % z)
        chk(x["brightest"]["mag"] == mags[0] and x["brightest"]["zh"] == x["stars"][0]["zh"],
            "%s brightest 与 stars[0] 不一致" % z)
        chk(0 <= x["raH"] < 24, "%s raH=%s 越界" % (z, x["raH"]))
        chk(-90 <= x["decDeg"] <= 90, "%s decDeg=%s 越界" % (z, x["decDeg"]))
        for s in x["stars"]:
            chk(0 <= s["raH"] < 24 and -90 <= s["decDeg"] <= 90, "%s 星坐标越界 %s" % (z, s["en"]))
        chk(len({s["zh"] for s in x["stars"]}) == len(x["stars"]), "%s stars 中文名重复" % z)
        for a, b in x["lines"]:
            chk(isinstance(a, int) and isinstance(b, int), "%s lines 下标非整数" % z)
            chk(0 <= a < len(x["stars"]) and 0 <= b < len(x["stars"]), "%s lines 下标越界" % z)
            chk(a != b, "%s lines 自环" % z)
        chk(len({tuple(sorted(p)) for p in x["lines"]}) == len(x["lines"]), "%s lines 有重复边" % z)
        for n in x["neighbours"]:
            chk(n in ids, "%s 邻居 %s 不在 88 星座内" % (z, n))
            chk(n != x["en"], "%s 邻居含自身" % z)
        chk(20 <= len(x["fact"]) <= 40, "%s fact 字数 %d" % (z, len(x["fact"])))
        chk(x["id"] == slug(x["en"]), "%s id 与英文名不符" % z)
    # 邻居对称
    nbm = {x["en"]: set(x["neighbours"]) for x in data}
    for a, s in nbm.items():
        for b in s:
            chk(a in nbm[b], "邻居不对称：%s-%s" % (a, b))

    print("校验 %s：%d 条，%d 字节" % (OUT, len(data), os.path.getsize(OUT)))
    if errs:
        print("FAIL（%d 项）:" % len(errs))
        for e in errs[:60]:
            print("  -", e)
        return 1
    print("PASS：88 条 / stars 4–7 颗 / mag 单调 / lines 下标合法且无重复无自环 / "
          "raH∈[0,24) / decDeg∈[-90,90] / rank 为 1..88 排列 / 邻居对称且都在 88 内 / fact 20–40 字")
    return 0


def main():
    ap = argparse.ArgumentParser(description="生成 / 校验 tools/constellations88.json")
    ap.add_argument("--verify", action="store_true", help="只校验产物")
    ap.add_argument("--group", choices=("con", "bf"), default="con",
                    help="中心归组方式：con=HYG 星座列（默认），bf=编号里的缩写（任务书原方案）")
    ap.add_argument("--rank", choices=("area", "d3"), default="area",
                    help="rank 来源：area=边界实算面积排名（默认），d3=properties.rank")
    args = ap.parse_args()
    if args.verify:
        return verify()
    return build(args)


if __name__ == "__main__":
    try:
        ssl._create_default_https_context = ssl._create_unverified_context
    except Exception:                                          # noqa: BLE001
        pass
    sys.exit(main())
