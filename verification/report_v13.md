# 星织 / Asterweave — v13 独立复核报告

复核者：独立复核 agent（未复用 tools/ 下任何生成器代码；求解器/统计/DOM 桩均本轮自写）
工作目录：`D:\AI-Native casual game`（= junction → `D:\Asterweave`，同一棵树）
Python：`C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`；Node：`D:\develop\NodeJS\node.exe`
冻结副本：`verification/frozen_v13/`；日志：`verification/logs/v13_*.txt`

## 0. 冻结指纹（sha256）
| 对象 | 字节 | sha256（前 16） |
|---|---|---|
| dist/星织-游戏本体/index.html | 416953 | b56232f98ac24534 |
| 星织-游戏本体.zip | 55011 | 8ec0cec5a5bad592 |
| tools/levels.json | 263588 | 4e4f0d479113b41d |
| docs/SPEC.md | 12881 | d765c7b004a2641c |
| 冉政-设计思路文档.md | 24407 | 3138ca7c02d466a1 |
| 冉政-迭代优化过程文档.md | 43128 | c6955db49d3bdb19 |
| game/index.html（模板） | 90064 | 73405b04cab832b0 |
| README.md | 4111 | 465b462d8866afa3 |
注：README.md 于 16:10:55 被改写（复核开始后 53s），上表为其当时快照；`dist/`、`game/`、`tools/levels.json`、两份冉政文档均在 16:03–16:10 定稿后未再变动（复核期间 hash 复测一致）。

## A. 数据自洽 — **通过**
命令：`python verification/v13_a_data.py`（日志 `verification/logs/v13_a.txt`）
- 50 关齐备；`id` 与序号一致；`mines` 无重复/越界（`len(mine)==len(mines)` 全关成立）。
- `rowRuns`/`colRuns` 由 `mines` 独立重算后逐关逐行/列全等（50×2 组，0 处不符）。
- `noise ⊆ mines`、`noise ∩ theme.stars = ∅`、`theme.stars ⊆ mines`、星坐标无重复、星名无重复、`lines` 下标合法且无自环——全部 50 关成立。
- `opening` 均为非雷格且邻域雷数 == 0（50/50）。
- `showRuns`：第 1 关 `false`，第 2–50 关 `true`（50/50）。
- HTML 内嵌 `const LEVELS` 与 `tools/levels.json`：结构等价 **且** 规范化空白后的文本逐字节相同（唯一一处 `const LEVELS = [`，注入块 `/* LEVELS_INJECT_START */`…`_END */`）。
- 星座唯一性：50 关 `theme.id` / `theme.name` 互不重复（0 冲突）。

## C. 难度指标（独立统计） — **通过**
口径：展开占比 = 开局 flood fill 后已翻开安全格 / n²；0 格占比 = 邻域雷数 0 的格数 / n²；孤立雷 = 8 邻域内无其它雷的雷。
- 尺寸集合 `{7,8,9,10,11}`，最大 11 ≤ 11（50/50）。
- 雷密度 15.6%–24.0%（第 1 关 15.6%，其余 18.5%–24.0%，均值 21.6%）。
- 展开占比 11.1%–33.0%（最大第 36 关 33.0%）≤38%；0 格占比 11.1%–30.0%（最大第 25 关 30.0%）≤40%；孤立雷 0–2 个 ≤2（第 22/25/26/28 关为 2，其余 0–1）。
- 阈值超出项：**0**。
- 备选口径（分母换成"安全格"）会令第 9/28/36 关展开占比变为 38.1%/39.6%/42.9% 而超线；本报告采用项目文档口径（分母 n²，与"雷密度"同分母），并在此显式记录该口径敏感性。

## B. 可解性（50 关逐关零猜测） — **通过**
命令：`python verification/v13_b_solve.py`（日志 `verification/logs/v13_b.txt`，播放序列 `verification/v13_play.json`）
求解器自写规则：R1 邻域计数传播（未翻开邻居数 == 剩余雷数 → 全雷；剩余 0 → 全安全）+ R2 数织行列枚举（枚举与已知雷/已知安全相容的全部连续块摆法，全摆法一致的格才判定）+ R3 flood fill；三者交替到不动点，任何一步若无可证明的格子即判不可解（绝不猜）。
- **可解 50/50，不可解 0**；每一步判定均与真值 `mines` 校验一致（无误判）。
- **第 1 关**：`showRuns=false` → 求解器禁用 R2，仅 R1+R3 即可通关（`仅邻域推理可解=True`）。
- 交叉验证文档主张：仅靠邻域计数（不用数织线索）可通关的只有 **4/50**（第 1、8、16、23 关），即 **46/50 必须用数织线索**——与迭代文档"50 关里有 46 关重新变成必须用星图线索"完全吻合。
- 探格次数（本求解器口径：优先探 0 格、已被连锁翻开的格不重复计动作）：**17–51** 次（第 1 关 26 次）。

