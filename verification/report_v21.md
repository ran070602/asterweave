# 星织 · 阶段性独立复核报告 v21

复核者：独立复核子代理（**未 import/复制** `tools/` 下任何生成器或校验器代码，校验器全部本轮独立实现）
时间 2026-10-23（Asia/Shanghai）；工作目录 `D:\AI-Native casual game`（junction `D:\Asterweave`，同一份目录）
项目尚未完成 → 本报告只给可信基线。原始输出：`verification/v21_*.{py,js,json}`、`verification/logs/v21_*.txt`。

## 0. 基线与 sha256（重要：基线在复核过程中移动过）

| 文件 | 11:26 冻结 `frozen_v21/` | 12:06 现行 `frozen_v21b/`（**本报告最终基线**） |
|---|---|---|
| dist/星织-游戏本体/index.html | 20F5173FB2BAE00D（418613 B） | AD05D8E9D7C6AAEF（419446 B） |
| index.html（根） | 20F5173FB2BAE00D | AD05D8E9D7C6AAEF |
| 星织-游戏本体.zip | 7D2FDD602756DEF5（62841 B） | 22920210682F3BEA（63044 B） |
| dist/build_manifest.json | 97669C5FB892B247 | A8F117EED25847D2 |
| game/index.html | —（未冻结） | 44A8CF8DFAF275DD |
| tools/levels.json · sky.json · level_stats.json | 0DA0E18EC009AE7B · 3EBE8A0FE93A49E0 · C1AA37AA0B10CA13（两版相同，未变） | 同左 |
| docs/SPEC.md · 设计思路 · 迭代优化 | 8512BB5F5AA0D600 · 2E7A325EE857DC64 · 3EE654B175ABF8F7（未变） | 同左 |

12:05–12:06 有人重建了发布物。两版差异**仅在 CSS**（JS 逻辑区逐字节相同）：12:06 版补回了 11:26 版**缺失**的
`.overlay{position:fixed;inset:0;…;opacity:0;visibility:hidden}` 基础规则（11:26 版结算遮罩样式是坏的），并清掉一行溢出到 `@media` 前的孤儿 CSS。
A–G 已在 12:06 基线上全部重跑，结论与 11:26 版一致。
复现冻结：`Copy-Item 'dist\星织-游戏本体\index.html' verification\frozen_v21b\dist_index.html -Force`

## A. 数据自洽 —— 通过
`python verification/v21_a_data.py`（`logs/v21_a.txt`）。50 关 `rowRuns`/`colRuns` 由 `mines` 重算后逐行逐列一致；
`theme.stars ⊆ mines`、`noise ⊆ mines`、`noise ∩ stars = ∅`；`opening` 非雷且 8 邻无雷；L1 `showRuns=false`、L2–50 `true`；`lives` 全 3；`id` 1..50 连续；
内嵌 `const LEVELS`（`/* LEVELS_INJECT_START..END */`）与 `tools/levels.json` deep-equal。
证据：`A 关数=50  theme.id 唯一=50` / `A 内嵌==levels.json : True` / `A 失败项 0` / `A_VERDICT PASS`

## B. 可解性（50 关零猜测） —— 通过
`python verification/v21_b_solve.py`（`logs/v21_b.txt`；明细 `v21_out_b.json`、`v21_solution.json`）。
自写求解器 = 邻域计数传播（`d==|F|`→余下安全、`d-|F|==|U|`→余下是雷）+ 数织行列枚举（逐行/列枚举满足 runs 与已知约束的全部放置，全票定雷/定安全）+ flood fill 到不动点；L1 按契约禁用行列表举。
证据：`B 可解 50/50`、`B 第1关 仅邻域推理（禁用行列枚举）：ok=True … revealed=29/29`、无 no-placement/conflict/loop-guard、`B_VERDICT PASS`

## C. 难度指标（独立统计） —— 通过
`python verification/v21_c_metrics.py`（`logs/v21_c.txt`）。口径：开局展开 = 从 `opening` 起的 0 格连通块 / n²；0 格占比 = 全盘 count==0 格 / n²。

