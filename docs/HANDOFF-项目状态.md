# 星织 Asterweave — 项目状态快照

> 状态：**未完工**。作者明确表示后续还要继续优化。本文件用于跨会话接手，勿当作终版说明。

- 快照日期：2026-10-22
- 当前关卡数：**50**
- 线上（主）：<https://asterweave.pages.dev>
- 线上（备）：<https://ran070602.github.io/asterweave/>

---

## 1. 交付目标（乐信圣文 AI Native 休闲游戏创作大赛）

| 交付物 | 当前状态 |
|---|---|
| `星织-游戏本体.zip`（根目录 `index.html` + `README.txt`，≤50MB） | 已产出（约 56 KB） |
| `冉政-设计思路文档.md` | 已有内容，随迭代继续更新 |
| `冉政-迭代优化过程文档.md` | 已有内容，随迭代继续更新 |
| 参赛提交（上传到比赛平台） | **尚未提交** |

## 2. 当前已达成

- **50 关**，数据在 `tools/levels.json`；`python tools/check_levels.py` 结果：硬失败 0 / 警告 0（零猜测可解、孤立雷、空行、密度、星座重复、图鉴覆盖全部通过）。
- **图鉴 50 星座**：`tools/sky.json` 由 `python tools/build_sky.py` 生成；关卡号按 `theme.id` 从 `levels.json` **反查**（避免计数错位）。
- **交互**：单击观测 / 双击·右键标记（220 ms 延迟判定窗口，已取代早期的"观测/标记"模式按钮）。
- **视觉**：双层闪烁星空背景（`body::before` + `body::after`，纯 CSS）；观测弹跳 + 亮度闪、标记轻抖 + 星形弹出、踩雷甩动；`prefers-reduced-motion` 全部降级。
- **图鉴交互**：真实天球投影、季节筛选、滚轮/双指缩放、拖动平移、星座详情为**屏幕中央 modal**（× / 点空白 / Esc 关闭）、未解锁星座显示**暗色名字**、「🔆 一键点亮（预览）」开发开关。
- **发布**：Cloudflare Pages（主，push 自动部署）+ GitHub Pages（备）。
- **质量保障**：`tools/build_release.py` 含注入回读、零外链、JS 语法、线索自洽校验与**四方 sha 一致性断言**；`verification/` 下已有 v07 / v10 / v13 / v14 独立复核报告与脚本。

## 3. 常用命令

```bash
python tools/build_release.py      # 构建：dist + ZIP + 同步根 index.html
python tools/check_levels.py       # 关卡自检
python tools/build_sky.py          # 重新生成图鉴数据
python tools/sync_docs_tables.py   # 文档关卡表同步（幂等，--dry 可预演）
```

- Python：`C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe`
- 无头验证：Edge `--headless=new --virtual-time-budget=N --dump-dom|--screenshot`
  ⚠️ **virtual-time 会冻结 CSS 过渡/动画**，探针读到的 computed 值可能是起始值（曾因此误判遮罩 opacity=0）。

## 4. 所有权边界（多会话并行协作）

| 归属 | 文件 |
|---|---|
| 本会话 | `game/index.html`、`docs/`、`README.md`、`tools/build_release.py`、`tools/build_sky.py`、`tools/sky.json`、`tools/check_levels.py`、`tools/sync_docs_tables.py` |
| 另一会话 | `tools/fit_constellation_levels.py`、`tools/gen_difficulty_first.py`、`tools/levels.json` |
| 独立复核者 | `verification/`（只增不改） |

提交时**按路径 add**，不要 `git add -A`（会混入他人未完成的改动）。

## 5. 已知坑（都踩过，改前先看）

1. SVG 上 `setPointerCapture` 会让 `click.target` 变成 SVG 根节点 → 选中逻辑要用 **pointerup 时记录的节点**。
2. 手势标志（`skyMoved` 之类）必须在手势结束时**复位**，否则"拖动一次后再也点不开"。
3. **大段替换 JS 函数区间风险高**：曾误删相邻的 `skyHintText()`，导致图鉴一打开就抛错、地图整片空白 → 改完必须跑构建 + 无头验证。
4. 无头浏览器里 CSS 过渡后的 computed 值不可信（见上）。
5. 文档同步脚本曾用固定正则匹配表格首尾 → **重复插入**；已改为"最长表格块、逐行比对、幂等"。
6. GitHub `push` 偶发 `502 / remote end hung up`，重试即可；Pages 部署 1–3 分钟生效。
7. `tools/levels.json` 属另一会话：本会话若要动它（如改 `teach`），需同时同步生成器，并在此记录。

