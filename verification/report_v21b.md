# 星织 · 独立复核报告 v21b（当前版本全量）

复核者：独立复核子代理（**未 import 任何 `tools/` 生成器**）。2026-10-23 13:3x（Asia/Shanghai）。
工作目录 `D:\AI-Native casual game`（junction `D:\Asterweave`，同一目录）。结论边验边落盘。
Python `C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`；Node `D:\develop\NodeJS\node.exe`。

## 0. 冻结基线（当前版本）与校验器来源

`dist/星织-游戏本体/index.html` = 根 `index.html` = `frozen_v21b` 冻结副本 = **AD05D8E9D7C6AAEF（419446 B）**；
`星织-游戏本体.zip` = 22920210682F3BEACF（63044）｜`game/index.html`（源）= 44A8CF8DFAF275DD（119325）；
`tools/levels.json` = 0DA0E18EC009AE7B｜`tools/sky.json` = 3EBE8A0FE93A49E0｜`tools/level_stats.json` = C1AA37AA0B10CA13；
`dist/build_manifest.json` = A8F117EED25847D2｜`docs/SPEC.md` = CF034D90876A98CB（14494）。
当前构建与上一轮冻结副本**逐字节相同** → 作者「418,613 → 419,446」的改动就是本报告复核的这一版。
`verification/v21b_setup.py` 把上一轮独立实现冻结为本轮 `v21b_*` 快照，HTML 来源改为**当前** dist、输出改名 `v21b_out_*`。
快照 sha256 前 16：`v21b_a_data.py=9C4017736FFEFA10`、`v21b_b_solve.py=16341E254BCB35CF`、`v21b_c_metrics.py=A51AE0D3D7043F4C`、`v21b_stub.js=EA4617483CAAF632`、`v21b_d_dom.js=C77D1FF5A8694600`、`v21b_f_anim.js=92F6E2841A4326F0`。
> ⚠ 并发提示：本回合开始后 `verification/` 仍在被另一进程写入（13:32:16 起新建 `_probe19.py`…`_probe23.py`，并改动 `report_v21.md`）；本报告结论只基于上述 sha，不受影响。
> 复现基线：`Get-FileHash 'dist\星织-游戏本体\index.html','index.html','星织-游戏本体.zip','game\index.html' -Algorithm SHA256`
## A. 当前版本数据自洽 —— **通过**

`python verification\v21b_a_data.py`（`logs\v21b_a.txt`）：内嵌 `LEVELS` 与 `tools/levels.json` **deep-equal**；50 关逐关 `rowRuns`/`colRuns` 由 `mines` 独立重算一致、`stars ⊆ mines`、`noise ⊆ mines`、`noise ∩ stars = ∅` 且两者无重复、`opening` 为安全 0 格、L1 `showRuns=false` / L2–50 `true`、`lives` 全 3、`id` 1..50 连续、`theme.id` 唯一 = 50。
证据：`A 关数=50  theme.id 唯一=50` / `A 内嵌==levels.json : True` / `A 失败项 0` / **`A_VERDICT PASS`**
## B. 当前版本 50 关零猜测可解 —— **通过**

`python verification\v21b_b_solve.py`（`logs\v21b_b.txt`、`v21b_out_b.json`、`v21b_solution.json`）：邻域计数传播（`d==|F|`→安全；`d-|F|==|U|`→雷）+ 数织行列枚举（全票定雷/定安全）+ flood fill 到不动点；L1 按契约禁用行列枚举。
证据：`B 可解 50/50` / `B 第1关 仅邻域推理（禁用行列枚举）：ok=True revealed=29/29` / **`B_VERDICT PASS`**；无 `no-placement`/`conflict`/`loop-guard`。
## C. 当前版本难度指标 —— **通过**

`python verification\v21b_c_metrics.py`（`logs\v21b_c.txt`；口径：开局展开 = 从 `opening` 起 0 格连通块 / n²）：
尺寸 ≤11 `max=11` ✓｜开局展开 ≤38% `max=33.0%`(L36) ✓｜0 格 ≤40% `max=28.9%`(L20) ✓｜孤立雷 ≤2 `max=2` ✓｜无空行空列（前五关 + 全 50 关）全 0 ✓｜雷密度 15–25% 实测 18.4%–24.0% ✓｜`level_stats.json` 逐关 8 字段 50 关全对 ✓。**`C_VERDICT PASS`**
注：`level_stats.probes` 与我的求解器 `reveal_actions` 在 18 关不同（最大 L15：31 vs 39），是批量推导顺序差异，非数据不一致 —— H 只核「文档数字 == 文件数字」。
## D. 运行时（DOM 桩） —— **通过（20/20）**

