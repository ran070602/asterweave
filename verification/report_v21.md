# 星织 · 阶段性独立复核报告 v21

复核者：独立复核子代理（未 import 任何 tools/ 生成器代码；校验器均为本轮独立实现）
时间：2026-10-23（Asia/Shanghai） 工作目录：`D:\AI-Native casual game`（junction `D:\Asterweave`，同一份目录）
说明：项目**尚未完成**，本报告只给可信基线；结论边验边落盘。全部原始输出见 `verification/v21_*`、`verification/logs/v21_*.txt`。

## 0. 冻结副本与 sha256（`verification/frozen_v21/`）

| 文件 | sha256（前 16 位） | bytes |
|---|---|---|
| dist/星织-游戏本体/index.html | 20F5173FB2BAE00D | 418613 |
| index.html（根） | 20F5173FB2BAE00D | 418613 |
| 星织-游戏本体.zip | 7D2FDD602756DEF5 | 62841 |
| tools/levels.json | 0DA0E18EC009AE7B | 261739 |
| tools/sky.json | 3EBE8A0FE93A49E0 | 66489 |
| tools/level_stats.json | C1AA37AA0B10CA13 | 14704 |
| dist/build_manifest.json | 97669C5FB892B247 | 836 |
| docs/SPEC.md | 8512BB5F5AA0D600 | 14476 |
| 冉政-设计思路文档.md | 2E7A325EE857DC64 | 24882 |
| 冉政-迭代优化过程文档.md | 3EE654B175ABF8F7 | 53712 |
| README.md | 668E4B51342AFA68 | 4521 |

复现冻结：
```powershell
New-Item -ItemType Directory -Force verification\frozen_v21
Copy-Item 'dist\星织-游戏本体\index.html' verification\frozen_v21\dist_index.html -Force
```

## A. 数据自洽 —— **通过**

命令：`python verification/v21_a_data.py`（日志 `verification/logs/v21_a.txt`）
逐关核验 50 关：`rowRuns`/`colRuns` 由 `mines` 重算后逐行逐列一致；`theme.stars ⊆ mines`、`noise ⊆ mines`、`noise ∩ stars = ∅`；
`opening` 非雷且 8 邻无雷（安全 0 格）；L1 `showRuns=false`、L2–L50 `true`；`lives` 全为 3；`id` 1..50 连续。
证据：`A 关数=50  theme.id 唯一=50` / `A 内嵌==levels.json : True` / `A 失败项 0` / `A_VERDICT PASS`
内嵌比对方式：截取 dist 内联脚本 `/* LEVELS_INJECT_START..END */` 中的 `const LEVELS = [...]` 反序列化后与 `tools/levels.json` deep-equal。

## B. 可解性（50 关零猜测） —— **通过**

自写求解器 `verification/v21_b_solve.py`：邻域计数传播（`d==|F|` → 余下安全；`d-|F|==|U|` → 余下是雷）+
数织行列枚举（逐行/逐列枚举满足 runs 与已知约束的全部放置，全票定雷/定安全）+ flood fill 到不动点；
L1 按契约禁用行列枚举（`showRuns=false` → `use_runs=False`）。判定：全部安全格被逻辑推出 → 可解。

命令：`python verification/v21_b_solve.py`（日志 `logs/v21_b.txt`，明细 `v21_out_b.json`、`v21_solution.json`）
证据：`B 可解 50/50`，`B 第1关 仅邻域推理（禁用行列枚举）：ok=True ... revealed=29/29`，`B_VERDICT PASS`
无 `no-placement` / `conflict` / `loop-guard` 报错。

## C. 难度指标（独立统计） —— **通过**

命令：`python verification/v21_c_metrics.py`（日志 `logs/v21_c.txt`）
口径取值：开局展开 = 从 `opening` 起的 0 格连通块（flood fill 到不动点）/ n²；0 格占比 = 全盘 count==0 的安全格 / n²。

| 口径 | 实测 | 判定 |
|---|---|---|
| 尺寸 ≤11 | max = 11 | 通过 |
| 开局展开 ≤38%（分母 n²） | max = 33.0%（L36） | 通过 |
| 0 格 ≤40%（分母 n²） | max = 28.9%（L20） | 通过 |
| 孤立雷 ≤2 | max = 2 | 通过 |
| 前五关无空行空列 | (1..5) 空行/空列全 0 | 通过 |
| 50 关全部无空行空列 | 全部 0 | 通过 |
| 雷密度 15%–25% | 18.4%–24.0% | 通过（附加） |
| `level_stats.json` 逐关字段对照 | 50 关全对（size/mines/stars/noise/iso/isEmpty/showRuns/zr） | 通过 |