## 6. 后续可优化方向（尚未最终确认）

- **真机测试**：iOS Safari 的渐变/模糊/双指缩放、安卓多机型（目前只有无头 Chromium + 作者手机的部分反馈）。
- **难度曲线**：50 关中 46 关"必须用数织线索"，另有 3 关仅靠数字即可解 —— 是否统一。
- **交互手感**：220 ms 判定窗口是否偏慢；撤销 / 重来 / 提示次数（目前 3 条命、无提示）。
- **图鉴**：「一键点亮」目前对玩家也可见，是否需要隐藏；早期提过的「星座连线寻路」小玩法。
- **内容扩展**：IAU 88 星座还有 38 个未用，可继续扩关。
- **音效**、**成绩分享图**、存档（现为 localStorage，键名 `leixian.migong.progress.v1`）。
- **文档**：把线上链接写进两份交付文档；提交前终检（ZIP 与线上 sha 一致、零外链、可解性）。

## 7. 2026-10-22/23 新增：通关揭晓改造 + 音效（阶段 1+2）

- **揭晓搬回棋盘**：通关后不再立刻弹遮屏 modal，而是在棋盘上依次播放——杂星退场（淡到 16% 灰）→ 星座星按**真实视星等从亮到暗**依次点亮（starLit）→ theme.lines 逐段连线（pathLength=1 描边动画）→ 中央浮出**星座名 / 英文 / 最亮星**与「✦ 星座图鉴 +1」。
  时序：杂星 0.22s → 星每颗 95ms → 线每段 58ms → 名字 → 结束；首次通关约 3s，**重玩走快速版**（45ms/30ms），**点击/任意键随时跳过**，prefers-reduced-motion 直接终态。
- **结算改为底部条**：通关不再用遮屏 modal（最后一关例外，仍弹「全部通关！」庆祝），底部结算条含「★ 星座档案 / ↻ 重来本关 / 下一关 →」，棋盘始终可见。
- **音效（WebAudio 合成，零外部文件）**：观测 tick、标记 click、点亮按音阶上行、连线双音、通关四音琶音、失败下滑音；首次用户手势时初始化 AudioContext；顶部 🔊 按钮开关并持久化（progress.sound，默认开）；通关加震动。
- **v2 修订（按用户反馈）**：揭晓阶段**去并发**——杂星退场 → 星座星**一次性亮起**（不再逐颗弹跳/逐颗发声，只一声和弦）→ **只保留逐段连线**（0.46s 描边、段间 155ms）→ 连线画完**弹小弹窗**（星座名 + 英文 + 最亮星 + 星图 + 科普 + 三个按钮「★ 图鉴详情 / ↻ 重来本关 / 下一关 →」）。原先浮在棋盘上的名字浮层已删除（太浅）。
- **结算条改为 position:fixed 贴屏幕底部**（原先在页面流里，手机上要下滑才能点到按钮），并加「×」可收起；仅在弹窗被 Esc/遮罩收起后才出现。
- 实测（无头 Edge + 键盘驱动真实 act()）：v1 通关 ov 不弹、lit=4 lines=2/2；v2 弹窗 overlay open、标题「第 N 关 · 观测成功」、cname=南十字座 Crux、三个按钮全在弹窗内且主按钮在视口内（primaryInView=true）；Esc 后底部条 position:fixed bottom=8px + 3 按钮 + ×；点 × 收起；跳过生效；失败仍弹 modal；音效开关落盘 false/true；第 50 关揭晓后弹「全部通关！」。全程零 JS 报错。

- **v3 修订（再次按用户反馈）**：
  1. 删掉通关弹窗里的「✦ 星座图鉴 +1」标签，以及面板内与弹窗标题重复的星座名；
  2. 弹窗排版收紧：**高度 616px → 340px**；四个视口（含 492×496 的极小可视高度）实测 `noInnerScroll=true`、`fitsViewport=true`、3 个按钮排成**一行**且全部落在视口内；
  3. **结算条删除右上角「×」**：原先点 × 之后「下一关 / 重来」就再也没有入口（用户体验缺陷）。现在结算条固定贴底、入口常驻；实测 `rxCount=0`、`position=fixed`、按钮 3 个（★ 图鉴详情 / ↻ 重来本关 / 下一关 →）。
