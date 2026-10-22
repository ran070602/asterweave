# 星织 / Asterweave — v13 独立复核报告

复核者：独立复核 agent（未 import / 未复制 `tools/` 下任何生成器代码；求解器、统计、DOM 桩、发布包与文档对账脚本均本轮自写）
工作目录：`D:\AI-Native casual game`（是 junction → `D:\Asterweave`，同一棵树）
环境：Python `C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`；Node `D:\develop\NodeJS\node.exe`（无 npm、零安装）
冻结副本 `verification/frozen_v13/`；日志 `verification/logs/v13_*.txt`；原始输出 `verification/v13_out_*.json`

## 0. 冻结指纹与"发布包在复核期间被改过"的事实
**以下结论全部针对 16:24:25 这一版；该版自 16:24:25 起至 16:26:52 连续 3 次复测未再变动（sha 稳定）。**

| 对象 | 字节 | sha256（前 16） |
|---|---|---|
| dist/星织-游戏本体/index.html | 416953 | b70363c501434395 |
| 星织-游戏本体.zip | 55400 | 9a77786223486e3c |
| dist/build_manifest.json | 836 | ddfab95519210826 |
| tools/levels.json | 263588 | 4e4f0d479113b41d |
| game/index.html（UI 源） | 90064 | 73405b04cab832b0 |
| docs/SPEC.md | 13252 | 16712878bf136e91 |
| 冉政-设计思路文档.md | 24407 | 3138ca7c02d466a1 |
| 冉政-迭代优化过程文档.md | 43128 | c6955db49d3bdb19 |
| README.md | 4111 | 7827727612cd2825 |

- 16:10:5x 首次冻结时：dist `b56232f9`、zip 55011B/`8ec0cec5`、manifest `ca0f2e35`。
- **16:11:08–09 整套重建**（SPEC 12881→13252B、README、zip、manifest 全变，dist 内容不变）。
- **16:24:25 再次重建**：dist→`b70363c5`、zip→55400B/`9a777862`、manifest→`ddfab955`。差异经 diff 逐行确认，**正是本报告 E 项查出的 SKY `level` 错标修复**（`ophiuchus` 21→29、`carina` 22→26、`hydra` 23→30，含 `neighbors` 内所有交叉引用）。修复前那一版（dist `b56232f9`）的 E 项为**不通过**，证据见 §E 末条（旧日志已被本轮复测覆盖，故结论以报告文字为准）。
- `tools/levels.json`（4e4f0d47）、两份冉政文档、`game/index.html`、`README.md`（16:10:55 定稿）在复核窗口内未再变 → A/B/C/H 的结论对前后两版都成立。

## A. 数据自洽 — **通过**
命令：`python verification/v13_a_data.py`（日志 `logs/v13_a.txt`）
- 50 关齐备；`id` 与序号一致；`mines` 无重复、无越界。
- `rowRuns`/`colRuns` 由 `mines` 独立重算后逐关逐行/列**全等**（100 组，0 处不符）。
- `noise ⊆ mines`；`noise ∩ theme.stars = ∅`；`theme.stars ⊆ mines`；星坐标/星名无重复；`lines` 下标合法、无自环——50 关全部成立。
- `opening` 均为非雷格且邻域雷数 == 0（50/50）；`showRuns` 第 1 关 `false`、第 2–50 关 `true`。
- HTML 内嵌 `const LEVELS` 与 `tools/levels.json`：结构等价 **且** 规范化空白后文本逐字节相同。
- **每个星座在 50 关里不重复**：`theme.id` / `theme.name` 各 50 个互不重复。
- 发布版 SKY：50 条，`level` 覆盖 1–50 且唯一，每条与该星座真实所在关号一致（修复后）。