| 口径 | 实测 | 判定 |
|---|---|---|
| 尺寸 ≤11 | max 11 | 通过 |
| 开局展开 ≤38%（分母 n²） | max 33.0%（L36） | 通过 |
| 0 格 ≤40%（分母 n²） | max 28.9%（L20） | 通过 |
| 孤立雷 ≤2 | max 2 | 通过 |
| 前五关无空行空列 / 50 关无空行空列 | 全 0 | 通过 |
| 雷密度 15–25%（附加） | 18.4–24.0% | 通过 |
| `level_stats.json` 逐关对账（size/mines/stars/noise/iso/isEmpty/showRuns/zr） | 50/50 全对 | 通过 |

注：`探格`（`level_stats.probes`）与我的求解器 reveal_actions 在 18 关上不同（最大 L15：39 vs 31），是推导顺序不同，非数据不一致。

## D. 运行时（自写 DOM 桩，vm 直跑 dist 内联脚本） —— 通过
桩 `verification/v21_stub.js`（自写 HTML 解析 + Element/EventTarget/closest/classList + 虚拟时钟 + localStorage + matchMedia；`vm.createContext` 跑 IIFE，只经公开 DOM/事件驱动）；测试 `v21_d_dom.js`（`logs/v21_d.txt`、`v21_out_d.json`）——**20/20 PASS**。
- **D1**：按我独立求解器的推理顺序点击（`v21_solution.json`），**50/50 关玩到 `status="won"`**；揭晓后 `lit` 格 == `theme.stars.length`、`#boardReveal line` == `theme.lines.length`、`wonoise` 格 == `noise.length`、模态 `.gstar/.gline/.gnoise` 三者全等、`noise ∩ 星座星 = ∅`、modal 均弹出。
- **D2 现行交互**：`D2a` 触摸轻触 `revealed 11→15`（pointerup 内即时、未推进时钟）；`D2b` 长按 200ms 未标记 / 400ms 已标记、抬起不再观测；`D2c` 长按雷位 `flagged=true` 且 `lives 3→3`；`D2d` 鼠标左键 `15→16`；`D2e` 右键 `flagged 2→3` 且未观测；`D2f/f2` 两次左键 / 两次轻触后 `flagged=0`（无双击标记）；`D2g` 源码 `DBL_MS=0`、`lastMouse=0`、棋盘无 `dblclick` 监听。
- **D3 界面**：`D3a` staticIndex `lvtag=334 < actHint=336 < board=360` 且同父（actHint 紧跟「第 N/50 关」行、在棋盘正上方）；`D3b` 文案 `📱 轻触 = 🔭 观测　长按 = ★ 标记　｜　💻 单击 = 🔭 观测　右键 = ★ 标记`（无「双击」）；`D3c` 首屏说明 3 句、仅首次第 1 关弹一次、关闭后 `introSeen=true` 落盘、二次启动不弹、重置进度不弹；`D3d` 失败结算条 = `["↻ 重来本关","换个关卡"]`；`D3e` 通关结算条 = `["★ 图鉴详情","↻ 重来本关","下一关 →"]`；`D3f` 进行中常驻「↻ 重玩本关」可见、结算时（通/败）hidden=true；`D3g` 全库无任何文案为「结算」的按钮（17 处「结算」全在注释）。
- **D4**：`D4a` 「全部解锁」一次点击可用关卡 `1→50`；`D4b` `dataset.gameState` 13 字段齐全（level,levelId,size,revealed,totalSafe,flagged,mines,lives,status,mode,totalLevels,clearedLevels,noise）；`D4c` playing 时无 `wonstar/wonoise/hitstar/hitnoise`、无杂星 SVG、`#boardReveal` 空、结算区与图鉴 modal 空；`D4d` 踩雷后只亮被踩的那 1 颗。
⚠ 契约措辞：实现里不存在名为「结算」的按钮 → 「通关结算条保留『结算』与『下一关』」字面无法对应（实质满足）。复现：`node verification/v21_d_dom.js`

