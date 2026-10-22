#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 tools/sky.json —— 星座图鉴数据（真实天文值）。
字段：id（与 levels.json 的 theme.id 对应）、中文/英文/拉丁/缩写、关卡号、
      中心赤经 ra（小时）/赤纬 dec（度）、面积排名、最亮星、季节、天区、
      真实 IAU 相邻星座（拉丁名 + 是否在游戏内可跳转）。
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (id, 中文, 英文, 拉丁, 缩写, 关, ra_h, dec_deg, 面积排名, 最亮星中文, 最亮星英文, 视星等, [相邻拉丁名])
RAW = [
    ("crux", "南十字座", "Crux", "Crux", "Cru", 1, 12.45, -60.0, 88, "十字架二", "Acrux", 0.77,
     ["Centaurus", "Musca"]),
    ("sagitta", "天箭座", "Sagitta", "Sagitta", "Sge", 2, 19.65, 18.5, 86, "天箭γ", "Gamma Sge", 3.47,
     ["Vulpecula", "Hercules", "Aquila", "Delphinus"]),
    ("cassiopeia", "仙后座", "Cassiopeia", "Cassiopeia", "Cas", 3, 1.0, 62.0, 25, "王良四", "Schedar", 2.24,
     ["Camelopardalis", "Cepheus", "Lacerta", "Andromeda", "Perseus"]),
    ("orion", "猎户座", "Orion", "Orion", "Ori", 4, 5.5, 2.0, 26, "参宿七", "Rigel", 0.13,
     ["Taurus", "Gemini", "Monoceros", "Canis Major", "Eridanus", "Lepus"]),
    ("ursa-minor", "小熊座", "Ursa Minor", "Ursa Minor", "UMi", 5, 15.0, 77.0, 56, "北极星", "Polaris", 1.98,
     ["Cepheus", "Camelopardalis", "Draco"]),
    ("cygnus", "天鹅座", "Cygnus", "Cygnus", "Cyg", 6, 20.6, 42.0, 16, "天津四", "Deneb", 1.25,
     ["Draco", "Lyra", "Vulpecula", "Pegasus", "Lacerta", "Cepheus"]),
    ("leo", "狮子座", "Leo", "Leo", "Leo", 7, 10.7, 13.0, 12, "轩辕十四", "Regulus", 1.35,
     ["Ursa Major", "Leo Minor", "Lynx", "Cancer", "Hydra", "Sextans", "Coma Berenices", "Virgo"]),
    ("pegasus", "飞马座", "Pegasus", "Pegasus", "Peg", 8, 22.7, 19.0, 7, "危宿三", "Enif", 2.39,
     ["Andromeda", "Lacerta", "Cygnus", "Vulpecula", "Delphinus", "Equuleus", "Pisces", "Aquarius"]),
    ("gemini", "双子座", "Gemini", "Gemini", "Gem", 9, 7.1, 22.0, 30, "北河三", "Pollux", 1.14,
     ["Lynx", "Auriga", "Taurus", "Orion", "Monoceros", "Canis Minor", "Cancer"]),
    ("scorpius", "天蝎座", "Scorpius", "Scorpius", "Sco", 10, 16.9, -30.0, 33, "心宿二", "Antares", 0.96,
     ["Ophiuchus", "Sagittarius", "Corona Australis", "Lupus", "Libra", "Norma"]),
    ("lyra", "天琴座", "Lyra", "Lyra", "Lyr", 11, 18.8, 37.0, 52, "织女一", "Vega", 0.03,
     ["Draco", "Hercules", "Cygnus", "Vulpecula"]),
    ("ursa-major", "大熊座", "Ursa Major", "Ursa Major", "UMa", 12, 11.3, 51.0, 3, "玉衡", "Alioth", 1.77,
     ["Draco", "Camelopardalis", "Lynx", "Leo Minor", "Canes Venatici", "Coma Berenices", "Bootes"]),
    ("corona-borealis", "北冕座", "Corona Borealis", "Corona Borealis", "CrB", 13, 15.8, 32.0, 73,
     "贯索四", "Alphecca", 2.23, ["Hercules", "Bootes", "Serpens"]),
    ("cepheus", "仙王座", "Cepheus", "Cepheus", "Cep", 14, 22.0, 70.0, 27, "天钩五", "Alderamin", 2.45,
     ["Ursa Minor", "Camelopardalis", "Cassiopeia", "Andromeda", "Lacerta", "Cygnus", "Draco"]),
    ("auriga", "御夫座", "Auriga", "Auriga", "Aur", 15, 6.0, 42.0, 21, "五车二", "Capella", 0.08,
     ["Camelopardalis", "Perseus", "Taurus", "Gemini", "Lynx"]),
    ("bootes", "牧夫座", "Bootes", "Boötes", "Boo", 16, 14.7, 31.0, 13, "大角", "Arcturus", -0.05,
     ["Draco", "Ursa Major", "Canes Venatici", "Coma Berenices", "Virgo", "Serpens", "Corona Borealis", "Hercules"]),
    ("perseus", "英仙座", "Perseus", "Perseus", "Per", 17, 3.5, 45.0, 24, "天船三", "Mirfak", 1.79,
     ["Cassiopeia", "Andromeda", "Triangulum", "Aries", "Taurus", "Auriga", "Camelopardalis"]),
    ("hercules", "武仙座", "Hercules", "Hercules", "Her", 18, 17.4, 31.0, 5, "帝座", "Kornephoros", 2.78,
     ["Draco", "Bootes", "Corona Borealis", "Serpens", "Ophiuchus", "Aquila", "Sagitta", "Vulpecula", "Lyra"]),
    ("draco", "天龙座", "Draco", "Draco", "Dra", 19, 17.0, 65.0, 8, "天棓四", "Eltanin", 2.23,
     ["Ursa Minor", "Camelopardalis", "Ursa Major", "Bootes", "Hercules", "Cygnus", "Lyra", "Aquila"]),
    ("centaurus", "半人马座", "Centaurus", "Centaurus", "Cen", 20, 13.5, -47.0, 9, "南门二", "Rigil Kentaurus",
     -0.27, ["Crux", "Musca", "Carina", "Vela", "Puppis", "Hydra", "Antlia", "Circinus", "Lupus", "Libra"]),
    ("ophiuchus", "蛇夫座", "Ophiuchus", "Ophiuchus", "Oph", 21, 17.4, -3.0, 11, "侯", "Rasalhague", 2.08,
     ["Hercules", "Serpens", "Scorpius", "Sagittarius", "Aquila", "Libra"]),
    ("carina", "船底座", "Carina", "Carina", "Car", 22, 8.7, -63.0, 34, "老人星", "Canopus", -0.72,
     ["Vela", "Puppis", "Pictor", "Volans", "Chamaeleon", "Musca"]),
    ("capricornus", "摩羯座", "Capricornus", "Capricornus", "Cap", 21, 21.0, -20.0, 40,
     "垒壁阵四", "Deneb Algedi", 2.85,
     ["Aquarius", "Aquila", "Sagittarius", "Microscopium", "Piscis Austrinus"]),
    ("grus", "天鹤座", "Grus", "Grus", "Gru", 22, 22.4, -47.0, 45, "鹤一", "Alnair", 1.73,
     ["Piscis Austrinus", "Microscopium", "Indus", "Tucana", "Phoenix", "Sculptor"]),
    ("phoenix", "凤凰座", "Phoenix", "Phoenix", "Phe", 23, 0.9, -49.0, 37, "火鸟六", "Ankaa", 2.40,
     ["Sculptor", "Grus", "Tucana", "Hydrus", "Eridanus", "Fornax"]),
    ("pavo", "孔雀座", "Pavo", "Pavo", "Pav", 24, 19.6, -66.0, 44, "孔雀十一", "Peacock", 1.94,
     ["Indus", "Telescopium", "Ara", "Apus", "Octans"]),
    ("virgo", "室女座", "Virgo", "Virgo", "Vir", 25, 13.4, -4.0, 2, "角宿一", "Spica", 0.98,
     ["Bootes", "Coma Berenices", "Leo", "Crater", "Corvus", "Hydra", "Libra", "Serpens"]),
    ("aquarius", "宝瓶座", "Aquarius", "Aquarius", "Aqr", 27, 22.3, -11.0, 10, "虚宿一", "Sadalsuud", 2.87,
     ["Pegasus", "Equuleus", "Delphinus", "Aquila", "Sagittarius", "Capricornus",
      "Piscis Austrinus", "Sculptor", "Cetus", "Pisces"]),
    ("pisces", "双鱼座", "Pisces", "Pisces", "Psc", 28, 0.9, 14.0, 14, "右更二", "Eta Psc", 3.62,
     ["Triangulum", "Andromeda", "Pegasus", "Aquarius", "Cetus", "Aries"]),
    ("aries", "白羊座", "Aries", "Aries", "Ari", 31, 2.6, 20.0, 39, "娄宿三", "Hamal", 2.00,
     ["Triangulum", "Andromeda", "Pisces", "Cetus", "Taurus", "Perseus"]),
    ("cancer", "巨蟹座", "Cancer", "Cancer", "Cnc", 32, 8.6, 20.0, 31, "柳宿增三", "Altarf", 3.53,
     ["Lynx", "Gemini", "Canis Minor", "Hydra", "Leo", "Leo Minor"]),
    ("corvus", "乌鸦座", "Corvus", "Corvus", "Crv", 33, 12.4, -18.0, 70, "轸宿一", "Gienah", 2.59,
     ["Virgo", "Crater", "Hydra"]),
    ("crater", "巨爵座", "Crater", "Crater", "Crt", 34, 11.4, -15.0, 53, "翼宿一", "Alkes", 4.08,
     ["Leo", "Sextans", "Hydra", "Corvus", "Virgo"]),
    ("leo-minor", "小狮座", "Leo Minor", "Leo Minor", "LMi", 35, 10.2, 33.0, 64, "势四", "Praecipua", 3.83,
     ["Ursa Major", "Lynx", "Cancer", "Leo"]),
    ("lynx", "天猫座", "Lynx", "Lynx", "Lyn", 36, 8.0, 47.0, 28, "天猫α", "Alpha Lyncis", 3.14,
     ["Ursa Major", "Camelopardalis", "Auriga", "Gemini", "Cancer", "Leo", "Leo Minor"]),
    ("monoceros", "麒麟座", "Monoceros", "Monoceros", "Mon", 37, 7.1, -3.0, 35, "麒麟β", "Beta Monocerotis", 3.76,
     ["Canis Major", "Canis Minor", "Gemini", "Hydra", "Lepus", "Orion", "Puppis"]),
    ("libra", "天秤座", "Libra", "Libra", "Lib", 38, 15.2, -15.0, 29, "氐宿四", "Zubeneschamali", 2.61,
     ["Scorpius", "Ophiuchus", "Serpens", "Virgo", "Hydra", "Centaurus", "Lupus"]),
    ("columba", "天鸽座", "Columba", "Columba", "Col", 39, 5.9, -35.0, 54, "丈人一", "Phact", 2.64,
     ["Lepus", "Caelum", "Pictor", "Puppis", "Canis Major"]),
    ("lepus", "天兔座", "Lepus", "Lepus", "Lep", 40, 5.6, -20.0, 51, "厕一", "Arneb", 2.58,
     ["Orion", "Taurus", "Eridanus", "Caelum", "Columba", "Canis Major", "Monoceros"]),
    ("corona-australis", "南冕座", "Corona Australis", "Corona Australis", "CrA", 41, 19.0, -42.0, 80,
     "南冕α", "Alfecca Meridiana", 4.10, ["Sagittarius", "Scorpius", "Ara", "Telescopium"]),
    ("lupus", "豺狼座", "Lupus", "Lupus", "Lup", 42, 15.4, -43.0, 46, "骑官十", "Alpha Lupi", 2.30,
     ["Scorpius", "Libra", "Hydra", "Centaurus", "Circinus", "Norma"]),
    ("aquila", "天鹰座", "Aquila", "Aquila", "Aql", 43, 19.7, 3.0, 22, "河鼓二", "Altair", 0.76,
     ["Sagitta", "Hercules", "Ophiuchus", "Serpens", "Scutum", "Sagittarius", "Capricornus",
      "Aquarius", "Delphinus"]),
    ("cetus", "鲸鱼座", "Cetus", "Cetus", "Cet", 44, 1.7, -10.0, 4, "土司空", "Diphda", 2.04,
     ["Aries", "Pisces", "Aquarius", "Sculptor", "Fornax", "Eridanus", "Taurus"]),
    ("sagittarius", "人马座", "Sagittarius", "Sagittarius", "Sgr", 45, 19.1, -25.0, 15, "箕宿三", "Kaus Australis", 1.79,
     ["Aquila", "Scutum", "Serpens", "Ophiuchus", "Scorpius", "Corona Australis", "Telescopium",
      "Indus", "Capricornus", "Microscopium"]),
    ("puppis", "船尾座", "Puppis", "Puppis", "Pup", 46, 7.7, -31.0, 20, "弧矢增二十二", "Naos", 2.21,
     ["Carina", "Vela", "Pictor", "Canis Major", "Columba", "Monoceros", "Hydra", "Pyxis"]),
    ("vela", "船帆座", "Vela", "Vela", "Vel", 47, 9.6, -47.0, 32, "天社一", "Regor", 1.75,
     ["Carina", "Puppis", "Pyxis", "Antlia", "Centaurus"]),
    ("serpens", "巨蛇座", "Serpens", "Serpens", "Ser", 48, 16.2, 2.0, 23, "蜀", "Unukalhai", 2.63,
     ["Corona Borealis", "Bootes", "Virgo", "Libra", "Ophiuchus", "Hercules", "Aquila", "Scutum",
      "Sagittarius"]),
    ("piscis-austrinus", "南鱼座", "Piscis Austrinus", "Piscis Austrinus", "PsA", 49, 22.3, -30.0, 60,
     "北落师门", "Fomalhaut", 1.16,
     ["Capricornus", "Microscopium", "Grus", "Sculptor", "Aquarius"]),
    ("eridanus", "波江座", "Eridanus", "Eridanus", "Eri", 50, 3.8, -25.0, 6, "水委一", "Achernar", 0.46,
     ["Cetus", "Fornax", "Phoenix", "Hydrus", "Tucana", "Horologium", "Caelum", "Lepus", "Orion",
      "Taurus"]),
    ("hydra", "长蛇座", "Hydra", "Hydra", "Hya", 23, 10.5, -20.0, 1, "星宿一", "Alphard", 1.98,
     ["Antlia", "Cancer", "Canis Minor", "Centaurus", "Corvus", "Crater", "Leo", "Libra", "Lupus",
      "Monoceros", "Puppis", "Pyxis", "Sextans", "Virgo"]),
]