## B. 可解性（逐关零猜测） — **通过**
命令：`python verification/v13_b_solve.py`（日志 `logs/v13_b.txt`；播放序列 `verification/v13_play.json`）
自写规则：R1 邻域计数传播 + R2 数织行列枚举（枚举与已知雷/已知安全相容的全部连续块摆法，只判"全摆法一致"的格）+ R3 flood fill，三者交替到不动点；无可证明的格子即判不可解，**绝不猜**。
- **可解 50/50，不可解 0**，且每一步判定都与真值 `mines` 一致（0 误判）。
- **第 1 关 `showRuns=false` → 求解器禁用 R2，仅邻域推理 + flood 即可通关**（`仅邻域推理可解=True`）。
- 交叉验证：仅靠邻域计数可通关的只有 **4/50**（第 1、8、16、23 关）→ **46/50 必须用数织线索**，与文档主张完全吻合，也与 `tools/level_stats.json` 的 `nb_only=[1,8,16,23]` 一致。
- 探格次数（本求解器口径：优先探 0 格、被连锁翻开的格不重复计动作）：17–51 次。

## C. 难度指标（独立统计） — **通过**
口径：展开占比 = 开局 flood fill 后已翻开安全格 / n²；0 格占比 = 邻域雷数 0 的格数 / n²；孤立雷 = 8 邻域内无其它雷的雷。
- 尺寸集合 `{7,8,9,10,11}`，最大 11（≤11，50/50）。
- 雷密度 15.6%–24.0%，均值 21.6%（第 1 关 15.6%，其余 18.5%–24.0%）。
- 展开占比 11.1%–33.0%（最大第 36 关）≤38%；0 格占比 11.1%–30.0%（最大第 25 关）≤40%；孤立雷 0–2（第 22/25/26/28 关为 2）≤2；**阈值超出项 0**。
- 口径敏感性：若把分母改成"安全格"，第 9/28/36 关展开占比为 38.1%/39.6%/42.9% 将超线。本报告采用项目文档口径（分母 n²，与"雷密度"同分母），并在此显式记录。

## D. 运行时（自写 DOM 桩驱动 dist 内联脚本） — **通过**
命令：`node verification/v13_d_dom.js`（日志 `logs/v13_d.txt`；**107 项断言 / 105 通过 / 0 不通过 / 2 记录项**）
- **50 关全部玩到 `status="won"`**（`won=50 lost=[] stuck=[]`）：全程零踩雷，每关 `revealed == totalSafe`、`flagged == mines`，`dataset.gameState` 的 `level/size/revealed/totalSafe/flagged/mines/lives/status/mode/totalLevels/clearedLevels/noise` 字段齐全。
- **揭晓图逐关断言通过（50/50）**：星座星数 == `theme.stars.length`、连线数 == `theme.lines.length`、杂星暗点数 == `noise`、杂星坐标与星座星坐标不重叠；棋盘揭晓类名 `wonstar`/`wonoise` 计数同样吻合。
- `<title>星织 Asterweave · 50 关</title>`；`modeDig`「🔭 观测」、`modeFlag`「★ 标记」；第 1 关 `lvtag` 显示「仅邻域数字」、第 2 关「含行列线索」。
- **`status!=="won"` 时 DOM 不泄露雷位**：未翻开且未插旗的格子 `textContent`/`innerHTML` 全空；无 `wonstar/wonoise/hitstar/hitnoise` 类名；`board.innerHTML` 不含 `mines`/`noise` 字样。
- **失败路径**：连踩 3 颗 → `status="lost"`、`lives=0`、结算标题「观测失败」、命数图标仍 3 槽。
- **「全部解锁」一次点击即生效（本轮修过的 bug）**：打开关卡面板后只点 1 次 `#unlockBtn`，禁用按钮数 49→0、`devUnlock=true`、文案变「🔒 恢复进度锁」；再点 1 次恢复（disabled 回到 49）。监听器已在 `resetBtn` 回调之外（dist `document.getElementById('unlockBtn').addEventListener('click', toggleUnlockAll);`）。
- 键盘契约：`Enter` 探格仍有效；`Esc` 依次关 结算→星座卡→图鉴→关卡面板。

