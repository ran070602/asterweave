# 星织 / Asterweave v1.0 独立复核报告

- 复核人：独立复核者（第 5 位，v10）
- 时间：2026-10-22
- 工作目录：`D:\AI-Native casual game`（junction → `D:\Asterweave`，两者 levels.json 哈希相同）
- 复核对象：`dist/星织-游戏本体/index.html`、`星织-游戏本体.zip`、`tools/levels.json`、两份文档、`docs/SPEC.md`
- 方法：自写 Python 求解器（邻域计数 + 数织行列枚举 + flood fill 到不动点）与自写 Node DOM stub；未 import/copy `tools/generate_levels.py`、`tools/fit_constellation_levels.py`。
- 脚本：`verification/v10_*.py` / `verification/v10_dom.js`；原始输出 `verification/v10_out_*.json`。

## 结论速览

（逐项追加中）

## A. 数据自洽 —— 通过

命令：`python verification/v10_a_data.py`（原始数据 `verification/v10_out_a.json`）

- 20 关 id = 1..20，无重复；`mines` 无重复、无越界。
- 逐关 `mines == theme.stars ∪ noise`，`noise ⊆ mines`，`noise ∩ theme.stars = ∅`。
- `rowRuns`/`colRuns` 按 `mines` 重算后逐关逐行完全相等（含空行 `[]`）。
- `opening` 均为安全 0 格（周围 8 格雷数 = 0）；`lives` 均为 3。
- 第 1 关 `showRuns=false`，第 2–20 关均 `true`。
- HTML 内嵌 `const LEVELS`（20 关）与 `tools/levels.json` 解析后 **深度相等**。
- 唯一瑕疵（不影响 A 判定）：`<title>` 写「星织 Asterweave · 10 关」，实际 20 关（见 F）。

## B. 可解性（20 关逐关零猜测） —— 通过

命令：`python verification/v10_b_solve.py`（原始数据 `verification/v10_out_b.json`）

求解器三段：① 已翻开格的邻域计数传播；② 行列 `runs` 全排列枚举并取「所有方案一致」的格；③ 新判定安全格逐一点开 + 0 格 flood fill；循环到不动点。判定标准 = 全部安全格被逻辑翻开。

- **20/20 关在不动点前翻开全部安全格，无一步需要猜测**；20 关的 `mines_deduced` 也等于总雷数。
- 第 1 关关闭数织约束、只用邻域推理仍可解（`clicks=25`），满足「第 1 关只用邻域推理」。
- 求解器点击次数（0 格优先的贪心）17–43 次/关，与文档「探格次数」同量级但口径不完全相同（见 G）。

## C. 难度指标（独立统计） —— 通过

口径：开局从 `opening` 做 0 格 flood fill；0 格 = 安全格中邻域雷数为 0 的格；孤立雷 = 周围 8 格无其他雷的雷。阈值 ≤38% / ≤40% / ≤2。

下表每格为 `展开% / 0格% / 孤立雷`（20 关全量）：

```
L01 25.0/22.2/1   L02 24.5/26.3/1   L03 25.0/14.0/1   L04 11.1/12.5/1
L05 29.7/25.5/1   L06 22.4/18.9/2   L07 14.8/23.8/1   L08 28.0/33.3/0
L09 29.6/23.8/1   L10 20.0/25.3/1   L11 29.0/33.8/1   L12 24.7/30.8/1
L13 18.5/22.6/1   L14 22.0/30.0/1   L15 23.0/31.2/1   L16 20.7/29.2/0
L17 19.0/29.0/2   L18 27.3/28.7/1   L19 19.8/22.9/2   L20 23.1/36.5/1
```

- 最大开局展开 **29.7%**（L05）≤38%；最大 0 格占比 **36.5%**（L20）≤40%；最大孤立雷 **2**（L06/L17/L19）≤2。**无超阈值关**。
- 参考：孤立雷 2 的 3 关属于达标上限边缘，建议上线前略降（见建议 3）。

## D. 运行时（自写 DOM stub） —— 不通过（256 项断言，1 项失败）

命令：`node verification/v10_dom.js`（原始数据 `verification/v10_out_d.json`）；零 npm，自写 `El/Doc/window/localStorage/setTimeout` stub 并 `vm` 执行内嵌脚本。