CN_NAMES = {  # 拉丁名 -> 中文名（含未收录的常邻居，方便展示）
    "Caelum": "雕具座", "Scutum": "盾牌座", "Horologium": "时钟座", "Corvus": "乌鸦座",
    "Crater": "巨爵座", "Leo Minor": "小狮座", "Lynx": "天猫座", "Columba": "天鸽座",
    "Lepus": "天兔座", "Aries": "白羊座", "Cancer": "巨蟹座", "Libra": "天秤座",
    "Sagittarius": "人马座", "Virgo": "室女座", "Taurus": "金牛座", "Puppis": "船尾座",
    "Vela": "船帆座", "Carina": "船底座", "Sextans": "六分仪座", "Norma": "矩尺座",
    "Microscopium": "显微镜座", "Piscis Austrinus": "南鱼座", "Indus": "印第安座",
    "Tucana": "杜鹃座", "Sculptor": "玉夫座", "Hydrus": "水蛇座", "Fornax": "天炉座",
    "Telescopium": "望远镜座", "Ara": "天坛座", "Apus": "天燕座", "Octans": "南极座",
    "Grus": "天鹤座", "Phoenix": "凤凰座", "Pavo": "孔雀座", "Virgo": "室女座",
    "Aquarius": "宝瓶座", "Capricornus": "摩羯座", "Pisces": "双鱼座",
    "Centaurus": "半人马座", "Musca": "苍蝇座", "Vulpecula": "狐狸座", "Hercules": "武仙座",
    "Aquila": "天鹰座", "Delphinus": "海豚座", "Camelopardalis": "鹿豹座", "Cepheus": "仙王座",
    "Lacerta": "蝎虎座", "Andromeda": "仙女座", "Perseus": "英仙座", "Taurus": "金牛座",
    "Gemini": "双子座", "Monoceros": "麒麟座", "Canis Major": "大犬座", "Eridanus": "波江座",
    "Lepus": "天兔座", "Ursa Minor": "小熊座", "Draco": "天龙座", "Cygnus": "天鹅座",
    "Lyra": "天琴座", "Pegasus": "飞马座", "Leo": "狮子座", "Leo Minor": "小狮座", "Lynx": "天猫座",
    "Cancer": "巨蟹座", "Hydra": "长蛇座", "Sextans": "六分仪座", "Coma Berenices": "后发座",
    "Virgo": "室女座", "Equuleus": "小马座", "Pisces": "双鱼座", "Aquarius": "宝瓶座",
    "Auriga": "御夫座", "Canis Minor": "小犬座", "Scorpius": "天蝎座", "Ophiuchus": "蛇夫座",
    "Sagittarius": "人马座", "Corona Australis": "南冕座", "Lupus": "豺狼座", "Libra": "天秤座",
    "Norma": "矩尺座", "Ursa Major": "大熊座", "Canes Venatici": "猎犬座", "Bootes": "牧夫座",
    "Boötes": "牧夫座", "Corona Borealis": "北冕座", "Serpens": "巨蛇座", "Triangulum": "三角座",
    "Aries": "白羊座", "Sagitta": "天箭座", "Crux": "南十字座", "Carina": "船底座",
    "Vela": "船帆座", "Puppis": "船尾座", "Antlia": "唧筒座", "Circinus": "圆规座",
    "Pictor": "绘架座", "Volans": "飞鱼座", "Chamaeleon": "蝘蜓座", "Corvus": "乌鸦座",
    "Crater": "巨爵座", "Pyxis": "罗盘座",
}