## E. 新增图鉴页 — **通过**（对 16:24:25 版；16:11:09 版曾不通过，见下）
- 具备 `#skyBtn`「✦ 图鉴」与 `#skyPanel`（`skyCount`/`skyTotal`/`skyFilters`/`skyLitBtn`/`#skyMap`/`#skyDetail`/`#constModal`）；`game/index.html` 同样具备（模板 SKY=[]）。
- 开关正常：点 `#skyBtn` 打开（`hidden=false`、`class` 含 `open`），再点 / `#skyCloseBtn` / `Esc` 均可关闭；天球图渲染 **50 个** `skynode`，只含赤经赤纬投影，不内嵌任何星图坐标。
- **`skyCount` 与实际通关数一致**：通关 50 关 → `skyCount=50`；干净存档只通第 1 关 → `1/50`；**只通第 1、21 关 → `skyCount=2`（与 cleared=2 相符）**。
- **未通关星座不泄露星图**：只通第 1、21 关时点选未通关的**蛇夫座**（真实第 29 关）→ 显示「未观测 · 第 29 关 · 通关后点亮」，HTML 内无 `gstar/gline/gnoise`。已通关的**摩羯座**（第 21 关）→ 渲染 9 颗星，坐标与摩羯座自身完全一致，事实文案也取自摩羯座自身（不再张冠李戴）。
- 契约未破：打开图鉴后 `dataset.gameState` 字段完整、棋盘键盘可用、遮罩/焦点逻辑照旧；`skyLitBtn`「一键点亮（预览）」是独立 dev 开关（`devSkyLit`），不影响通关计数。
- **16:11:09 版的旧缺陷（供留痕）**：SKY 的 `level` 有 3 处错标（蛇夫座 21、船底座 22、长蛇座 23，实为 29/26/30），导致 `level` 覆盖只有 46 个唯一值（21/22/23 各重复、26/29/30 缺号），后果是 ①只通第 1、21 关时 `skyCount=3≠2`，中间进度虚高 +1~+3；②未通关的「蛇夫座」卡片自称「第 21 关 · 已观测」并渲染出 9 颗星图 —— 而那正是**摩羯座**的星图与文案。16:24:25 重建已修好这 3 处，本轮复测全绿。

## F. 通关动画 — **通过**（静态 + 运行时双确认）
- 静态：`checkWin()` 置 `S.status='won'` 后立刻 `winFlashPending = true`、给棋盘加 `reveal-flash`，再 `setTimeout(..., reduce ? 120 : 900)`；`renderModal()` 首行 `if (winFlashPending){ closeModal(false); return; }` → **先点亮星座闪一下、约 900ms 后才弹 modal**，`prefers-reduced-motion` 下降为 120ms。
- 运行时（DOM 桩虚拟时钟，非静态推断）：通关瞬间 `overlay` 未打开且棋盘 `class` 含 `reveal-flash`；推进到 ~880ms 仍不弹；再推进 40ms 后 `overlay open`；随后 `reveal-flash` 被移除。

## G. 发布包 — **通过**
命令：`python verification/v13_g_release.py`（日志 `logs/v13_g.txt`）
- ZIP 根目录**恰为** `index.html` + `README.txt` 两项（无多余目录/文件）。
- **ZIP 内 index.html 与 dist 版 sha256 完全相同**：`b70363c5…f828`，字节 416953 = 416953。
- HTML 零外部引用：`http://`=0、`https://`=0、`fetch(`=0、`XMLHttpRequest`=0、`WebSocket`=0、`<link`=0、`<img`=0、`import(`=0、`src=`=0。另有 `url(`×2，均为**内联 SVG 渐变内部引用**（`fill="url(#skyMw)"` / `fill="url(#skyVig)"`），非外部资源。
- `dist/build_manifest.json` 与实测**逐项一致**：`build_sha256=b70363c5…`、`html_bytes=416953`、`zip_sha256=9a777862…`、`zip_bytes=55400`、`level_count=50`、`ui_sha256=73405b04…`、`levels_sha256=4e4f0d47…`、`zip_root_entries=[index.html, README.txt]`，`checks` 全 true。
- 附带：README 里的线上试玩地址 `https://ran070602.github.io/asterweave/` 实测 HTTP 200，页面 `<title>` 为「星织 Asterweave · 50 关」（未逐字节比对部署产物，仅作存在性佐证）。