注：`探格`（level_stats.probes）与我的独立求解器的 reveal_actions 在 18 关上不同（最大差 L15：39 vs 31），
差值是求解器策略（批量推导顺序）不同所致，不属于数据不一致；报告 H 只核「文档数字 == 文件数字」。

## D. 运行时（自写 DOM 桩，vm 直跑 dist 内联脚本） —— **通过**

桩：`verification/v21_stub.js`（自写 HTML 解析 + Element/EventTarget + 虚拟时钟 + localStorage + matchMedia；
用 `vm.createContext` 跑 dist 的 `<script>` IIFE，只经公开 DOM 与事件驱动，无任何内部变量访问）。
测试：`verification/v21_d_dom.js`（日志 `logs/v21_d.txt`，原始 `v21_out_d.json`）——**20 项全通过**。

- **D1 50 关逐关玩到 `status="won"`**：按我独立求解器给出的推理顺序点击（`v21_solution.json`），
  50/50 关 `status=won`；揭晓后 `lit` 格 == `theme.stars.length`、`#boardReveal line` == `theme.lines.length`、
  `wonoise` 格 == `noise.length`、模态 `.gstar/.gline/.gnoise` 三者相等、`noise ∩ 星座星 = ∅`、modal 均正常弹出。
  证据：`PASS D1 50/50 关通过，lit=stars, boardLines=lines, wonoise=noise, gstar/gline/gnoise 全等，modal 均打开`
- **D2 现行交互四条路径**（`v21_out_d.json`）：
  `PASS D2a` 触摸轻触 → `revealed 11 -> 15`（同一 pointerup 内、未推进时钟，即时）；
  `PASS D2b` 长按：200ms 未标记 / 400ms 已标记；抬起后 `revealed=false`（长按后抬起不再观测）；
  `PASS D2c` 长按雷位：`mineFlagged=true`，`lives 3->3`（不扣命）；
  `PASS D2d` 鼠标左键单击 → `revealed 15 -> 16`；
  `PASS D2e` 鼠标右键 → `flagged 2 -> 3` 且未观测；
  `PASS D2f/D2f2` 两次左键 / 两次轻触后 `flagged=0`（双击不产生标记）；
  `PASS D2g` 源码 `DBL_MS=0`、`lastMouse=0`、棋盘无 `dblclick` 监听。
- **D3 界面细节**：
  `PASS D3a` `staticIndex` lvtag=334 < actHint=336 < board=360，且 lvtag/actHint 同父（actHint 紧跟「第 N/50 关」行、在棋盘正上方）；
  `PASS D3b` 文案 `📱 轻触 = 🔭 观测　长按 = ★ 标记　｜　💻 单击 = 🔭 观测　右键 = ★ 标记`（无「双击」）；
  `PASS D3c` 首屏说明 3 句、仅在首次第 1 关弹一次、关闭后 `introSeen=true` 落盘、二次启动不弹、重置进度后不弹；
  `PASS D3d` 失败结算条按钮 == `["↻ 重来本关","换个关卡"]`（无「结算」按钮），常驻重玩按钮隐藏；
  `PASS D3e` 通关结算条按钮 == `["★ 图鉴详情","↻ 重来本关","下一关 →"]`（保留「下一关」），常驻重玩按钮隐藏；
  `PASS D3f` 进行中常驻「↻ 重玩本关」可见；`PASS D3g` **全库不存在任何文案为「结算」的按钮**（17 处「结算」全在注释里）。
  ⚠ 口径提示：契约写「通关结算条保留『结算』与『下一关』」，实现里没有名为「结算」的按钮 —— 实质（保留入口 + 下一关）满足，字面不一致，属契约措辞问题。
- **D4**：`PASS D4a` 「全部解锁」一次点击可用关卡 `1 -> 50`；
  `PASS D4b` `dataset.gameState` 13 字段齐全（level,levelId,size,revealed,totalSafe,flagged,mines,lives,status,mode,totalLevels,clearedLevels,noise）；
  `PASS D4c` playing 时无任何 `wonstar/wonoise/hitstar/hitnoise`、无杂星 SVG、`#boardReveal` 空、结算区/图鉴 modal 空；
  `PASS D4d` 踩雷后只有被踩的 1 颗亮出，其余雷位不泄露。
  复现：`node verification/v21_d_dom.js`



