#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""星座关卡 v3：**难度优先**的十关曲线。
原则（用户明确要求）：可玩性 > 星座动画。前十关由小盘、少星、无杂星逐步加码；
杂星（不属于星座的雷）从第 6 关才少量出现，仅用于"让星图线索重新必要"，不为了画面堆雷。
每关都用逻辑求解器验收：零猜测可解；并记录"是否必须用星图线索"（不作为前十关的硬闸门）。
输出 tools/levels.json。
"""
import importlib.util, json, os, random, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location("gl", os.path.join(ROOT, "tools", "generate_levels.py"))
gl = importlib.util.module_from_spec(spec); spec.loader.exec_module(gl)

# (中文名, 英文名, 归一化 x,y, 视星等)
CRUX = [("十字架二", "Acrux", (0.30, 0.12), 0.77), ("十字架三", "Mimosa", (0.70, 0.30), 1.25),
        ("十字架一", "Gacrux", (0.28, 0.86), 1.59), ("十字架四", "Imai", (0.72, 0.74), 2.79)]
CRUX_L = [[0, 2], [1, 3]]

SAGITTA = [("左旗一", "Gamma Sge", (0.20, 0.30), 3.47), ("天箭座δ", "Delta Sge", (0.42, 0.28), 3.68),
           ("天箭座ε", "Epsilon Sge", (0.62, 0.34), 3.75), ("天箭座ζ", "Zeta Sge", (0.84, 0.30), 5.0)]
SAGITTA_L = [[0, 1], [1, 2], [2, 3]]

CAS = [("策", "Gamma Cas", (0.12, 0.34), 2.47), ("王良四", "Schedar", (0.30, 0.66), 2.24),
       ("王良一", "Caph", (0.50, 0.30), 2.28), ("阁道三", "Ruchbah", (0.70, 0.70), 2.68),
       ("阁道二", "Segin", (0.88, 0.34), 3.38)]
CAS_L = [[0, 1], [1, 2], [2, 3], [3, 4]]

ORION = [("参宿四", "Betelgeuse", (0.30, 0.12), 0.42), ("参宿五", "Bellatrix", (0.70, 0.18), 1.64),
         ("参宿一", "Alnitak", (0.38, 0.50), 1.77), ("参宿二", "Alnilam", (0.50, 0.48), 1.69),
         ("参宿三", "Mintaka", (0.62, 0.46), 2.25), ("参宿六", "Saiph", (0.34, 0.88), 2.06),
         ("参宿七", "Rigel", (0.72, 0.90), 0.13)]
ORION_L = [[0, 2], [2, 3], [3, 4], [4, 1], [2, 5], [4, 6]]

URSA_MINOR = [("北极星", "Polaris", (0.50, 0.06), 1.98), ("小熊γ", "Pherkad", (0.18, 0.30), 3.05),
              ("小熊β", "Kochab", (0.24, 0.52), 2.08), ("小熊ζ", "Zeta UMi", (0.42, 0.58), 4.29),
              ("小熊ε", "Epsilon UMi", (0.60, 0.66), 4.21), ("小熊δ", "Delta UMi", (0.74, 0.62), 4.36),
              ("小熊η", "Eta UMi", (0.70, 0.44), 4.95)]
URSA_MINOR_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 1]]

CYGNUS = [("天津四", "Deneb", (0.50, 0.06), 1.25), ("天津一", "Sadr", (0.47, 0.42), 2.23),
          ("辇道增七", "Albireo", (0.44, 0.92), 3.05), ("天津九", "Gienah", (0.86, 0.32), 2.48),
          ("天津二", "Delta Cyg", (0.70, 0.50), 2.87), ("天津八", "Iota Cyg", (0.20, 0.26), 3.79),
          ("天津六", "Tau Cyg", (0.26, 0.56), 3.74), ("天津三", "Eta Cyg", (0.64, 0.28), 3.89),
          ("辇道一", "Kappa Cyg", (0.34, 0.70), 3.77)]
CYGNUS_L = [[0, 1], [1, 2], [1, 6], [6, 5], [1, 4], [4, 3], [4, 7], [2, 8]]

LEO = [("轩辕十四", "Regulus", (0.30, 0.82), 1.35), ("轩辕十三", "Eta Leo", (0.24, 0.58), 3.48),
       ("轩辕十二", "Algieba", (0.30, 0.44), 2.08), ("轩辕十一", "Zeta Leo", (0.36, 0.30), 3.44),
       ("轩辕十", "Mu Leo", (0.46, 0.22), 3.88), ("轩辕九", "Epsilon Leo", (0.58, 0.20), 2.98),
       ("五帝座一", "Denebola", (0.84, 0.60), 2.14), ("西上相", "Zosma", (0.64, 0.52), 2.56),
       ("西次相", "Chertan", (0.62, 0.72), 3.33)]
LEO_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [2, 7], [7, 6], [7, 8], [8, 0]]

TAURUS = [("毕宿五", "Aldebaran", (0.42, 0.54), 0.87), ("毕宿一", "Epsilon Tau", (0.34, 0.62), 3.53),
          ("毕宿二", "Gamma Tau", (0.50, 0.44), 3.65), ("毕宿三", "Delta Tau", (0.58, 0.38), 3.76),
          ("毕宿四", "Theta Tau", (0.38, 0.48), 3.40), ("金牛ζ", "Zeta Tau", (0.30, 0.40), 2.97),
          ("五车五", "Elnath", (0.80, 0.14), 1.65), ("天关", "Lambda Tau", (0.16, 0.30), 3.47),
          ("觜宿一", "Lambda Ori", (0.72, 0.26), 3.39), ("金牛ο", "Omicron Tau", (0.46, 0.66), 3.61),
          ("金牛τ", "Tau Tau", (0.40, 0.30), 4.27)]
TAURUS_L = [[0, 1], [1, 4], [4, 2], [2, 3], [3, 6], [4, 5], [5, 7], [3, 8], [0, 9], [5, 10]]

SCORPIUS = [("房宿三", "Dschubba", (0.62, 0.24), 2.29), ("房宿四", "Acrab", (0.70, 0.16), 2.56),
            ("尾宿五", "Sargas", (0.84, 0.60), 1.86), ("心宿二", "Antares", (0.48, 0.50), 0.96),
            ("心宿一", "Tau Sco", (0.54, 0.62), 2.82), ("尾宿二", "Epsilon Sco", (0.46, 0.68), 2.29),
            ("尾宿三", "Mu Sco", (0.44, 0.78), 3.00), ("尾宿八", "Shaula", (0.52, 0.88), 1.62),
            ("尾宿九", "Lesath", (0.64, 0.88), 2.70), ("尾宿一", "Theta Sco", (0.74, 0.82), 1.86),
            ("天蝎σ", "Sigma Sco", (0.60, 0.38), 2.90), ("天蝎π", "Pi Sco", (0.80, 0.30), 2.89),
            ("天蝎ι", "Iota Sco", (0.86, 0.44), 3.03)]
SCORPIUS_L = [[1, 0], [0, 10], [10, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 2], [2, 12], [12, 11], [11, 1]]

GEMINI = [("北河二", "Castor", (0.62, 0.10), 1.58), ("北河三", "Pollux", (0.72, 0.20), 1.14),
          ("井宿三", "Alhena", (0.56, 0.74), 1.93), ("井宿一", "Mu Gem", (0.48, 0.44), 2.87),
          ("井宿二", "Nu Gem", (0.42, 0.52), 4.13), ("井宿四", "Xi Gem", (0.36, 0.60), 3.35),
          ("井宿五", "Epsilon Gem", (0.28, 0.66), 2.98), ("井宿六", "Zeta Gem", (0.32, 0.34), 3.79),
          ("积薪", "Kappa Gem", (0.44, 0.26), 3.57), ("井宿七", "Delta Gem", (0.52, 0.32), 3.53),
          ("钺", "Eta Gem", (0.38, 0.84), 3.28), ("双子τ", "Tau Gem", (0.24, 0.22), 4.41)]
GEMINI_L = [[0, 1], [0, 8], [8, 9], [9, 2], [1, 9], [8, 7], [7, 11], [8, 3], [3, 4], [4, 5], [5, 6], [6, 10]]

PEGASUS = [("室宿一", "Markab", (0.32, 0.22), 2.48), ("室宿二", "Scheat", (0.24, 0.44), 2.42),
           ("壁宿一", "Algenib", (0.52, 0.46), 2.83), ("壁宿二", "Alpheratz", (0.44, 0.18), 2.06),
           ("危宿三", "Enif", (0.88, 0.66), 2.39), ("离宫四", "Matar", (0.66, 0.34), 2.94),
           ("飞马θ", "Theta Peg", (0.74, 0.50), 3.53), ("飞马η", "Eta Peg", (0.58, 0.74), 2.94),
           ("飞马π", "Pi Peg", (0.78, 0.24), 4.28)]
PEGASUS_L = [[0, 1], [1, 2], [2, 3], [3, 0], [0, 4], [4, 6], [6, 5], [2, 7], [3, 8]]



DRACO = [("右枢", "Thuban", (0.30, 0.14), 3.65), ("天棓四", "Eltanin", (0.52, 0.10), 2.23),
         ("天棓三", "Rastaban", (0.64, 0.16), 2.79), ("天棓二", "Xi Dra", (0.72, 0.26), 3.75),
         ("天龙δ", "Delta Dra", (0.74, 0.40), 3.07), ("天龙ζ", "Zeta Dra", (0.68, 0.52), 3.17),
         ("天龙η", "Eta Dra", (0.58, 0.60), 2.73), ("天龙θ", "Theta Dra", (0.50, 0.68), 4.01),
         ("天龙ι", "Iota Dra", (0.40, 0.74), 3.29), ("天龙χ", "Chi Dra", (0.30, 0.70), 3.57),
         ("天龙ω", "Omega Dra", (0.24, 0.60), 4.80), ("天龙ψ", "Psi Dra", (0.20, 0.48), 4.58),
         ("天龙φ", "Phi Dra", (0.22, 0.36), 4.22), ("天龙τ", "Tau Dra", (0.26, 0.24), 4.45)]
DRACO_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10],
           [10, 11], [11, 12], [12, 13], [13, 0]]


CENTAURUS = [("南门二", "Rigil Kentaurus", (0.44, 0.74), -0.27), ("马腹一", "Hadar", (0.54, 0.68), 0.61),
             ("半人马θ", "Menkent", (0.28, 0.80), 2.06), ("半人马γ", "Gamma Cen", (0.36, 0.58), 2.17),
             ("半人马ε", "Epsilon Cen", (0.40, 0.50), 2.30), ("半人马η", "Eta Cen", (0.28, 0.42), 2.31),
             ("半人马ζ", "Zeta Cen", (0.50, 0.42), 2.55), ("半人马δ", "Delta Cen", (0.58, 0.54), 2.60),
             ("半人马ι", "Iota Cen", (0.48, 0.34), 2.73), ("半人马λ", "Lambda Cen", (0.40, 0.28), 3.13),
             ("半人马μ", "Mu Cen", (0.32, 0.24), 3.04), ("半人马ν", "Nu Cen", (0.24, 0.32), 3.41),
             ("半人马ξ", "Xi Cen", (0.64, 0.44), 4.83), ("半人马φ", "Phi Cen", (0.68, 0.60), 3.83)]
CENTAURUS_L = [[0, 1], [1, 7], [7, 12], [7, 13], [1, 8], [8, 2], [2, 3], [3, 4], [4, 5], [5, 6],
               [6, 9], [9, 10], [10, 11], [6, 8]]


CETUS = [("天仓五", "Menkar", (0.66, 0.40), 2.54), ("天仓四", "Gamma Cet", (0.74, 0.34), 3.47),
         ("天仓三", "Delta Cet", (0.78, 0.44), 4.07), ("天仓二", "Lambda Cet", (0.80, 0.52), 4.71),
         ("天囷一", "Mu Cet", (0.76, 0.56), 4.27), ("天囷二", "Xi2 Cet", (0.70, 0.52), 4.28),
         ("天囷三", "Nu Cet", (0.64, 0.50), 4.87), ("天囷四", "Xi1 Cet", (0.58, 0.54), 4.36),
         ("天囷八", "Nu Cet", (0.50, 0.56), 4.29), ("鲸鱼θ", "Theta Cet", (0.42, 0.58), 3.60),
         ("鲸鱼ι", "Iota Cet", (0.34, 0.62), 3.56), ("鲸鱼τ", "Tau Cet", (0.44, 0.70), 3.49),
         ("土司空", "Diphda", (0.24, 0.78), 2.04)]
CETUS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10], [9, 11], [11, 0], [10, 12], [11, 12]]


HERCULES = [("帝座", "Rasalgethi", (0.40, 0.16), 3.35), ("天纪二", "Pi Her", (0.30, 0.30), 3.92),
            ("天纪三", "Eta Her", (0.34, 0.44), 3.16), ("天纪四", "Zeta Her", (0.44, 0.50), 4.20),
            ("天棓一", "Epsilon Her", (0.56, 0.44), 3.14), ("天棓二", "Delta Her", (0.62, 0.34), 3.16),
            ("天棓三", "Alpha Her", (0.70, 0.24), 3.48), ("天棓四", "Beta Her", (0.78, 0.16), 3.73),
            ("天棓五", "Mu Her", (0.66, 0.52), 3.90), ("天棓六", "Xi Her", (0.58, 0.62), 4.47),
            ("天棓七", "Omicron Her", (0.46, 0.68), 4.36), ("天棓八", "Iota Her", (0.36, 0.66), 4.42),
            ("天棓九", "Theta Her", (0.30, 0.58), 4.42), ("天棓十", "Tau Her", (0.52, 0.28), 4.19)]
HERCULES_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 1], [4, 5], [5, 6], [6, 7], [4, 8], [8, 9],
              [9, 10], [10, 11], [11, 12], [4, 13], [13, 6]]

# ===== 11–20 关星座（更大、星更多；坐标归一化，视星等为真实值近似） =====
LYRA = [("织女一", "Vega", (0.52, 0.08), 0.03), ("渐台二", "Sheliak", (0.42, 0.40), 3.52),
        ("渐台三", "Sulafat", (0.56, 0.42), 3.25), ("天琴δ", "Delta Lyr", (0.46, 0.56), 4.30),
        ("天琴ζ", "Zeta Lyr", (0.66, 0.58), 4.34), ("天琴κ", "Kappa Lyr", (0.70, 0.30), 4.33),
        ("天琴θ", "Theta Lyr", (0.60, 0.22), 4.35)]
LYRA_L = [[0, 6], [6, 5], [0, 1], [1, 2], [1, 3], [2, 4], [3, 4]]

URSA_MAJOR = [("天枢", "Dubhe", (0.72, 0.18), 1.79), ("天璇", "Merak", (0.58, 0.32), 2.37),
              ("天玑", "Phecda", (0.60, 0.50), 2.44), ("天权", "Megrez", (0.70, 0.60), 3.31),
              ("玉衡", "Alioth", (0.48, 0.44), 1.77), ("开阳", "Mizar", (0.32, 0.34), 2.23),
              ("摇光", "Alkaid", (0.14, 0.24), 1.86)]
URSA_MAJOR_L = [[0, 1], [1, 2], [2, 3], [3, 0], [3, 4], [4, 5], [5, 6]]

CORONA_BOREALIS = [("贯索四", "Alphecca", (0.56, 0.56), 2.23), ("贯索三", "Beta CrB", (0.42, 0.48), 3.66),
                   ("贯索一", "Theta CrB", (0.32, 0.36), 4.06), ("贯索二", "Gamma CrB", (0.36, 0.22), 4.04),
                   ("贯索ε", "Epsilon CrB", (0.50, 0.14), 4.14), ("贯索δ", "Delta CrB", (0.62, 0.20), 3.84),
                   ("贯索ζ", "Zeta CrB", (0.70, 0.34), 4.57)]
CORONA_BOREALIS_L = [[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 0], [0, 1]]

CEPH = [("天钩五", "Alderamin", (0.46, 0.10), 2.45), ("仙王β", "Alfirk", (0.38, 0.20), 3.23),
        ("仙王γ", "Gamma Cep", (0.30, 0.32), 3.21), ("仙王ι", "Iota Cep", (0.34, 0.52), 3.52),
        ("仙王ζ", "Zeta Cep", (0.46, 0.58), 3.35), ("仙王ο", "Omicron Cep", (0.60, 0.50), 4.75),
        ("仙王κ", "Kappa Cep", (0.66, 0.36), 4.39), ("仙王ξ", "Xi Cep", (0.60, 0.22), 4.29)]
CEPH_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0]]

AURIGA = [("五车二", "Capella", (0.34, 0.16), 0.08), ("五车三", "Menkalinan", (0.44, 0.24), 1.90),
          ("五车四", "Theta Aur", (0.56, 0.30), 2.99), ("五车五", "Elnath", (0.74, 0.40), 1.65),
          ("御夫θ", "Theta Aur", (0.40, 0.46), 2.62), ("御夫ι", "Iota Aur", (0.28, 0.58), 2.69),
          ("御夫ε", "Epsilon Aur", (0.26, 0.40), 3.03), ("御夫η", "Eta Aur", (0.50, 0.56), 3.17)]
AURIGA_L = [[0, 1], [1, 2], [2, 3], [2, 7], [7, 4], [4, 5], [5, 6], [6, 0]]

AQUILA = [("河鼓二", "Altair", (0.44, 0.34), 0.76), ("河鼓一", "Beta Aql", (0.36, 0.26), 3.71),
          ("河鼓三", "Gamma Aql", (0.52, 0.26), 3.90), ("天鹰δ", "Delta Aql", (0.58, 0.42), 3.36),
          ("天鹰λ", "Lambda Aql", (0.64, 0.54), 3.44), ("天鹰θ", "Theta Aql", (0.50, 0.60), 3.23),
          ("天鹰ζ", "Zeta Aql", (0.40, 0.64), 2.99), ("天鹰η", "Eta Aql", (0.28, 0.50), 3.87),
          ("天鹰β", "Alshain", (0.22, 0.36), 3.71)]
AQUILA_L = [[1, 0], [0, 2], [2, 3], [3, 4], [3, 5], [5, 6], [6, 7], [7, 8], [0, 5]]

CANIS_MAJOR = [("天狼星", "Sirius", (0.42, 0.34), -1.46), ("军市一", "Mirzam", (0.32, 0.28), 1.98),
               ("天狼增四", "Nu2 CMa", (0.28, 0.44), 4.11), ("弧矢七", "Wezen", (0.50, 0.64), 1.83),
               ("弧矢一", "Adhara", (0.40, 0.74), 1.50), ("弧矢二", "Sigma CMa", (0.52, 0.78), 2.45),
               ("犬狼ζ", "Zeta CMa", (0.60, 0.60), 3.02), ("犬狼η", "Eta CMa", (0.54, 0.46), 2.45),
               ("犬狼ε", "Adhara", (0.60, 0.50), 1.98)]
CANIS_MAJOR_L = [[1, 0], [0, 2], [0, 7], [7, 8], [7, 3], [3, 4], [4, 5], [3, 6], [6, 8]]

BOOTES = [("大角", "Arcturus", (0.40, 0.66), -0.05), ("梗河一", "Izar", (0.50, 0.52), 2.37),
          ("招摇", "Gamma Boo", (0.42, 0.40), 2.68), ("右摄提一", "Eta Boo", (0.28, 0.44), 2.68),
          ("左摄提一", "Zeta Boo", (0.60, 0.44), 4.18), ("玄戈", "Mu Boo", (0.62, 0.30), 4.52),
          ("牧夫δ", "Delta Boo", (0.54, 0.18), 3.47), ("牧夫ν", "Nu Boo", (0.34, 0.14), 4.06),
          ("牧夫μ", "Mu1 Boo", (0.24, 0.56), 4.31), ("牧夫θ", "Theta Boo", (0.20, 0.70), 4.05)]
BOOTES_L = [[0, 1], [1, 2], [2, 3], [2, 4], [4, 5], [5, 6], [6, 7], [7, 3], [0, 8], [8, 9], [9, 0]]

PERSEUS = [("天船三", "Mirfak", (0.40, 0.28), 1.79), ("大陵五", "Algol", (0.34, 0.50), 2.09),
           ("英仙ρ", "Rho Per", (0.58, 0.24), 3.32), ("英仙γ", "Gamma Per", (0.64, 0.42), 2.93),
           ("英仙δ", "Delta Per", (0.52, 0.54), 3.01), ("英仙ε", "Epsilon Per", (0.44, 0.64), 2.89),
           ("英仙ζ", "Zeta Per", (0.32, 0.62), 2.85), ("英仙η", "Eta Per", (0.24, 0.42), 3.76),
           ("英仙ν", "Nu Per", (0.22, 0.28), 3.77), ("英仙τ", "Tau Per", (0.20, 0.16), 3.95)]
PERSEUS_L = [[0, 1], [1, 7], [7, 6], [6, 5], [5, 4], [4, 3], [3, 2], [0, 8], [8, 9], [9, 0], [0, 2]]


# ===== 21–23 关星座（更大，16 星级别） =====
OPHIUCHUS = [
    ("侯", "Yed Prior", (0.10, 0.42), 2.73), ("韩", "Yed Posterior", (0.16, 0.50), 3.23),
    ("楚", "Cebalrai", (0.22, 0.56), 2.76), ("天江三", "Theta Oph", (0.32, 0.62), 3.27),
    ("天江二", "Eta Oph", (0.48, 0.66), 2.43), ("天江一", "Zeta Oph", (0.56, 0.58), 2.56),
    ("天市右垣九", "Delta Oph", (0.62, 0.46), 2.73), ("天市右垣十", "Epsilon Oph", (0.68, 0.36), 3.24),
    ("天市右垣十一", "Zeta Oph", (0.74, 0.26), 3.19), ("天市左垣九", "Nu Oph", (0.52, 0.40), 3.34),
    ("天市左垣十", "Xi Oph", (0.46, 0.30), 4.39), ("天市左垣十一", "Omicron Oph", (0.40, 0.22), 4.59),
    ("天市左垣六", "Kappa Oph", (0.30, 0.30), 3.19), ("天市左垣七", "Iota Oph", (0.22, 0.38), 4.39),
    ("天蝎ν", "Mu Oph", (0.58, 0.72), 4.58), ("宗正一", "Beta Oph", (0.66, 0.62), 2.76),
]
OPHIUCHUS_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [6, 9], [9, 10],
               [10, 11], [11, 12], [12, 13], [13, 0], [4, 14], [14, 15], [15, 6]]

CARINA = [
    ("老人星", "Canopus", (0.30, 0.18), -0.72), ("船底β", "Miaplacidus", (0.44, 0.60), 1.67),
    ("船底θ", "Theta Car", (0.52, 0.40), 2.74), ("船底ω", "Omega Car", (0.46, 0.22), 3.29),
    ("船底υ", "Upsilon Car", (0.62, 0.30), 2.97), ("船底χ", "Chi Car", (0.68, 0.42), 3.46),
    ("船底ι", "Iota Car", (0.58, 0.66), 2.21), ("船底ε", "Epsilon Car", (0.38, 0.74), 1.86),
    ("船底η", "Eta Car", (0.72, 0.22), 4.50), ("船底p", "p Car", (0.78, 0.34), 3.30),
    ("船底q", "q Car", (0.40, 0.44), 3.44), ("船底r", "r Car", (0.34, 0.54), 3.13),
    ("船底s", "s Car", (0.28, 0.64), 3.80), ("船底t", "t Car", (0.22, 0.74), 3.48),
]
CARINA_L = [[0, 1], [1, 2], [2, 3], [0, 3], [2, 4], [4, 5], [2, 6], [6, 8], [8, 9], [9, 7],
            [6, 7], [0, 10], [10, 11], [11, 12], [12, 13]]

HYDRA = [
    ("星宿一", "Alphard", (0.72, 0.30), 1.98), ("星宿二", "Theta Hya", (0.64, 0.38), 3.88),
    ("星宿三", "Iota Hya", (0.56, 0.34), 3.91), ("星宿四", "Lambda Hya", (0.50, 0.28), 3.61),
    ("星宿五", "Mu Hya", (0.42, 0.34), 3.81), ("星宿六", "Nu Hya", (0.36, 0.42), 3.11),
    ("星宿七", "Xi Hya", (0.30, 0.50), 3.54), ("柳宿一", "Epsilon Hya", (0.24, 0.58), 3.38),
    ("柳宿二", "Delta Hya", (0.18, 0.64), 4.14), ("长蛇β", "Beta Hya", (0.12, 0.70), 4.27),
    ("长蛇γ", "Gamma Hya", (0.20, 0.76), 2.99), ("长蛇π", "Pi Hya", (0.34, 0.84), 3.25),
    ("长蛇σ", "Sigma Hya", (0.48, 0.88), 4.44), ("长蛇τ", "Tau Hya", (0.62, 0.84), 4.60),
    ("长蛇φ", "Phi Hya", (0.74, 0.78), 4.12), ("长蛇χ", "Chi Hya", (0.84, 0.70), 4.93),
]
HYDRA_L = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9], [9, 10],
           [10, 11], [11, 12], [12, 13], [13, 14], [14, 15]]

# 十关曲线：先小后大；杂星只从第 6 关起少量出现
PLAN = [
    dict(lid=1, zh="南十字座", en="Crux", stars=CRUX, lines=CRUX_L, board=6, probes=(16,26), runs=False,
         teach="黑格是夜空里的星。左边和上面的数字 = 这一行/列里连着几颗星。把星标出来，星座就会亮。"),
    dict(lid=2, zh="天箭座", en="Sagitta", stars=SAGITTA, lines=SAGITTA_L, board=6, probes=(16,24), teach=""),
    dict(lid=3, zh="仙后座", en="Cassiopeia", stars=CAS, lines=CAS_L, board=6, probes=(16,24), teach=""),
    dict(lid=4, zh="猎户座", en="Orion", stars=ORION, lines=ORION_L, board=7, probes=(20,28), teach=""),
    dict(lid=5, zh="小熊座", en="Ursa Minor", stars=URSA_MINOR, lines=URSA_MINOR_L, board=7, probes=(20,28), teach=""),
    dict(lid=6, zh="天鹅座", en="Cygnus", stars=CYGNUS, lines=CYGNUS_L, board=7, probes=(24,32),
         teach="注意：边缘有些星**不属于**这个星座，它们同样是雷，但不会被连进星座图。"),
    dict(lid=7, zh="狮子座", en="Leo", stars=LEO, lines=LEO_L, board=8, probes=(26,34), teach=""),
    dict(lid=8, zh="飞马座", en="Pegasus", stars=PEGASUS, lines=PEGASUS_L, board=8, probes=(26,34), teach=""),
    dict(lid=9, zh="双子座", en="Gemini", stars=GEMINI, lines=GEMINI_L, board=9, probes=(30,40), teach=""),
    dict(lid=10, zh="天蝎座", en="Scorpius", stars=SCORPIUS, lines=SCORPIUS_L, board=9, probes=(30,40), teach=""),    dict(lid=11, zh="天琴座", en="Lyra", stars=LYRA, lines=LYRA_L, board=9, probes=(29, 38), teach=""),
    dict(lid=12, zh="大熊座", en="Ursa Major", stars=URSA_MAJOR, lines=URSA_MAJOR_L, board=9, probes=(30, 38),
         teach="这一关的七颗星就是北斗七星。"),
    dict(lid=13, zh="北冕座", en="Corona Borealis", stars=CORONA_BOREALIS, lines=CORONA_BOREALIS_L,
         board=9, probes=(31, 39), teach=""),
    dict(lid=14, zh="仙王座", en="Cepheus", stars=CEPH, lines=CEPH_L, board=10, probes=(31, 39), teach=""),
    dict(lid=15, zh="御夫座", en="Auriga", stars=AURIGA, lines=AURIGA_L, board=10, probes=(32, 40), teach=""),
    dict(lid=16, zh="牧夫座", en="Bootes", stars=BOOTES, lines=BOOTES_L, board=10, probes=(34, 44), teach=""),
    dict(lid=17, zh="英仙座", en="Perseus", stars=PERSEUS, lines=PERSEUS_L, board=11, probes=(34, 44), teach=""),
    dict(lid=18, zh="武仙座", en="Hercules", stars=HERCULES, lines=HERCULES_L, board=11, probes=(34, 46), teach=""),
    dict(lid=19, zh="天龙座", en="Draco", stars=DRACO, lines=DRACO_L, board=10, probes=(34, 46), teach=""),
    dict(lid=20, zh="半人马座", en="Centaurus", stars=CENTAURUS, lines=CENTAURUS_L, board=11, probes=(34, 46), teach=""),
]

FACTS = {
    "Crux": "南十字座是南半球最有名的星座，四颗亮星组成一个十字；它的长轴延长约 4.5 倍就指向南天极。",
    "Sagitta": "天箭座是全天第三小的星座，四颗星排成一支箭，位于银河之中。",
    "Cassiopeia": "仙后座五颗亮星连成一个 W（或 M），秋天在北边天空很容易找到。",
    "Orion": "猎户座中间三颗星排成一条直线（腰带），左上是红色的参宿四，右下是亮蓝的参宿七。",
    "Ursa Minor": "小熊座最末端是北极星，它几乎不动，是辨认方向的基准。",
    "Cygnus": "天鹅座像一个大十字，也叫「北十字」，最亮的天津四在十字顶端。",
    "Leo": "狮子座前半身像一把反写的镰刀，亮星轩辕十四在镰刀底部。",
    "Taurus": "金牛座有 V 形的脸和两颗长角，最亮的毕宿五是一颗橙色巨星。",
    "Scorpius": "天蝎座红色的心宿二在胸口，尾巴向右下弯出一个大钩。",
    "Gemini": "双子座两颗亮星北河二、北河三并肩而立，像一对孪生兄弟。",
}

FACTS.update({
    "Hercules": "武仙座由「拱心石」四边形和四条向外伸展的手臂组成，是北天最大的星座之一。",
    "Cetus": "鲸鱼座是黄道附近的大星座，最亮的土司空和天仓五连成一个不规则的长链。",
    "Ophiuchus": "蛇夫座是黄道十三星座之一，像一个提蛇的人；它横跨银河，夏季在南方天空。",
    "Carina": "船底座是南天最亮的星座之一，拥有全天第二亮的老人星，还有著名的船底座星云。",
    "Hydra": "长蛇座是全天面积最大的星座，从巨蟹座一直蜿蜒到天秤座，头尾跨度超过四分之一天空。",
    "Centaurus": "半人马座拥有离太阳最近的恒星系统「南门二」（三合星），是南天最壮观的星座之一。",
    "Draco": "天龙座是一条绕着小熊座蜿蜒的「长龙」，十四颗星连成一条长折线，在北天整夜可见。",
    "Lyra": "天琴座最亮的织女一是夏季大三角之一；四颗暗星组成一个小平行四边形，像一把竖琴。",
    "Ursa Major": "大熊座的七颗亮星就是「北斗七星」：斗柄三颗、斗身四颗，是北天最好认的形状。",
    "Corona Borealis": "北冕座七颗星连成一个半圆，像一顶镶着宝石的王冠。",
    "Cepheus": "仙王座几颗星连成一个屋形（五边形），位于北极星附近，终年可见。",
    "Auriga": "御夫座像一个五边形，最亮的五车二是北天第六亮星，冬季黄昏挂在天顶附近。",
    "Aquila": "天鹰座的河鼓二就是「牛郎星」，两侧两颗暗星像它挑着的担子。",
    "Canis Major": "大犬座拥有全天最亮的天狼星；它和猎户座的参宿四、小犬座的南河三组成冬季大三角。",
    "Bootes": "牧夫座像一个风筝（或冰淇淋筒），最亮的大角星是北天最亮的恒星。",
    "Perseus": "英仙座像一个「人」字，其中的大陵五是一颗著名的食变星，亮度会周期性变化。",
    "Taurus": "金牛座有 V 形的脸和两颗长角，最亮的毕宿五是一颗橙色巨星，还有昴星团。",
})


def scale_centre(stars, n):
    pts, seen = [], set()
    for zh, en, (x, y), mag in stars:
        r, c = int(round(y * (n - 1))), int(round(x * (n - 1)))
        if (r, c) in seen:
            return None
        seen.add((r, c))
        pts.append((zh, en, (r, c), mag))
    rows = [p[2][0] for p in pts]; cols = [p[2][1] for p in pts]
    dy, dx = int(round((n - 1) / 2 - (min(rows) + max(rows)) / 2)), int(round((n - 1) / 2 - (min(cols) + max(cols)) / 2))
    out, seen2 = [], set()
    for zh, en, (r, c), mag in pts:
        rr, cc = r + dy, c + dx
        if not (0 <= rr < n and 0 <= cc < n) or (rr, cc) in seen2:
            return None
        seen2.add((rr, cc))
        out.append((zh, en, (rr, cc), mag))
    return out


def ring(n):
    return [(r, c) for r in range(n) for c in range(n)
            if r == 0 or c == 0 or r == n - 1 or c == n - 1]


def evaluate(pl, const_pts, noise, n, rng):
    cs = {rc for _, _, rc, _ in const_pts}
    ms = cs | set(noise)
    d = {
        "id": pl["lid"], "name": f"第 {pl['lid']} 关 · {pl['zh']}", "size": n,
        "mines": [list(rc) for rc in sorted(ms)],
        "noise": [list(rc) for rc in sorted(noise)],
        "showRuns": pl.get("runs", True), "opening": [0, 0], "lives": 3,
        "teach": pl["teach"], "technique": "constellation",
        "theme": {"id": pl["en"].lower().replace(" ", "-"), "name": pl["zh"], "nameEn": pl["en"],
                  "fact": FACTS.get(pl["en"], ""),
                  "stars": [{"name": zh, "en": en, "rc": list(rc), "mag": mag,
                             "tint": ("warm" if zh in ("参宿四", "心宿二") else
                                      ("cool" if zh in ("参宿七", "天津四") else "neutral"))}
                            for zh, en, rc, mag in const_pts],
                  "lines": pl["lines"]},
    }
    d["rowRuns"] = [gl.line_runs([(r, c) in ms for c in range(n)]) for r in range(n)]
    d["colRuns"] = [gl.line_runs([(r, c) in ms for r in range(n)]) for c in range(n)]
    p0 = gl.Puzzle(n, [tuple(m) for m in d["mines"]], (0, 0), True)
    best = None
    for r in range(n):
        for c in range(n):
            if (r, c) in p0.mines or p0.num[r][c] != 0:
                continue
            k = gl.opening_reveal_count(gl.Puzzle(n, [tuple(m) for m in d["mines"]], (r, c), True))
            if best is None or k > best[0]:
                best = (k, r, c)
    if best is None:
        return None
    k, r, c = best
    d["opening"] = [r, c]
    ok, probs, info = gl.check_level(d, static=False)
    return dict(d=d, ok=ok, info=info, k=k, n=n, noise=noise)



def isolated_mines(d, n):
    """没有任何相邻雷的雷数（这类雷常常“看一眼就知道”，会削弱推理感）"""
    ms = {tuple(m) for m in d["mines"]}
    iso = 0
    for (r, c) in ms:
        if not any((r + dr, c + dc) in ms for dr in (-1, 0, 1) for dc in (-1, 0, 1) if dr or dc):
            iso += 1
    return iso

def stats_of(d, n):
    """0 格数量、0 格占安全格比例、开局展开占棋盘比例"""
    ms = {tuple(m) for m in d["mines"]}
    p = gl.Puzzle(n, list(ms), tuple(d["opening"]), True)
    zeros = sum(1 for r in range(n) for c in range(n)
                if (r, c) not in ms and p.num[r][c] == 0)
    safe = n * n - len(ms)
    return zeros, (zeros / safe if safe else 1.0)


def fit(pl, rng, iso_cap=3, require_filled=True):
    """难度由「总雷数（星座星 + 杂星）」控制，而不是把星座做大。
    目标：开局展开别太多、0 格别太多、探格次数落在目标带内。"""
    target_probes = pl["probes"]
    max_open = 0.38
    best = None
    for n in (pl["board"], pl["board"] + 1, pl["board"] + 2):
        # 设计顺序：先按可玩性定盘面密度，再让星座"藏在"满天星里
        dens = min(0.22, 0.18 + 0.004 * pl["lid"])
        target_total = int(round(dens * n * n))
        nk_target = max(0, target_total - len(pl["stars"]))
        base = scale_centre(pl["stars"], n)
        if base is None:
            continue
        cs = {rc for _, _, rc, _ in base}
        # 杂星候选 = 全盘任意非星座格：先按可玩性铺满盘面，星座藏在里面
        ring_c = [(r, c) for r in range(n) for c in range(n) if (r, c) not in cs]
        lo = max(0, nk_target - 2)
        hi = min(len(ring_c), nk_target + 2)
        for nk in range(lo, hi + 1):
            trials = 1 if nk == 0 else 180
            for _ in range(trials):
                noise = set() if nk == 0 else set(rng.sample(ring_c, nk))
                got = evaluate(pl, base, noise, n, rng)
                if not got or not got["ok"]:
                    continue
                info = got["info"]
                zeros, zr = stats_of(got["d"], n)
                if zr > 0.40:            # 0 格太多 = 一开局连锁翻掉大半盘，直接排除
                    continue
                ms_now = {tuple(m) for m in got["d"]["mines"]}
                if require_filled:
                    if not all(any((r, c) in ms_now for c in range(n)) for r in range(n)):
                        continue        # 有空行 = 边缘太空，排除
                    if not all(any((r, c) in ms_now for r in range(n)) for c in range(n)):
                        continue        # 有空列，同上
                iso = isolated_mines(got["d"], n)
                if iso > iso_cap:              # 孤立雷超过 3 个就“看一眼就知道”，排除（优先压到 1–2 个）
                    continue
                open_ratio = got["k"] / (n * n)
                if open_ratio > max_open:          # 一开局就翻开太多 → 免谈
                    continue
                # 后段星座很难同时满足所有约束：只设下限，靠近目标带靠打分
                if info["reveal_actions"] < max(18, target_probes[0] - 8):
                    continue
                # 打分：探格落在目标带 > 0 格少 > 星图线索贡献 > 杂星少
                in_band = 1 if info["reveal_actions"] <= target_probes[1] else 0
                dist = abs(info["reveal_actions"] - (target_probes[0] + target_probes[1]) / 2)
                score = (in_band, -iso, -zr, -abs(nk - nk_target), -abs(dist) / 10.0, min(info["runs_cells"], 16))
                if best is None or score > best[0]:
                    best = (score, got, zeros, zr)
            if best and best[0][0] == 1 and best[0][1] <= -0.30:
                break
    return best


def main():
    rng = random.Random(20261021)
    out = []
    for pl in PLAN:
        best = None
        used_cap = None
        # 松紧阶梯：先满足"无空行空列 + 孤立雷少"，压不住再逐级放宽（可玩性优先）
        for filled, cap in ((True, 2), (True, 3), (False, 2), (False, 3), (False, 4)):
            best = fit(pl, rng, iso_cap=cap, require_filled=filled)
            if best is not None:
                used_cap = cap if not filled else str(cap) + "/满"
                break
        if best is None:
            # 找不到合格摆法就截断（不拿不合格关卡凑数），并如实报告停在哪个星座
            print(f"!! 第 {pl['lid']} 关 {pl['zh']} 在约束下无合格摆法，生成到此截止")
            break
        got, zeros, zr = best[1], best[2], best[3]
        d, info, n = got["d"], got["info"], got["n"]
        nb = "必须用星图线索" if not info["nb_only_ok"] else "数字即可解"
        print(f"第 {pl['lid']:2d} 关 {pl['zh']:6s} {n}×{n} 星{len(d['theme']['stars']):2d} "
              f"杂{len(d['noise']):2d} 雷{len(d['mines']):2d} 探格{info['reveal_actions']:2d} "
              f"雷{len(d['mines']):2d} 杂{len(d['noise']):2d} 0格{zeros:2d}({zr*100:.0f}%) 孤立{isolated_mines(d, n):d}(上限{used_cap}) 展开{got['k']:2d}/{n*n} 星图{info['runs_cells']:2d} {nb}")
        out.append(d)
    if len(out) < 3:
        print(f"!! 只生成了 {len(out)} 关，为保护现有数据，不覆盖 tools/levels.json")
        return
    json.dump(out, open(os.path.join(ROOT, "tools", "levels.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ 已写出 tools/levels.json（{len(out)} 关）")


if __name__ == "__main__":
    main()