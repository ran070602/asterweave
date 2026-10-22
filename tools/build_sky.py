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
    ("hydra", "长蛇座", "Hydra", "Hydra", "Hya", 23, 10.5, -20.0, 1, "星宿一", "Alphard", 1.98,
     ["Antlia", "Cancer", "Canis Minor", "Centaurus", "Corvus", "Crater", "Leo", "Libra", "Lupus",
      "Monoceros", "Puppis", "Pyxis", "Sextans", "Virgo"]),
]

CN_NAMES = {  # 拉丁名 -> 中文名（含未收录的常邻居，方便展示）
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