## D. 运行时（自写 DOM 桩，Node 直跑 dist 内联脚本） — **通过**
命令：`node verification/v13_d_dom.js`（日志 `verification/logs/v13_d.txt`；107 项断言，100 通过 / 4 不通过全部落在 E / 3 记录项）
- **50 关全部玩到 `status="won"`**（`won=50 lost=[] stuck=[]`），全程零踩雷、`revealed == totalSafe`、`flagged == mines`；每关 `dataset.gameState` 的 `level/size/revealed/totalSafe/flagged/mines/lives/status/mode/totalLevels/clearedLevels/noise` 字段齐全。
- **揭晓图逐关断言通过**：星座星数 == `theme.stars.length`、连线数 == `theme.lines.length`、杂星暗点数 == `noise`（去重后）、杂星坐标与星座星坐标无重叠——50/50 关成立（棋盘揭晓类名 `wonstar`/`wonoise` 计数同样吻合）。
- 第 1 关 `lvtag` 显示「仅邻域数字」（`showRuns=false`），第 2 关显示「含行列线索」。
- 按钮文案：`<title>星织 Asterweave · 50 关</title>`；`modeDig`=「🔭 观测」、`modeFlag`=「★ 标记」、`skyBtn`=「✦ 图鉴」。
- `status!=="won"` 时 DOM 不泄露雷位：未翻开未插旗的格子 `textContent`/`innerHTML` 全空；棋盘无 `wonstar/wonoise/hitstar/hitnoise` 类名；`board.innerHTML` 不含 `mines`/`noise` 字样。通关前揭晓态永不出现。
- 失败路径：连踩 3 颗星 → `status="lost"`、`lives=0`、结算标题「观测失败」、命数图标仍为 3 槽。
- **「全部解锁」按钮一次点击即生效（本轮修过的 bug）**：打开关卡面板后只点 1 次 `#unlockBtn`，禁用按钮数 49→0 且 `progress.devUnlock=true`、文案变「🔒 恢复进度锁」；再点 1 次恢复锁（disabled 回到 49）。监听器已提到 `resetBtn` 回调外（`dist` 第 24009 行 `document.getElementById('unlockBtn').addEventListener('click', toggleUnlockAll);`）。
- 键盘契约：`Enter` 触发探格仍有效；Esc 依次关 结算→星座卡→图鉴→关卡面板。

## E. 新增图鉴页 — **不通过**（页面能开能关，但索引数据有 3 处错标，导致计数错位 + 未通关星座泄露星图）
- 具备：`#skyBtn`「✦ 图鉴」、`#skyPanel`（`skyCount`/`skyTotal`/`skyFilters`/`skyLitBtn`/`#skyMap`/`#skyDetail`/`#constModal`）；`game/index.html` 同样具备（模板 SKY=[]）。
- 开关正常：点 `#skyBtn` 打开（`hidden=false`、`class` 含 `open`）、再点或 `#skyCloseBtn` 或 Esc 关闭；天球图渲染 **50 个** `skynode`，节点只含赤经赤纬投影，不内嵌星图坐标。
- 契约未破：打开图鉴后 `dataset.gameState` 字段完整、棋盘键盘可用、遮罩/焦点逻辑照旧。
- **缺陷 1（计数错位）**：`SKY` 的 `level` 字段有 3 处错标 + 4 处缺号 —— `ophiuchus`(蛇夫座) 标 21（实为 29）、`carina`(船底座) 标 22（实为 26）、`hydra`(长蛇座) 标 23（实为 30），于是 `level ∈ {21,22,23}` 各出现 2 条、`26/29/30` 无条目（50 条只覆盖 46 个关号）。`skyCount = SKY.filter(level 已通关).length` 因此不等于实际通关数：**实测 cleared=2（只通关第 1、21 关）时 `skyCount=3`**；按此推算 frontier 在 22–30 时 `skyCount` 会比真实通关数多 1–3（把 3 个未到达的星座提前点亮）。100% 通关（cleared=50）时恰好又相等，所以只在中间进度暴露。
- **缺陷 2（未通关泄露星图 + 张冠李戴）**：`skyDetailHtml` 用 `LEVELS[s.level-1]` 取星图。仅通关第 1、21 关时，点选**未通关**的「蛇夫座」→ 卡片自称「第 21 关 · 已观测」并**渲染出完整星图**（9 颗 `gstar`），坐标集合与**摩羯座**（第 21 关真实星座）完全一致，事实文案也是摩羯座的（"摩羯座像一个倒三角…"）。即：星图既泄露了未通关星座的揭晓内容，又挂错了名字；同理 `carina`/`hydra` 也会提前 4/7 个关卡点亮。真正到第 26/29/30 关时，「图鉴 +1」奖励失效（已在 22/21/23 关领过）。
- 未受影响的部分：`eridanus`（第 50 关，未通关）等**正常条目**不泄露——只显示「未观测」+「第 50 关 · 通关后点亮」+ 坐标/天区元信息，无 `gstar/gline/gnoise`。所以泄露只发生在上述 3 条错标条目上。

## F. 通关动画 — **通过**（静态 + 运行时都确认）
- 静态：`checkWin()` 里 `S.status='won'` 后置 `winFlashPending = true`、给棋盘加 `reveal-flash`，再 `setTimeout(..., reduce ? 120 : 900)`；`renderModal()` 首行 `if (winFlashPending){ closeModal(false); return; }` —— 即**先点亮星座闪一下、约 900ms 后才弹 modal**（`prefers-reduced-motion` 下降为 120ms）。
- 运行时（DOM 桩虚拟时钟）：通关瞬间 `overlay` 未打开且棋盘 `class` 含 `reveal-flash`；推进到 ~880ms 仍未弹；再推进 40ms 后 `overlay open`；随后 `reveal-flash` 被移除。

<!-- APPEND -->