- 教训：凡是"给用户一个关闭入口"的按钮，都要先问一句"关掉之后主流程入口还在不在"。

- **v4 事故与修复（弹窗不再居中）**：用户反馈"通关弹窗要在屏幕中间弹出"。
  根因：v3 里我用非贪婪正则删 `.result .rx` 样式 —— 正则 `  \.result \.rx\{[\s\S]*?\n  \}\n` 的结束条件与该规则的实际写法不匹配，于是**一路吞到后面第一个 `\n  }`**，把 `.modal .modal-cname/.modal-cmeta`、`.result.win/.lose/.msg/.result-btns`、以及**整条 `.overlay{position:fixed;inset:0;display:flex;align-items:center…}` 基础规则**一并删掉。没有 `.overlay` 的定位，弹窗就退回页面流、落在页面底部（要滚动才看得到）。同一次删除还留下一个孤立 `}`，造成 CSS 花括号 333/334 不配平。
  修复：从 `git show dc6bcbe~1:game/index.html` 取回被误删的整段原文补上；删除孤立 `}`；追加 `.overlay{top:0;left:0;right:0;bottom:0;padding:12px}` 作为不支持 `inset` 的浏览器保险。
  复验：`overlay=fixed, align=center`；页面滚到底（`scrollY=183`）时弹窗 `top=177/bottom=535`、**中心偏移 6px**、完全在视口内 = true；底部条背景恢复 `rgb(20,37,28)`、`.result-btns` = flex、3 按钮、无 ×。
- **两条硬教训**：
  1. **不要用 `[\s\S]*?\n  }` 这类"到下一个收尾大括号"的正则删 CSS/JS**——中间夹着的规则会被一起吃掉。删规则要用唯一锚点或明确的起止行。
  2. **CSS 改动后必须跑花括号配平审计**（本次新增 `audit_braces.py`）；"是否在视口内"要用**严格判据**（`top>=0 && bottom<=innerHeight`）。v3 时的 `fitsViewport` 只检查了高度和 `top>=-1`，所以弹窗掉到页面底部时仍报 true —— **这个弱判据让 bug 从我眼皮底下溜了过去**。

- **v5 音效修订（按玩家反馈）**：
  1. **踩雷音重做**：原先 `sawtooth 320→90Hz` 扫频被玩家形容"像放屁"，换成 **低频顿音（sine 165→98Hz，尾部 72/60Hz）+ 一记低通白噪声（340Hz）**，听感是"沉闷撞击"。文件里已无 `sawtooth`。
  2. **音量可调**：点 🔊 打开音量弹层（滑块 0–100% + 一键静音/开启），**图标随音量分档**（静音=斜杠，`vol-1/2/3` 依次多一道声波）；`progress.volume` 默认 **0.7**，与 `progress.sound` 一起持久化；调大音量会自动解除静音。
  3. **整体音量抬升**：各音效基准增益提高约 2–2.5 倍（dig 0.06 / mark 0.05 / stars 0.10 / line 0.075 / win 0.13 / fail 0.34），再乘主音量。
  4. 规则文案同步为"顶部 🔊 图标点开可调音量（图标会随音量变化，可一键静音）"；Esc 与外点均先关音量弹层。
  实测（插桩记录 WebAudio 真实参数）：踩雷音 = 2×sine(165/98Hz) + 1×低通噪声源，增益 0.238/0.154 = 基准×0.7（证明主音量生效）；滑块 0/25/50/100% → 图标 `sndoff/vol-1/vol-2/vol-3`；`volume`、`sound` 均正确落盘；点外部关闭弹层；零 JS 报错。

- **v6 音量再加大（player 反馈"还是小"）**：新增主增益常量 `SND_BOOST = 2.2`（滑块拉满 = 基准×2.2），**默认音量 0.7 → 0.85**（含读取回退、滑块初值、百分比初值共 5 处），并对 `tone()`/`noiseHit()` 的最终振幅加**上限 0.92 的限幅**防削波破音。
  实测：踩雷顿音增益 **0.6358 = 0.34 × 0.85 × 2.2**、噪声 **0.4114 = 0.22 × 0.85 × 2.2**；线索音 0.11 = 0.05 × 1.0 × 2.2。相比 v5 默认（0.238）**响约 2.67 倍**；滑块拉到 100% 还能再高（0.748，未触限幅）。
