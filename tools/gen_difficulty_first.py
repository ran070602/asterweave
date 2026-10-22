#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""难度优先的关卡生成器（v2 思路，用户 2026-10-22 指定）：

1. 先按"可玩性"定盘面：棋盘尺寸（≤11，手机友好）、雷密度、孤立雷、空行空列、0 区；
2. 用求解器验收该盘面"零猜测可解"；
3. **再从盘面里找出星座**：把星座图案做旋转/翻转/缩放后"贴"到已有的雷上（每颗星吸附到最近的一颗雷），
   贴上的那组雷就是 `theme.stars`，其余全部是杂星（`noise`）。
4. 星座只是"命名"一层，不改变难度。

输出：tools/levels_new.json（21 关之后的关卡）
"""
import importlib.util, json, math, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

gl = load("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
f = load("f", os.path.join(ROOT, "tools", "fit_constellation_levels.py"))


# ===== 31–50 关星座（坐标按真实星图简化，视星等为近似值） =====
ARIES = [("娄宿三", "Hamal", (0.30, 0.40), 2.00), ("娄宿一", "Sheratan", (0.44, 0.52), 2.64),
         ("娄宿二", "Mesarthim", (0.50, 0.56), 3.86), ("胃宿一", "Bharani", (0.64, 0.66), 3.61),
         ("白羊ο", "Omicron Ari", (0.22, 0.60), 5.14)]
ARIES_L = [[0, 1], [1, 2], [1, 3], [3, 4]]

CANCER = [("鬼宿四", "Asellus Australis", (0.48, 0.52), 3.94), ("鬼宿三", "Asellus Borealis", (0.46, 0.40), 4.66),
          ("柳宿增三", "Acubens", (0.74, 0.62), 4.25), ("柳宿三", "Iota Cnc", (0.34, 0.56), 4.02),
          ("柳宿二", "Delta Cnc", (0.62, 0.74), 3.94), ("巨蟹ζ", "Zeta Cnc", (0.60, 0.34), 4.67)]
CANCER_L = [[0, 1], [0, 2], [0, 3], [0, 4], [1, 5], [5, 2]]

CORVUS = [("轸宿一", "Gienah", (0.72, 0.28), 2.59), ("轸宿四", "Algorab", (0.70, 0.62), 2.95),
          ("轸宿二", "Kraz", (0.54, 0.68), 2.65), ("轸宿三", "Alchiba", (0.38, 0.48), 4.02),
          ("轸宿增四", "Epsilon Crv", (0.60, 0.44), 3.02)]
CORVUS_L = [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [4, 2]]

CRATER = [("翼宿一", "Alkes", (0.30, 0.52), 4.08), ("翼宿二", "Gamma Crt", (0.40, 0.42), 4.06),
          ("翼宿三", "Delta Crt", (0.52, 0.38), 3.56), ("翼宿四", "Epsilon Crt", (0.62, 0.44), 4.81),
          ("翼宿五", "Zeta Crt", (0.64, 0.58), 4.71), ("翼宿六", "Eta Crt", (0.50, 0.66), 5.17),
          ("翼宿七", "Theta Crt", (0.38, 0.62), 4.70)]
CRATER_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 0]]

DELPHINUS = [("瓠瓜一", "Alpha Del", (0.34, 0.46), 3.77), ("瓠瓜二", "Beta Del", (0.40, 0.36), 3.63),
             ("瓠瓜三", "Gamma Del", (0.48, 0.32), 3.92), ("瓠瓜四", "Delta Del", (0.58, 0.38), 4.43),
             ("瓠瓜五", "Epsilon Del", (0.64, 0.48), 4.03)]
DELPHINUS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]]

LYNX = [("轩辕九", "Alpha Lyn", (0.26, 0.62), 3.14), ("轩辕十", "38 Lyn", (0.36, 0.50), 3.82),
        ("天猫μ", "Mu Lyn", (0.48, 0.44), 3.83), ("天猫ζ", "Zeta Lyn", (0.56, 0.30), 3.97),
        ("天猫β", "Beta Lyn", (0.68, 0.24), 3.53), ("天猫τ", "Tau Lyn", (0.60, 0.54), 4.54),
        ("天猫ψ", "Psi Lyn", (0.46, 0.66), 4.39)]
LYNX_L = [[0, 1], [1, 2], [2, 3], [3, 4], [2, 5], [5, 6], [6, 0]]

MONOCEROS = [("麒麟α", "Alpha Mon", (0.22, 0.40), 3.94), ("麒麟β", "Beta Mon", (0.34, 0.34), 3.74),
             ("麒麟γ", "Gamma Mon", (0.44, 0.42), 3.99), ("麒麟δ", "Delta Mon", (0.54, 0.36), 4.15),
             ("麒麟ε", "Epsilon Mon", (0.62, 0.44), 4.39), ("麒麟ζ", "Zeta Mon", (0.70, 0.54), 4.33),
             ("麒麟θ", "Theta Mon", (0.30, 0.60), 4.13)]
MONOCEROS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [2, 6], [6, 0]]

COLUMBA = [("天鸽α", "Phact", (0.30, 0.40), 2.65), ("天鸽β", "Wazn", (0.40, 0.58), 3.12),
           ("天鸽γ", "Gamma Col", (0.52, 0.46), 4.36), ("天鸽δ", "Delta Col", (0.62, 0.40), 3.85),
           ("天鸽ε", "Epsilon Col", (0.72, 0.50), 3.87), ("天鸽η", "Eta Col", (0.54, 0.66), 3.96),
           ("天鸽θ", "Theta Col", (0.44, 0.30), 5.00), ("天鸽κ", "Kappa Col", (0.66, 0.62), 4.37),
           ("天鸽λ", "Lambda Col", (0.24, 0.56), 4.87)]
COLUMBA_L = [[0, 1], [0, 2], [2, 3], [3, 4], [2, 5], [5, 1], [0, 6], [5, 7], [1, 8]]

LEPUS = [("厕一", "Arneb", (0.30, 0.46), 2.58), ("厕二", "Nihal", (0.38, 0.62), 2.81),
         ("厕三", "Gamma Lep", (0.62, 0.42), 3.60), ("厕四", "Delta Lep", (0.70, 0.56), 3.76),
         ("屏一", "Epsilon Lep", (0.56, 0.58), 3.19), ("屏二", "Mu Lep", (0.50, 0.48), 3.29),
         ("屏三", "Zeta Lep", (0.44, 0.40), 3.55), ("屏四", "Eta Lep", (0.68, 0.30), 3.71),
         ("厕增七", "Kappa Lep", (0.28, 0.32), 4.35), ("厕增六", "Lambda Lep", (0.36, 0.26), 4.29)]
LEPUS_L = [[0, 1], [0, 2], [2, 3], [2, 4], [4, 5], [5, 6], [6, 0], [2, 7], [0, 8], [8, 9]]

ANDROMEDA = [("壁宿二", "Alpheratz", (0.20, 0.30), 2.06), ("奎宿九", "Mirach", (0.44, 0.42), 2.06),
             ("天大将军一", "Almach", (0.66, 0.52), 2.10), ("奎宿五", "Delta And", (0.38, 0.34), 3.27),
             ("奎宿六", "Mu And", (0.54, 0.30), 3.86), ("奎宿七", "Nu And", (0.62, 0.30), 4.53),
             ("奎宿八", "Xi And", (0.30, 0.46), 4.87), ("奎宿二", "Zeta And", (0.26, 0.52), 4.06),
             ("奎宿三", "Eta And", (0.40, 0.56), 4.40), ("天大将军九", "Theta And", (0.58, 0.44), 4.61)]
ANDROMEDA_L = [[0, 3], [3, 1], [1, 2], [1, 4], [4, 5], [0, 6], [6, 7], [7, 8], [8, 1], [4, 9], [9, 2]]

LUPUS = [("骑官十", "Alpha Lup", (0.26, 0.40), 2.30), ("骑官四", "Beta Lup", (0.40, 0.34), 2.68),
         ("骑官一", "Gamma Lup", (0.54, 0.42), 2.78), ("骑官二", "Delta Lup", (0.62, 0.52), 3.22),
         ("骑官三", "Epsilon Lup", (0.66, 0.62), 3.37), ("骑官五", "Zeta Lup", (0.48, 0.56), 3.41),
         ("骑官六", "Eta Lup", (0.36, 0.62), 3.42), ("骑官七", "Theta Lup", (0.28, 0.56), 4.22),
         ("骑官八", "Iota Lup", (0.58, 0.26), 3.55), ("骑官九", "Kappa Lup", (0.44, 0.22), 3.88)]
LUPUS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [2, 5], [5, 6], [6, 7], [7, 0], [1, 8], [8, 9]]

SAGITTARIUS = [("斗宿四", "Nunki", (0.52, 0.44), 2.05), ("斗宿五", "Tau Sgr", (0.60, 0.50), 3.32),
               ("斗宿六", "Zeta Sgr", (0.40, 0.52), 2.60), ("箕宿一", "Gamma Sgr", (0.30, 0.60), 2.98),
               ("箕宿二", "Delta Sgr", (0.26, 0.70), 2.70), ("箕宿三", "Epsilon Sgr", (0.36, 0.78), 1.79),
               ("箕宿四", "Eta Sgr", (0.46, 0.72), 3.10), ("斗宿一", "Phi Sgr", (0.56, 0.62), 3.17),
               ("斗宿二", "Lambda Sgr", (0.64, 0.36), 2.82), ("斗宿三", "Mu Sgr", (0.58, 0.28), 3.84),
               ("建三", "Omicron Sgr", (0.68, 0.44), 3.76), ("天渊三", "Alpha Sgr", (0.74, 0.56), 3.97)]
SAGITTARIUS_L = [[0, 1], [0, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0], [0, 8], [8, 9], [8, 10], [10, 11]]

PUPPIS = [("弧矢七", "Wezen", (0.34, 0.58), 1.83), ("弧矢一", "Adhara", (0.28, 0.70), 1.50),
          ("弧矢二", "Sigma Pup", (0.40, 0.76), 2.25), ("弧矢三", "Rho Pup", (0.46, 0.36), 2.83),
          ("弧矢四", "Pi Pup", (0.54, 0.44), 2.71), ("弧矢五", "Tau Pup", (0.62, 0.50), 2.94),
          ("狐矢六", "Nu Pup", (0.56, 0.62), 3.17), ("船尾ξ", "Xi Pup", (0.66, 0.64), 3.34),
          ("船尾ο", "Omicron Pup", (0.70, 0.52), 4.45), ("船尾χ", "Chi Pup", (0.44, 0.24), 3.03),
          ("船尾μ", "Mu Pup", (0.30, 0.42), 2.99)]
PUPPIS_L = [[0, 1], [0, 2], [0, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [3, 9], [9, 10], [10, 0]]

VELA = [("天社一", "Gamma Vel", (0.34, 0.34), 1.75), ("天社二", "Delta Vel", (0.46, 0.40), 1.96),
        ("天社三", "Kappa Vel", (0.58, 0.34), 2.47), ("天社四", "Mu Vel", (0.66, 0.46), 2.69),
        ("天社五", "Phi Vel", (0.60, 0.60), 3.54), ("天社六", "Psi Vel", (0.46, 0.66), 3.60),
        ("天社七", "Lambda Vel", (0.28, 0.52), 2.21), ("天社八", "Omicron Vel", (0.30, 0.68), 3.60),
        ("天社九", "Epsilon Vel", (0.50, 0.22), 3.01), ("天社十", "Theta Vel", (0.24, 0.26), 3.25),
        ("天社十一", "Iota Vel", (0.68, 0.72), 4.08)]
VELA_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 0], [6, 7], [0, 9], [9, 8], [4, 10]]

ERIDANUS = [("水委一", "Achernar", (0.82, 0.84), 0.46), ("波江θ", "Theta Eri", (0.66, 0.72), 2.90),
            ("波江γ", "Gamma Eri", (0.58, 0.62), 2.95), ("波江δ", "Delta Eri", (0.52, 0.52), 3.54),
            ("天园五", "Epsilon Eri", (0.46, 0.44), 3.73), ("天园六", "Zeta Eri", (0.40, 0.36), 4.80),
            ("波江η", "Eta Eri", (0.34, 0.28), 3.89), ("波江τ", "Tau Eri", (0.28, 0.22), 4.08),
            ("天园一", "Iota Eri", (0.22, 0.30), 4.11), ("天园二", "Kappa Eri", (0.18, 0.42), 4.24),
            ("波江ν", "Nu Eri", (0.22, 0.52), 3.93), ("波江ξ", "Xi Eri", (0.26, 0.60), 5.16),
            ("波江ο", "Omicron1 Eri", (0.30, 0.70), 4.04), ("波江μ", "Mu Eri", (0.36, 0.78), 4.01),
            ("波江β", "Cursa", (0.44, 0.26), 2.78), ("波江ψ", "Psi Eri", (0.56, 0.30), 4.80)]
ERIDANUS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10],
              [10, 11], [11, 12], [12, 13], [13, 3], [5, 14], [14, 15], [15, 1]]

SERPENS = [("天市右垣七", "Alpha Ser", (0.30, 0.34), 2.63), ("天市右垣八", "Beta Ser", (0.42, 0.40), 3.67),
           ("天市右垣九", "Gamma Ser", (0.52, 0.36), 3.85), ("天市右垣十", "Delta Ser", (0.62, 0.30), 3.80),
           ("天市右垣十一", "Epsilon Ser", (0.72, 0.36), 3.71), ("巨蛇η", "Eta Ser", (0.64, 0.50), 3.23),
           ("巨蛇ξ", "Xi Ser", (0.54, 0.56), 3.54), ("巨蛇μ", "Mu Ser", (0.44, 0.62), 3.54),
           ("巨蛇ν", "Nu Ser", (0.34, 0.58), 4.32), ("巨蛇ο", "Omicron Ser", (0.26, 0.50), 4.26),
           ("巨蛇ι", "Iota Ser", (0.36, 0.72), 3.58), ("巨蛇κ", "Kappa Ser", (0.46, 0.78), 4.09)]
SERPENS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 0],
             [7, 10], [10, 11], [11, 7]]

PISCIS_AUST = [("北落师门", "Fomalhaut", (0.52, 0.44), 1.16), ("南鱼ε", "Epsilon PsA", (0.44, 0.56), 4.18),
               ("南鱼δ", "Delta PsA", (0.58, 0.58), 4.21), ("南鱼γ", "Gamma PsA", (0.64, 0.48), 4.46),
               ("南鱼β", "Beta PsA", (0.40, 0.34), 4.29), ("南鱼μ", "Mu PsA", (0.32, 0.50), 4.50),
               ("南鱼θ", "Theta PsA", (0.28, 0.62), 5.01), ("南鱼ι", "Iota PsA", (0.64, 0.70), 4.35),
               ("南鱼τ", "Tau PsA", (0.72, 0.40), 4.94)]
PISCIS_AUST_L = [[0, 1], [1, 2], [2, 3], [0, 3], [0, 6], [6, 5], [5, 4], [0, 7], [7, 2], [3, 8]]

LEO_MINOR = [("轩辕十", "Praecipua", (0.36, 0.46), 3.83), ("小狮β", "Beta LMi", (0.52, 0.34), 4.20),
             ("小狮21", "21 LMi", (0.68, 0.44), 4.49), ("小狮10", "10 LMi", (0.30, 0.62), 4.54),
             ("小狮37", "37 LMi", (0.56, 0.66), 4.68)]
LEO_MINOR_L = [[0, 1], [1, 2], [0, 3], [0, 4], [4, 2]]

FORNAX = [("天炉α", "Dalim", (0.30, 0.46), 3.86), ("天炉β", "Beta For", (0.44, 0.36), 4.45),
          ("天炉ν", "Nu For", (0.58, 0.42), 4.68), ("天炉ω", "Omega For", (0.62, 0.58), 4.96),
          ("天炉δ", "Delta For", (0.40, 0.62), 4.99)]
FORNAX_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]]

TRIANGULUM = [("三角α", "Mothallah", (0.44, 0.34), 3.42), ("三角β", "Beta Tri", (0.30, 0.56), 3.00),
              ("三角γ", "Gamma Tri", (0.68, 0.54), 4.01)]
TRIANGULUM_L = [[0, 1], [1, 2], [2, 0]]

CORONA_AUSTRALIS = [("南冕α", "Alfecca Meridiana", (0.36, 0.44), 4.11), ("南冕β", "Beta CrA", (0.46, 0.36), 4.10),
                    ("南冕γ", "Gamma CrA", (0.58, 0.36), 4.23), ("南冕δ", "Delta CrA", (0.68, 0.46), 4.57),
                    ("南冕ε", "Epsilon CrA", (0.62, 0.60), 4.83), ("南冕ζ", "Zeta CrA", (0.48, 0.64), 4.74),
                    ("南冕η", "Eta CrA", (0.34, 0.58), 5.46)]
CORONA_AUSTRALIS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 0]]

# ---------------------------------------------------------------- 星座池
POOL = {
    "摩羯座": ("Capricornus", f.CAPRICORNUS, f.CAPRICORNUS_L),
    "天鹤座": ("Grus", f.GRUS, f.GRUS_L),
    "凤凰座": ("Phoenix", f.PHOENIX, f.PHOENIX_L),
    "孔雀座": ("Pavo", f.PAVO, f.PAVO_L),
    "室女座": ("Virgo", f.VIRGO, f.VIRGO_L),
    "船底座": ("Carina", f.CARINA, f.CARINA_L),
    "宝瓶座": ("Aquarius", f.AQUARIUS, f.AQUARIUS_L),
    "双鱼座": ("Pisces", f.PISCES, f.PISCES_L),
    "蛇夫座": ("Ophiuchus", f.OPHIUCHUS, f.OPHIUCHUS_L),
    "长蛇座": ("Hydra", f.HYDRA, f.HYDRA_L),
    "三角座": ("Triangulum", TRIANGULUM, TRIANGULUM_L),
    "南冕座": ("Corona Australis", CORONA_AUSTRALIS, CORONA_AUSTRALIS_L),
    "小狮座": ("Leo Minor", LEO_MINOR, LEO_MINOR_L),
    "天炉座": ("Fornax", FORNAX, FORNAX_L),
    "白羊座": ("Aries", ARIES, ARIES_L),
    "巨蟹座": ("Cancer", CANCER, CANCER_L),
    "乌鸦座": ("Corvus", CORVUS, CORVUS_L),
    "巨爵座": ("Crater", CRATER, CRATER_L),
    "海豚座": ("Delphinus", DELPHINUS, DELPHINUS_L),
    "天猫座": ("Lynx", LYNX, LYNX_L),
    "麒麟座": ("Monoceros", MONOCEROS, MONOCEROS_L),
    "天秤座": ("Libra", f.LIBRA, f.LIBRA_L),
    "天鸽座": ("Columba", COLUMBA, COLUMBA_L),
    "天兔座": ("Lepus", LEPUS, LEPUS_L),
    "仙女座": ("Andromeda", ANDROMEDA, ANDROMEDA_L),
    "豺狼座": ("Lupus", LUPUS, LUPUS_L),
    "天鹰座": ("Aquila", f.AQUILA, f.AQUILA_L),
    "鲸鱼座": ("Cetus", f.CETUS, f.CETUS_L),
    "人马座": ("Sagittarius", SAGITTARIUS, SAGITTARIUS_L),
    "船尾座": ("Puppis", PUPPIS, PUPPIS_L),
    "船帆座": ("Vela", VELA, VELA_L),
    "巨蛇座": ("Serpens", SERPENS, SERPENS_L),
    "南鱼座": ("Piscis Austrinus", PISCIS_AUST, PISCIS_AUST_L),
    "波江座": ("Eridanus", ERIDANUS, ERIDANUS_L),
}

# 21–30 关：先定难度（尺寸/密度/探格目标），再配星座
PLAN = [
    dict(lid=21, zh="摩羯座", size=9,  dens=0.18, probes=(22, 32), teach=""),
    dict(lid=22, zh="天鹤座", size=9,  dens=0.19, probes=(24, 34), teach=""),
    dict(lid=23, zh="凤凰座", size=10, dens=0.19, probes=(26, 36), teach=""),
    dict(lid=24, zh="孔雀座", size=10, dens=0.20, probes=(28, 38), teach=""),
    dict(lid=25, zh="室女座", size=10, dens=0.20, probes=(28, 40), teach=""),
    dict(lid=26, zh="船底座", size=11, dens=0.20, probes=(30, 42), teach=""),
    dict(lid=27, zh="宝瓶座", size=11, dens=0.21, probes=(30, 44), teach=""),
    dict(lid=28, zh="双鱼座", size=11, dens=0.21, probes=(32, 44), teach=""),
    dict(lid=29, zh="蛇夫座", size=11, dens=0.22, probes=(33, 46), teach=""),
    dict(lid=30, zh="长蛇座", size=11, dens=0.22, probes=(33, 46), teach=""),
]

# 31–50 关：棋盘 10–11，密度 21%→25%，探格 36→52
PLAN += [
    dict(lid=31, zh="白羊座", size=10, dens=0.21, probes=(34, 44), teach=""),
    dict(lid=32, zh="巨蟹座", size=10, dens=0.21, probes=(34, 44), teach=""),
    dict(lid=33, zh="乌鸦座", size=10, dens=0.22, probes=(35, 45), teach=""),
    dict(lid=34, zh="巨爵座", size=10, dens=0.22, probes=(35, 45), teach=""),
    dict(lid=35, zh="小狮座", size=10, dens=0.22, probes=(36, 46), teach=""),
    dict(lid=36, zh="天猫座", size=10, dens=0.23, probes=(36, 46), teach=""),
    dict(lid=37, zh="麒麟座", size=11, dens=0.23, probes=(37, 47), teach=""),
    dict(lid=38, zh="天秤座", size=11, dens=0.23, probes=(37, 47), teach=""),
    dict(lid=39, zh="天鸽座", size=11, dens=0.23, probes=(38, 48), teach=""),
    dict(lid=40, zh="天兔座", size=11, dens=0.24, probes=(38, 48), teach=""),
    dict(lid=41, zh="南冕座", size=11, dens=0.24, probes=(39, 49), teach=""),
    dict(lid=42, zh="豺狼座", size=11, dens=0.24, probes=(39, 49), teach=""),
    dict(lid=43, zh="天鹰座", size=11, dens=0.24, probes=(40, 50), teach=""),
    dict(lid=44, zh="鲸鱼座", size=11, dens=0.24, probes=(40, 50), teach=""),
    dict(lid=45, zh="人马座", size=11, dens=0.25, probes=(41, 51), teach=""),
    dict(lid=46, zh="船尾座", size=11, dens=0.25, probes=(41, 51), teach=""),
    dict(lid=47, zh="船帆座", size=11, dens=0.25, probes=(42, 52), teach=""),
    dict(lid=48, zh="巨蛇座", size=11, dens=0.25, probes=(42, 52), teach=""),
    dict(lid=49, zh="南鱼座", size=11, dens=0.25, probes=(43, 53), teach=""),
    dict(lid=50, zh="波江座", size=11, dens=0.25, probes=(44, 54), teach=""),
]


def transforms(points):
    """归一化星位 → 旋转/翻转后的归一化坐标（保持 0..1）"""
    out = []
    for rot in (0, 90, 180, 270):
        for flip in (False, True):
            pts = []
            for (x, y) in points:
                if flip:
                    x = 1 - x
                a = math.radians(rot)
                # 以 (0.5,0.5) 为中心旋转，再平移到 0..1
                cx, cy = x - 0.5, y - 0.5
                nx = cx * math.cos(a) - cy * math.sin(a) + 0.5
                ny = cx * math.sin(a) + cy * math.cos(a) + 0.5
                pts.append((nx, ny))
            out.append(pts)
    return out


def snap(pts_norm, mines, n, scale):
    """把（已变换的）星位贴到雷上：每颗星吸附 1.5 格内最近的未占用雷。"""
    mines = list(mines)
    span = (n - 1) * scale
    best = None
    # 用每颗雷作为"第一颗星"的锚点，避免枚举所有平移
    for (mr, mc) in mines:
        for (px, py) in ((pts_norm[0][1], pts_norm[0][0]),):
            dy = mr - py * span
            dx = mc - px * span
            if abs(dy - round(dy)) > 0.34 or abs(dx - round(dx)) > 0.34:
                continue
            used, chosen, cost = set(), [], 0.0
            ok = True
            for (x, y) in pts_norm:
                tr, tc = y * span + dy, x * span + dx
                cand = None; cd = 99
                for (rr, cc) in mines:
                    if (rr, cc) in used:
                        continue
                    d2 = (rr - tr) ** 2 + (cc - tc) ** 2
                    if d2 < cd:
                        cd, cand = d2, (rr, cc)
                if cand is None or cd > 2.6:      # 允许 ~1.6 格误差
                    ok = False; break
                used.add(cand); chosen.append(cand); cost += cd
            if not ok:
                continue
            rows = [p[0] for p in chosen]; cols = [p[1] for p in chosen]
            if max(rows) - min(rows) < n * 0.4 or max(cols) - min(cols) < n * 0.4:
                continue                            # 太挤，不像星座
            cxs = sum(p[1] for p in chosen) / len(chosen)
            cys = sum(p[0] for p in chosen) / len(chosen)
            off = (abs(cxs - (n - 1) / 2) + abs(cys - (n - 1) / 2)) / n
            score = (round(off, 1), cost, abs(scale - 0.75))
            if best is None or score < best[0]:
                best = (score, chosen)
    return best[1] if best else None


def neighbours(n, cell):
    r, c = cell
    return [(r + dr, c + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
            if (dr or dc) and 0 <= r + dr < n and 0 <= c + dc < n]


def gen_layout(n, k, rng):
    """先给每行/每列各铺一颗（消灭空行空列），再在已有雷旁边生长到 k 颗（压低孤立雷）。
    这是"先定难度、再找星座"的第一步：盘面完全由难度参数决定，与星座无关。"""
    ms = set()
    cols = list(range(n)); rng.shuffle(cols)
    for r in range(n):
        ms.add((r, cols[r % n]))
    for c in range(n):
        if not any((r, c) in ms for r in range(n)):
            r = rng.randrange(n)
            for m in list(ms):
                if m[0] == r:
                    ms.discard(m); ms.add((r, c)); break
    guard = 0
    while len(ms) < k and guard < 5000:
        guard += 1
        base = rng.choice(list(ms))
        cand = [x for x in neighbours(n, base) if x not in ms]
        if cand:
            ms.add(rng.choice(cand))
        else:
            free = [(r, c) for r in range(n) for c in range(n) if (r, c) not in ms]
            if not free:
                break
            ms.add(rng.choice(free))
    return ms


def make_board(pl, rng):
    n = pl["size"]
    k = int(round(pl["dens"] * n * n))
    zh = pl["zh"]
    en, stars, lines = POOL[zh]
    k = max(k, len(stars))
    best_cand = None
    for attempt in range(3000):
        ms = gen_layout(n, k, rng)
        if any(not any((r, c) in ms for c in range(n)) for r in range(n)):
            continue
        if any(not any((r, c) in ms for r in range(n)) for c in range(n)):
            continue
        if f.isolated_mines({"mines": [list(x) for x in ms]}, n) > 2:
            continue
        iso = f.isolated_mines({"mines": [list(x) for x in ms]}, n)
        d = build_level(pl, ms, en, stars, lines, n)
        if d is None:
            continue
        ok, probs, info = gl.check_level(d, static=False)
        if not ok:
            continue
        zeros, zr = f.stats_of(d, n)
        if zr > 0.38:
            continue
        if not (pl["probes"][0] <= info["reveal_actions"] <= pl["probes"][1] + 6):
            continue
        iso_now = f.isolated_mines({"mines": [list(x) for x in ms]}, n)
        mid = (pl["probes"][0] + pl["probes"][1]) / 2
        cand_score = (iso_now, abs(info["reveal_actions"] - mid), zr)
        # 从盘面里"认出"星座
        pts_all = [(x, y) for (_, _, (x, y), _) in stars]
        for scale in (0.62, 0.72, 0.82, 0.92):
            for pts in transforms(pts_all):
                chosen = snap(pts, ms, n, scale)
                if not chosen:
                    continue
                d2 = attach_theme(d, en, stars, lines, chosen, n, zh)
                if d2:
                    if "best" not in dir() or True:
                        pass
                    cand = (cand_score, d2, info, zeros, zr)
                    if best_cand is None or cand[0] < best_cand[0]:
                        best_cand = cand
                    if cand_score[0] == 0 and cand_score[1] <= 2:
                        return d2, info, zeros, zr
    return (best_cand[1], best_cand[2], best_cand[3], best_cand[4]) if best_cand else None


def build_level(pl, ms, en, stars, lines, n):
    d = {
        "id": pl["lid"], "name": f"第 {pl['lid']} 关 · {pl['zh']}", "size": n,
        "mines": [list(rc) for rc in sorted(ms)], "noise": [],
        "showRuns": True, "opening": [0, 0], "lives": 3,
        "teach": pl["teach"], "technique": "constellation",
        "rowRuns": [gl.line_runs([(r, c) in ms for c in range(n)]) for r in range(n)],
        "colRuns": [gl.line_runs([(r, c) in ms for r in range(n)]) for c in range(n)],
    }
    p0 = gl.Puzzle(n, [tuple(m) for m in d["mines"]], (0, 0), True)
    best = None
    for r in range(n):
        for c in range(n):
            if (r, c) in p0.mines or p0.num[r][c] != 0:
                continue
            kk = gl.opening_reveal_count(gl.Puzzle(n, [tuple(m) for m in d["mines"]], (r, c), True))
            if kk / (n * n) > 0.38:
                continue
            if best is None or kk > best[0]:
                best = (kk, r, c)
    if best is None:
        return None
    d["opening"] = [best[1], best[2]]
    return d


def attach_theme(d, en, stars, lines, chosen, n, zh):
    order = []
    for idx, (name_zh, name_en, _xy, mag) in enumerate(stars):
        order.append(idx)
    theme_stars = []
    for idx, pos in enumerate(chosen):
        name_zh, name_en, _xy, mag = stars[idx]
        theme_stars.append({"name": name_zh, "en": name_en, "rc": [pos[0], pos[1]], "mag": mag,
                            "tint": ("warm" if name_zh in ("参宿四", "心宿二") else
                                     ("cool" if name_zh in ("参宿七", "天津四") else "neutral"))})
    ms = {tuple(m) for m in d["mines"]}
    if any((s["rc"][0], s["rc"][1]) not in ms for s in theme_stars):
        return None
    if len({(s["rc"][0], s["rc"][1]) for s in theme_stars}) != len(theme_stars):
        return None
    d["theme"] = {"id": en.lower().replace(" ", "-"), "name": zh, "nameEn": en,
                  "fact": f.FACTS.get(en, ""), "stars": theme_stars, "lines": lines}
    star_rc = {(s["rc"][0], s["rc"][1]) for s in theme_stars}
    d["noise"] = [list(rc) for rc in sorted(ms - star_rc)]
    return d


def main():
    lo, hi = 0, 10 ** 9
    if len(sys.argv) >= 3:
        lo, hi = int(sys.argv[1]), int(sys.argv[2])
    rng = random.Random(20261023)
    out = []
    for pl in [p for p in PLAN if lo <= p["lid"] <= hi]:
        got = None
        # 失败兜底：换棋盘尺寸 / 微调密度再试（棋盘仍 ≤11）
        for size, ddelta in ((pl["size"], 0.0), (pl["size"] + 1, 0.0), (pl["size"], 0.01),
                             (pl["size"] + 1, 0.01), (pl["size"] + 1, -0.01)):
            if size > 11:
                continue
            trial = dict(pl, size=size, dens=max(0.16, min(0.24, pl["dens"] + ddelta)))
            got = make_board(trial, rng)
            if got:
                break
        if not got:
            print(f"!! 第 {pl['lid']} 关 {pl['zh']} 生成失败", flush=True)
            continue
        d, info, zeros, zr = got
        n = d["size"]
        iso = f.isolated_mines(d, n)
        print(f"第 {pl['lid']:2d} 关 {pl['zh']:5s} {n}x{n} 雷{len(d['mines']):2d} "
              f"星座星{len(d['theme']['stars']):2d} 杂{len(d['noise']):2d} 探格{info['reveal_actions']:2d} "
              f"星图{info['runs_cells']:2d} 孤立{iso} 0格{zr*100:.0f}%"
              f"{' 必须星图' if not info['nb_only_ok'] else ' 数字可解'}", flush=True)
        out.append(d)
    if len(out) < 3:
        print("!! 生成数量不足，放弃写入"); sys.exit(1)
    json.dump(out, open(os.path.join(ROOT, "tools", "levels_new.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ 已写出 tools/levels_new.json（{len(out)} 关）")


if __name__ == "__main__":
    main()