## E. 图鉴 —— 通过
`python verification/v21_e_sky.py`（`logs/v21_e.txt`）+ `node verification/v21_e_dom.js`（`logs/v21_e_dom.txt`，4/4 PASS）。
数据：内嵌 `SKY` == `tools/sky.json`；50 个 id 唯一；`LEVELS[i].theme.id ↔ SKY[].level` 双向一致且 level 唯一覆盖 1..50；中文名一致；相邻星座 id/level 都落在 SKY 内。
运行时：六种进度态（0/1/7/25/49/50 关通关）`#skyCount` = 0/1/7/25/49/50 == 实际通关数、`#skyTotal` 恒 50；未通关星座详情 `gstar=gline=gnoise=0`、无 `data-jump`、无 `sky-fact`、不出现任何其它星座名；已通关 crux `gstar/gline/gnoise = 4/2/3` == `stars/lines/noise` 且有 fact；地图未观测节点只出 `.lbl.off` 暗名、无星图 SVG。

## F. 通关动画 —— 通过（含 2 处死代码）
`node verification/v21_f_anim.js`（`logs/v21_f.txt`，7/7 PASS）。静态：`checkWin` 顺序 `status='won' → markCleared → winRevealDone=false → winRevealPending=true → render() → startBoardReveal(alreadyCleared)`；`renderModal()` 首行 `if (winFlashPending || winRevealPending){ closeModal(false); return; }`。
运行时（L1）：制胜瞬间 modal 未弹（`overlay.open=false`、`#modalBtns` 空）、`#board` 已挂 `reveal-stage`；约 490ms 星座星首次 `lit`，连线 DOM 立即注入（CSS `animation-delay` 延时），**约 2115ms 才弹 modal**；重玩已通关 ≈1030ms；`prefers-reduced-motion` 直接落终态（0–5ms 弹窗、连线齐全）；揭晓中按 Enter 可跳过。
⚠ 死代码：`winFlashPending` 全库从未被赋 true（提前返回实际靠 `winRevealPending`）；`.board.reveal-flash`（CSS `winStarFlash`）从未被 JS 添加，「闪一下」实际由 `.reveal-stage .cell.wonstar.lit{animation:starGlow}` 实现。契约写「约 900ms」，实测首通 ≈2.1s、重玩 ≈1.0s。

## G. 发布包 —— 通过
`python verification/v21_g_release.py`（12:06 基线 → `logs/v21_g.txt`；冻结基线 `V21_BASE=frozen` → `logs/v21_g_frozen.txt`，两者同判 PASS）。
ZIP 根条目恰为 `index.html` + `README.txt`（无子目录；README.txt 2547 B / sha `a12c6b77c290d60f`）；ZIP 内 `index.html` sha256 == dist；根 `index.html` sha256 == dist；外部引用全 0（`http(s)://` / `fetch(` / `XMLHttpRequest` / `WebSocket` / `<link` / `<img` / `import(` 各 0），`url(` 2 次且均为内联 SVG 片段引用 `url(#skyMw)`、`url(#skyVig)`；`node --check` 内联脚本通过；`build_manifest.json` 的 ui/levels/build/zip sha256、zip_bytes、html_bytes、level_count 逐项一致，`zip_root_entries` 与 5 个 `checks` 独立复核为 true。