- **20/20 关均玩到 `status="won"`**；每关揭晓图 `gstar == theme.stars.length`、`gline == theme.lines.length`、`gnoise == noise.length == noise 长度`，且 `gnoise` 坐标与任一 `gstar` 坐标零重合。
- 第 1 关棋盘 `clue` 数 = 0；第 2 关 = `2n+1`（角 + n 列 + n 行）。按钮文案「🔭 观测」「★ 标记」；`<title>` 含「星织 Asterweave」。
- 未通关时逐关检查全部雷格（含杂星）：`class=="cell"`、无文本、无 SVG；`body.dataset.gameState` 无坐标；闪烁期 `overlay` 未打开。**无泄露**。
- 失败路径：踩爆 3 颗 → `status="lost"`、`lives=0`、modal 标题「观测失败」、仅 3 颗雷显示为 hitstar/hitnoise。
- **失败项：全新页面点「🔓 全部解锁」无效**。点击前后 `localStorage` 的 `devUnlock` 均为 `false`，按钮文案不变；先点一次「重置进度」后再点才生效（`devUnlock=true`、第 19 关解锁）。
  - 根因：`index.html:8070-8071`，`unlockBtn` 的 click 监听被写在 `resetBtn` 的 click 回调里，首次加载从未绑定；复现：页面刚加载时点「全部解锁」，DevTools 看 `localStorage["leixian.migong.progress.v1"].devUnlock` 仍为 false。
- 附带：`<title>` 仍写「10 关」，实际 20 关（页面关卡按钮显示 20，manifest `level_count=20`）。

## E. 通关动画 —— 通过（仅静态确认）

- `index.html:7487-7498`：`checkWin` 置 `status='won'`、`markCleared` 后设 `winFlashPending=true`、`boardEl.classList.add('reveal-flash')`，再 `setTimeout(..., reduce ? 120 : 900)` 才清除并 `render()`；`index.html:7864-7866` 的 `renderModal()` 首行 `if (winFlashPending){ closeModal(false); return; }`，确实先闪约 900ms 再弹 modal；CSS `index.html:328-336` 有 `reveal-flash` 动画，`prefers-reduced-motion` 下禁用。
- 说明：本条**仅静态确认**（未做浏览器帧级观测）；D 的运行时 stub 另证「闪烁期 overlay 未 open、flush 900ms 后 modal 打开」。

## F. 发布包 —— 通过

命令：`python verification/v10_f_release.py`（原始数据 `verification/v10_out_f.json`）

- `dist/星织-游戏本体/index.html`：sha256 `e43e0b4d…24b4`，151517 bytes；ZIP sha256 `d9448270…86c4`，27361 bytes。
- ZIP 根目录 = `index.html` + `README.txt`；ZIP 内 `index.html` 151517 bytes、sha256 与 dist **逐字节相同**。
- `dist/build_manifest.json` 的 `levels_sha256` / `build_sha256` / `html_bytes` / `zip_sha256` / `zip_bytes` / `level_count=20` **全部与实测一致**。
- HTML 外部引用计数全 0：`http(s)://` 0、`fetch(` 0、`XMLHttpRequest` 0、`WebSocket` 0、`<link` 0、`<img` 0、`import(` 0、`<script src=` 0；单文件离线可跑。
- 唯一文案瑕疵：`<title>星织 Asterweave · 10 关</title>` 与实际 20 关不符。
- 补充：manifest `ui_sha256` 与 `game/index.html` 实测 sha256 一致（`7f5237e2…17bb`），说明 D 的解锁缺陷来自 UI 源文件而非构建注入。

## G. 文档对账 —— 不通过（表格字段通过，命名与多处事实不一致）

命令：`python verification/v10_g_docs.py`（原始数据 `verification/v10_out_g.json`）

