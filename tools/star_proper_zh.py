# -*- coding: utf-8 -*-
"""知名恒星的传统中文名（只收录高置信度条目；未收录的沿用「星座名+拜耳字母」惯例，如「天炉α」）。

键：constellations88.json 里星星的英文名（"Alpha CMa" 这种）。
值：传统中文星名。
用途：tools/merge_levels_51_88.py（写关卡 theme.stars[].name / brightest）与 tools/extend_sky_88.py（写图鉴 brightest）。
"""

PROPER = {
    # 大犬座
    "Alpha CMa": "天狼", "Beta CMa": "军市一", "Gamma CMa": "弧矢一", "Epsilon CMa": "弧矢七",
    # 小犬座
    "Alpha CMi": "南河三", "Beta CMi": "南河二",
    # 金牛座
    "Alpha Tau": "毕宿五", "Beta Tau": "五车五", "Eta Tau": "天关", "Zeta Tau": "天关二",
    # 仙女座
    "Alpha And": "壁宿二", "Beta And": "奎宿九", "Gamma And": "天大将军一",
    # 猎犬座
    "Alpha CVn": "常陈一", "Beta CVn": "常陈四",
    # 海豚座（沿用现有数据表里的专名）
    "Alpha Del": "瓠瓜一", "Beta Del": "瓠瓜二", "Gamma Del": "瓠瓜三",
    "Delta Del": "瓠瓜四", "Epsilon Del": "瓠瓜五",
    # 小马座
    "Alpha Equ": "虚宿二",
    # 南极座
    "Sigma Oct": "南极星",
    # 南三角座
    "Alpha TrA": "三角形三", "Beta TrA": "三角形二", "Gamma TrA": "三角形一",
    # 天坛座
    "Alpha Ara": "杵二", "Beta Ara": "杵三",
    # 盾牌座
    "Alpha Sct": "盾牌α",
    # 三角座
    "Alpha Tri": "娄宿增六", "Beta Tri": "天大将军九",
    # 狐狸座
    "Alpha Vul": "齐增五",
    # 蝎虎座
    "Alpha Lac": "螣蛇一",
    # 后发座
    "Alpha Com": "东上将",
    # 玉夫座
    "Alpha Scl": "玉夫α",
}