`node verification\v21b_d_dom.js`（`logs\v21b_d.txt`；桩用 `vm` 直跑当前 dist 内联 IIFE，仅经公开 DOM 与事件驱动）。**脚本对当前版本仍完全可用**：`D 合计 PASS 20 / FAIL 0`。
D1 50/50 关玩到 `status=won`（`lit=stars`、`#boardReveal line=lines`、`wonoise=noise`、`gstar/gline/gnoise` 全等、modal 均开）；D2a 触摸轻触即时观测（`revealed 11→15`，未推进时钟）；D2b 长按 200ms 未标记 / 400ms 已标记、抬起不再观测；D2c 长按雷位标记且 `lives 3→3`；D2d 左键观测；D2e 右键标记不观测；D2f/D2f2 双击不产生标记；D2g `DBL_MS=0`、`lastMouse=0`、棋盘无 `dblclick` 监听 → 四条交互路径与「双击不标记」全部成立。
精确化补充：全文件确有 **1 处** `dblclick` 监听，但在**图鉴地图**（`skyEls.map`，视图复位用），与棋盘标记语义无关。
## E. 星座图鉴 —— **通过**

`python verification\v21b_e_sky.py` + `node verification\v21b_e_states.js`（`logs\v21b_e.txt`、`logs\v21b_e_dom.txt`）。
数据侧：内嵌 `SKY` == `tools/sky.json`（50 座）；`SKY[].level` 唯一覆盖 1..50；**`SKY[].level == LEVELS[theme.id].id` 正反双向成立**；`neighbors` 引用自洽 → **`E_VERDICT PASS`**。
运行时按任务书六态 `{}`/`{1}`/`{1,21}`/前21/前49/全部50 → `#skyCount` = **0/1/2/21/49/50**（`#skyTotal`=50，侧栏 `#clearedCount` 同步）。关键：非连续态 `{1,21}` 得 **2** 而非 21 → 计数用「已通关集合大小」而非「最高关号」。
`E1`/`E3`/`E4` PASS（`E3` 已通关星座 `gstar/gline/gnoise` == `stars/lines/noise` 且显示 fact；`E4` 地图未观测节点 `.lbl.off`、无星图元素）；`E2` PASS：把**全部 48 个**未通关星座逐个打开，均无 `gstar/gline/gnoise`、无 `data-jump`、无 `sky-fact`、不显示别的星座名。
> 备注（**我方校验器的 bug，非游戏 bug，修正后才通过**）：初版按「星座名字符串包含」判泄露，把 `半人马座` 里包含的 `人马座` 误判为泄露。正确做法是先剥掉自身名字再匹配；修正后 48/48 无泄露。
## F. 通关动画 —— **部分通过（核心行为正确；两处口径不符）**

`node verification\v21b_f_anim.js`（`logs\v21b_f.txt`）+ 源码静态核验。
- **[通过] 顺序**：`checkWin` = 置 `won` → `winRevealPending=true` → `render()` → `startBoardReveal()`；`renderModal()` L24083 `if (winFlashPending || winRevealPending){ closeModal(false); return; }` 确实提前返回 → 制胜瞬间不弹窗、先点亮星座（`.reveal-stage` + `.wonstar.lit{animation:starGlow}`「闪一下」）再弹 modal（运行时 `modalOpen` false→true）。`F1/F2/F7` PASS。
- **[通过] reduced-motion 缩短**：`startBoardReveal` 直接 `finishBoardReveal()` 落终态（实测弹窗 ~5ms vs 首通 2115ms）。`F6` PASS。
- **[✗ 时长口径] 任务书写「约 900ms」，实测首通 2115ms / 重玩 1030ms，源码内不存在任何 900ms 常量**。`startBoardReveal`：`end = t0 + stars*step + 620 + (drawn-1)*lineStep + 820`，`t0=400`、`lineStep=155`；fast 分支 `160/12/300/62/460`；L24014 注释自称「~3.2s（首次）/ ~1.5s（重玩）」。既不合代码也不合实测。
- **[✗ 机制命名] `winFlashPending`（L23140 声明）从未被赋 `true`**，全文件仅 2 处（声明 + L24083 读取）→ **死代码**；`.reveal-flash` 与 `@keyframes winStarFlash`（L439–447）CSS 存在但 JS 从不添加该类 → 同样不可达。真正生效的是 `winRevealPending`：「`winFlashPending` + `renderModal` 提前返回」只有后半句在起作用。
## G. 发布包 —— **通过**

`python verification\v21b_g_release.py`（`logs\v21b_g.txt`）：ZIP 根目录恰为 `index.html` + `README.txt`（无目录项/垃圾文件）；ZIP 内 `index.html` sha == dist == 根 `index.html` == 冻结副本 = `AD05D8E9D7C6AAEF`（419446 B）。
零外部引用：`http(s)://`/`fetch(`/`XMLHttpRequest`/`WebSocket`/`<link`/`<img`/`import(`/`src=`/`@import`/`<iframe`/`<object`/`<embed`/`new Worker` **全为 0**；`url(` 仅 2 次（`#skyMw`、`#skyVig`）为**内联 SVG 内部引用**。
`dist/build_manifest.json` 9 字段（ui/levels/build/zip sha、level_count=50、zip_bytes=63044、html_bytes=419446、build_output、zip、zip_root_entries）**逐项与实测一致**，其 `checks` 5 项我独立重算后同样成立（含 `node --check`）。**`G_VERDICT PASS`**
## H. 文档对账 —— **不通过（1 项：迭代文档措辞与实现不符；其余全对）**