- **关卡表结构字段通过**：两份文档的 20 关表（设计 L162、迭代 L117）共 40 行，`星座 / 尺寸 / 星座星 / 杂星 / 总雷` 与 `levels.json` **逐行全部一致**。
- `探格` 列：两文档数值完全一致（19–47），但 `levels.json` 无此字段、且依赖推理路径（独立求解器同口径为 17–43），**该列未判定**，不作为数据矛盾。
- **改名未彻底**：正文版本行已写「星织 / Asterweave」，但两份文档 H1 仍是「雷线谜图 · 设计思路文档 / 迭代优化过程文档」（各文件第 1 行）。
- **文档说 X、实测 Y（4 条）**：
  1. 设计 L27「第 1–3 关不显示行列线索，第 4 关起显示」 vs 数据仅第 1 关 `showRuns=false`，第 2/3 关均 `true`。
  2. 设计 L225「教学文案第 1、4、8 关」 vs 实际非空 `teach` = **第 1、6、12 关**（第 4、8 关为空）。
  3. 迭代 L154「20 关里有 **16** 关必须用星图线索」 vs 同文表格 17 关标「否」；独立复算 neighborhood-only 卡住 **17** 关（仅 L1/L8/L16 不靠数织）→ 应为 17。
  4. 迭代 L154「20 关全部达标…**无空行空列**」 vs L1 有 3 个空行（0/4/7）、2 个空列（4/7）。
- 另有陈旧描述：设计 L209「10 关数据（约 87 KB）」 vs 实测 20 关 / 151517 B；`docs/SPEC.md` v1.3 仍写「10 关初版：第 1–3 关 false」、6×6→8×8 难度表，且出现「10 关」11 次。
- 历史章节（3 关/10 关初版）可保留，但上述 1–4 条写在「当前规则 / 当前结果」语境，属明确对账失败。

## 总体判定 —— 不通过（2/7 项必查不通过）

| 项 | 判定 | 一句话 |
|---|---|---|
| A 数据自洽 | **通过** | 20 关 mines/runs/opening/noise/内嵌 LEVELS 全一致 |
| B 可解性 | **通过** | 20/20 零猜测；第 1 关仅邻域推理可解 |
| C 难度指标 | **通过** | 展开≤29.7%、0 格≤36.5%、孤立雷≤2，无超阈值 |
| D 运行时 | **不通过** | 20/20 通关与揭晓全对；但「全部解锁」首次点击无效（256 项仅此 1 失败） |
| E 通关动画 | **通过（仅静态）** | `winFlashPending` + 900ms 延迟 + `renderModal` 提前返回 |
| F 发布包 | **通过** | ZIP 根目录 index.html、逐字节一致、零外链、manifest 全对 |
| G 文档对账 | **不通过** | 关卡表与改名主体 OK，但 H1 旧名 + 4 处文档-实测矛盾 |

## 仍不通过清单

1. **D-1（阻断级）**：`index.html:8071` 把 `unlockBtn` 的监听注册在 `resetBtn` 回调内，全新页面「🔓 全部解锁」无任何反应，`progress.devUnlock` 保持 false；先点一次「重置进度」后才恢复。
2. **G-1**：两份交付文档 H1 仍为旧名「雷线谜图」，未改为「星织 / Asterweave」。
3. **G-2**：设计文档规则表把第 2/3 关描述为「不显示行列线索」，与实际 `showRuns=true` 相反；教学关写成 1/4/8，实际 1/6/12。
4. **G-3**：迭代文档「16 关必须用星图线索」应为 17；「无空行空列」对第 1 关不成立。
5. **非阻断**：`<title>` 仍写「10 关」；SPEC v1.3 仍按 10 关初版描述（6×6→8×8、第 1–3 关 false）。

## 上线前 Top 3 建议

1. **修解锁回归并加构建闸门**：把 `unlockBtn` 绑定移到初始化顶层（`loadProgress()` 后调用 `refreshUnlockBtn()` 并统一绑定），并在 `build_release.py` 增加「每个交互按钮至少 1 个 click 监听」的静态断言，防止再次回归。
2. **一次性同步所有对外文案到 20 关**：`<title>`、两份文档 H1、设计文档规则表（第 2 关起显示数织）、teach 关号（1/6/12）、16→17、删「无空行空列」与「87 KB/10 关」；SPEC 升级为 20 关契约或明确标注「历史初版」。
3. **给孤立雷留余量**：L06/L17/L19 的孤立雷=2 正踩阈值上限，建议降到 ≤1 并复跑本报告 B/C 脚本；同时把 B/C 校验接入发布流程，避免后续换关后指标漂移。