## H. 文档对账 —— 表格全对；正文 6 处陈旧数字（不通过项仅为文档）
`python verification/v21_h_docs.py`（`logs/v21_h.txt`）。
- **逐格 0 差异**：设计思路 L170 起 50 行表、迭代 L117 起 50 行表（关/星座/棋盘/星座星/杂星/总雷/探格次数/数织线索贡献），行数为 50、关号 1..50、8 列每格均等于 `levels.json` + `level_stats.json`；两表末列（只用数字能解？/ 必须用星图线索？）与 `level_stats.nb_only` 0 处不符；「50 关里 45 关必须用星图线索」与实测完全一致（`nb_only=true` 仅 [1,5,8,16,23]）；SPEC 现行交互七要素齐全且与契约一致。
- **文档说 X、实测 Y（6 处）**：① 设计思路 L226 / 迭代 L187「探格 19–47 次」→ 实测 **11–49**（L1=11、L48=49）；② 设计思路 L226「全 50 关棋盘 7×7–11×11」→ 实测 **6×6–11×11**（同句自己又写「第 1 关现在是 6×6」）；③ 设计思路 L165 / 迭代 L109「雷密度 15.6%–24.0%，均值 21.6%」→ 实测 **18.4%–24.0%，均值 21.5%**；④ 同处「杂星 6–22 颗 / 第 1 关 6 颗」→ 实测 **3–22，L1=3**；⑤ 设计思路 L77 / SPEC §3「第 2 关数织贡献 12 格、第 10 关 10 格 / L2 ≥5（实测 12）」→ 实测 **L2=3、L10=14**（两文档自己的表也写 L2=3）；⑥ SPEC 标题 **v1.7** 而正文修订只到 **v1.4**（缺 v1.5–v1.7），§2/§3 仍按「10 关初版」写实例数字（尺寸 6→7→8、`showRuns` 第 1–3 关 false、teach 只 1/2/6 关）→ 实测 6×6–11×11、仅 L1 `showRuns=false`、teach 非空 **4 关 [1,2,6,12]**。（SPEC 已声明实例数字不构成契约，故 ⑥ 属陈旧而非违约。）

## 总体判定：**不通过**（无硬缺陷；不通过项全部落在文档与措辞）
A/B/C/D/E/F/G 七项**全部通过**：数据自洽、50 关零猜测可解、难度口径达标、50 关运行时全部可通关、现行交互四条路径正确、界面细节符合、图鉴不泄露、发布包自包含且 manifest 对齐。
可信基线 `verification/frozen_v21b/`（12:06 版，sha256 见 §0）；不通过清单见下。

## 仍不通过清单
1. H-⑤：设计思路 L77 与 SPEC §3「第 2 关数织贡献 12 格」与实测（3 格）冲突，且与两文档自己的表冲突 —— 唯一会误导难度判断的一条。
2. H-①②③④：设计思路 L165/L226 与迭代 L109/L187 的探格区间、棋盘下限、雷密度区间、杂星下限共 4 处数字停留在旧数据版本。
3. H-⑥：SPEC 标题 v1.7 与正文修订记录（止于 v1.4）不一致；§2/§3 的 10 关初版实例数字已过期。
4. F：`winFlashPending` 从未置 true、`.reveal-flash` 从未被添加（契约点名的两个动画开关是死代码）。
5. 契约措辞：不存在「结算」按钮（通关结算条为 图鉴详情 / 重来本关 / 下一关 →）。
6. 基线风险（非代码缺陷）：复核期间发布物被重建一次，任何哈希类结论都有保鲜期。

## 给开发者的 top 3 修改建议（按优先级）
1. **改掉文档旧数字，并让正文区间数字自动生成**：按 H 清单 1–2 更新 6 处（探格 11–49、棋盘 6×6–11×11、密度 18.4–24.0%/均值 21.5%、杂星 3–22/L1=3、L2 数织贡献 3、L10=14），最好让 `tools/sync_docs_tables.py` 连正文数字一起生成，避免下次调关卡再脱节。
2. **补 SPEC 版本纪律**：在修订行补 v1.5/v1.6/v1.7（长按标记、结算条按钮区分、第 1 关 6×6 与前五关调松），并把 §2/§3 的「10 关初版」实例数字改成「以 `tools/levels.json` 为准」或同步刷新。
3. **清死代码或让它真生效**：要么真正置 `winFlashPending=true` 并给棋盘加 `reveal-flash`，要么删掉两者，让「提前返回 + 闪一下」只有一条实现路径；同时把契约里的「结算」按钮描述改成实际按钮名（图鉴详情 / 重来本关 / 下一关 →）。

## 复现
`python verification/v21_{a_data,b_solve,c_metrics,e_sky,g_release,h_docs}.py`；`node verification/v21_{d_dom,e_dom,f_anim}.js`
（`V21_HTML` 切换 dist 版本，`V21_BASE=frozen|live` 切换 G 基线）。