脚本判定 `H_VERDICT FAIL`，失败项恰 1 条（下表最后一条），下面前 4 条均 PASS：

`python verification\v21b_h_docs.py`（`logs\v21b_h.txt`）。
- 两份 `冉政-*.md` 的 **50 行关卡表逐格 0 差异**：`关号/星座名/棋盘尺寸/星座星/杂星/总雷/探格/数织线索贡献` 与 `tools/levels.json` + `tools/level_stats.json` 三方相符；行数各 50，关号恰 1..50。
- 「必须用线索」关数表述一致：文档写「50 关里有 **45** 关重新变成'必须用星图线索'」，实测 `level_stats.nb_only==false` = **45 关** ✓；「只用数字能解？/必须用星图线索？」列极性与 `nb_only` 逐关一致（L1 各自特殊标注）。
- `docs/SPEC.md` 操作契约 == 实现：无模式切换（`modeBtn`=0、无「模式」按钮）；轻触/长按、单击/右键俱在；「不做双击标记」✓（`DBL_MS`=0、`lastMouse`=0、棋盘无 `dblclick`）；SPEC `长按 ~380ms` == `LONG_PRESS_MS=380`；SPEC `容差 12px` == `MOVE_TOL=12`；`contextmenu` 被 `preventDefault`。
- 「**★ 图鉴详情**」措辞：SPEC 已正确写作「★ 图鉴详情」而非「结算」✓；全构建 18 处「结算」**全在注释里，零个按钮文案**（静态 `<button>` 文本只有「🔓 全部解锁/重置进度/关闭/🔆 一键点亮（预览）/×/开始观测/↻ 重玩本关」，通关按钮为动态生成）。
- **[✗ 文档说 X、实测 Y（唯一一处）]** `冉政-迭代优化过程文档.md` L248 仍写 `| ✅ 通关 | 下一关 → · ↻ 重来本关 · **结算**（用来回看星座揭晓） |`，L250 亦称「通关之所以保留『结算』」，但当前实现该按钮是 **「★ 图鉴详情」**（D3e 实测结算条按钮 = `["★ 图鉴详情","↻ 重来本关","下一关 →"]`）。SPEC 已改、迭代文档未同步（L252 引用的 `v17_strip_test.js` 也仍断言「通关条含结算」）。
## 总体判定

**A/B/C/D/E/G 通过（D 20/20、E 数据+运行时 4/4、F 运行时 7/7）；F 部分通过（2 项不符）；H 不通过（1 项：文档措辞）。**
**无数据错误、无可解性缺陷、无运行时交互缺陷、无发布包缺陷 —— 唯一实质问题集中在「揭晓时长口径/死代码」与「1 处文档未同步」。**

### 仍不通过清单
1. **F-时长**：通关揭晓「~900ms」不成立 —— 实测首通 **2115ms** / 重玩 **1030ms**，源码无 900ms 常量。
2. **F-机制**：`winFlashPending` 声明后从未赋值（死代码）；`.reveal-flash`/`winStarFlash` CSS 不可达；真正生效的是 `winRevealPending`。
3. **H-文档**：`冉政-迭代优化过程文档.md` L248/L250 仍把通关按钮写作「**结算**」，与实现（「★ 图鉴详情」）及 SPEC 不符。

### top 3 修改建议
1. **先定口径再动代码**：确认揭晓时长目标是「~900ms」还是「~2.1s」。若 900ms，把 `startBoardReveal` 参数（620/820/155）等比压缩到 total ≈ 900ms（fast ≈ 500ms）；若维持 2s，则更新任务书与文档，别让「900ms」继续作为验收线流传。
2. **删死代码或接通它**：删掉 `winFlashPending` 与 L439–447 不可达的 `.reveal-flash`/`winStarFlash` CSS，或把点亮动作改为置 `winFlashPending=true` 再由其清除；否则下一位复核者仍会把它当作机制证据。
3. **同步迭代文档与旧断言**：把 `冉政-迭代优化过程文档.md` L248/L250 的「结算」改为「★ 图鉴详情」（或明确标注为历史记录），并更新 `verification/v17_strip_test.js` 中断言「通关条含结算」的用例，避免验证脚本继续为过期行为背书。

### 复现命令（脚本快照 `verification/v21b_*`，全部只读；未改动 game/tools/docs/dist/根 index.html/zip/两份冉政-*.md）
```powershell
$py='C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'; $env:PYTHONIOENCODING='utf-8'
& $py verification\v21b_a_data.py ; & $py verification\v21b_b_solve.py ; & $py verification\v21b_c_metrics.py
& 'D:\develop\NodeJS\node.exe' verification\v21b_d_dom.js
& $py verification\v21b_e_sky.py ; & 'D:\develop\NodeJS\node.exe' verification\v21b_e_states.js
& 'D:\develop\NodeJS\node.exe' verification\v21b_f_anim.js
& $py verification\v21b_g_release.py ; & $py verification\v21b_h_docs.py
```