def season_of(ra):
    """以"晚上 21 点中天"粗略划分季节（北半球视角，南天星座同理看可见时段）"""
    if 9 <= ra < 15: return "春季"
    if 15 <= ra < 21: return "夏季"
    if ra >= 21 or ra < 3: return "秋季"
    return "冬季"


def zone_of(dec):
    if dec >= 30: return "北天"
    if dec <= -30: return "南天"
    return "赤道带"


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


def main():
    by_latin = {r[3]: r for r in RAW}
    out = []
    for (sid, zh, en, latin, abbr, level, ra, dec, rank, bzh, ben, bmag, neigh) in RAW:
        in_game = [by_latin[n][0] for n in neigh if n in by_latin]
        out.append({
            "id": sid, "zh": zh, "en": en, "latin": latin, "abbr": abbr, "level": level,
            "ra": ra, "dec": dec,
            "raText": fmt_ra(ra), "decText": fmt_dec(dec),
            "areaRank": rank, "season": season_of(ra), "zone": zone_of(dec),
            "brightest": {"zh": bzh, "en": ben, "mag": bmag},
            "neighbors": [{"latin": n, "zh": CN_NAMES.get(n, n),
                           "id": by_latin[n][0] if n in by_latin else None,
                           "level": by_latin[n][5] if n in by_latin else None} for n in neigh],
            "inGameNeighbors": in_game,
        })
    path = os.path.join(ROOT, "tools", "sky.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✅ 已写出 {path}（{len(out)} 个星座）")
    seasons = {}
    for x in out:
        seasons[x["season"]] = seasons.get(x["season"], 0) + 1
    print("季节分布:", seasons)
    print("天区分布:", {k: sum(1 for x in out if x["zone"] == k) for k in ("北天", "赤道带", "南天")})
    print("相邻关系总数:", sum(len(x["neighbors"]) for x in out),
          "其中游戏内可跳转:", sum(len(x["inGameNeighbors"]) for x in out))


if __name__ == "__main__":
    main()