## H. 文档对账 — **通过**（有 3 处文字口径需订正，不影响数据）
命令：`python verification/v13_h_docs.py`（日志 `logs/v13_h.txt`）
- **两份文档的关卡表都完整对得上 `tools/levels.json`**：
  - `冉政-设计思路文档.md`：表头 L170（9 列：关/星座/棋盘/星座星/杂星/总雷/探格次数/数织线索贡献/只用数字能解？），分隔行 L171，表体 **L172–L221 = 50 行**，星座/尺寸/星座星/杂星/总雷 **0 处不符**。
  - `冉政-迭代优化过程文档.md`：表头 L117（9 列，末列为「必须用星图线索？」），分隔行 L118，表体 **L119–L168 = 50 行**，同样 **0 处不符**。
  - 两表的 `探格`、`数织线索贡献` 列与 `tools/level_stats.json` 的 `probes`/`runs` **逐格一致（0 处不符）**；两表推出的"必须用星图线索"46 关与我的独立求解器**完全一致**。
- README：`README.md` 与包内 `README.txt` 都说明了**图鉴**（✦ 图鉴 / 50 个星座 / 天球投影 / 一键点亮预览）、玩法（观测/标记/右键/失败条件）与「全部解锁」；已改名「星织 / Asterweave」，无旧名残留（`迷阵`/`迷宫`/`leixian.migong` 均未出现）。
- SPEC.md 已改名、版本 v1.7；两份冉政文档已改名（文中出现的「雷线」「leixian.migong」是**历史命名沿革的叙述**，非当前产品名）。
- **"文档说 X、实测 Y" 清单**：
  1. `冉政-设计思路文档.md` L165：「杂星从第 1 关就少量出现（**1–2 颗**）」→ 实测第 1 关杂星 **6** 颗，前 10 关为 6/7/9/10/6/6/9/10/6/8，全盘 6–22 颗。**不符**（真实设计与"杂星参与难度"的意图一致，只是这句数字是旧稿残留）。
  2. 同 L165「目标雷密度约 **18%**」与 L223/README「约 **20%**」→ 实测均值 **21.6%**（15.6%–24.0%）。**两个数都对不上，且文档之间自相矛盾**。
  3. L223「**每行每列都至少有一颗星**」→ 实测第 1 关有 3 个空行、2 个空列（其余 49 关无空行空列）。绝对表述不成立，但迭代文档 L184 已把第 1 关显式豁免为"走降级"，故**仅属措辞不严**。
  4. 两处小节标题仍写「**10 关**曲线（v0.5）」而其下表格已是 50 行——**标题未随扩容更新**。
  5. `探格次数` 不是可独立复现的量：文档列与其自带 `level_stats.json` 完全自洽（0 处不符），但我自写求解器的口径与之在 47/50 关不同（我 17–51 vs 文档 24–47，最大差 14）。文档 L278 自己也承认"与复核实现差 ±1"，实际差异比 ±1 大，建议把该列标注为"生成器口径"。

## 总体判定
**基本通过，可发布**——A/B/C/D/F/G/H 全部通过；E 项在 16:24:25 重建后通过；无 P0/P1 阻塞。唯一仍"不通过"的只有文档文字口径（3 处数字/措辞），不影响玩法与数据正确性。

### 仍不通过清单
1. `冉政-设计思路文档.md` L165「杂星 1–2 颗」与实测（第 1 关 6 颗）不符。
2. 文档雷密度表述不统一（18% vs 20% vs 实测 21.6%）。
3. 两处「10 关曲线（v0.5）」标题未随 50 关扩容更新。
4. （表述）L223「每行每列都至少有一颗星」对第 1 关不成立，宜加"第 1 关除外"。
5. （口径）`探格次数` 列与本轮独立求解器在 47/50 关有差（最大 14），建议标注为生成器口径。

### 上线前 top 3
1. **把"发布包在复核期间被重建两次"这件事收口**：再跑一次 `tools/build_release.py` 后冻结，确认 dist/zip/manifest 三者 sha 与本次记录一致（本次已确认 16:24:25 版自 16:24:25→16:26:52 稳定）；顺手在 CI/脚本里加"manifest 与实测 sha 一致"的断言。
2. **订正文档那 3 处数字/标题**（杂星 1–2 颗 → 6 颗且给出 6–22 区间；密度统一为"约 20%（实测 15.6%–24.0%，均值 21.6%）"；两个「10 关曲线」标题改成 50 关）。
3. **给 `探格次数` 列标注口径**（或改成"生成器口径，允许多路径 ±N"），避免下一位复核者再把它当成可独立复现的硬指标而反复对账。

