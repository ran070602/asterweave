# T13 独立复核报告 · v0.3（10 关 · 数织提前 / 爱心命数 / 结算 modal）

> 复核者：verify-t13（全新独立复核者，未参与实现）｜复核时间：2026-10-21 16:5x–17:2x（Asia/Shanghai）
> 状态：**已完成** —— A/B/C/D/发布包/文档对账均已实测；结论见 §7。
> 独立性声明：本报告的 A/B/C 脚本 `verification/t13_level_check.py` 为**本轮自写**，不 import、不复制 `tools/generate_levels.py`；C 另用上一轮独立实现 `verification/c_uniqueness.py`（原样复制为 `_t13_c_xcheck.py`，仅改输出路径）做**第二实现互证**——上一轮（`report_t11.md` §13）出现过"复核脚本自身 bug 导致假阳性"，本轮凡关键结论均以两种实现互证后才下判定。

## 0. 被复核对象（以 sha256 为准）与冻结副本

本轮开始时实测 sha256（`Get-FileHash -Algorithm SHA256`）：

| 对象 | 字节 | sha256 |
|---|---|---|
| `dist/冉政-游戏本体/index.html` | 48,555 | `f9c7d69ca249c067eaf8dac094c37e8b0d50e3c018f6539f2b8ee0668969b1a9` |
| `冉政-游戏本体.zip` | 12,977 | `bdea61a74973bfc509650bc402a80a9543ab0b614d2c71a392cdd995779d4231` |
| `tools/levels.json` | 11,828 | `891b416c1ac53e586039d4020a8f5a09152ae396be23109b14f0c2ed61009746` |
| `tools/report.md` | 26,612 | `6a5718e7892f2506e5ec348a2a821fc663819e4a0ada37b6c30b530eee76abdc` |
| `docs/SPEC.md`（v1.2） | 10,590 | `6f270c30e9f3ce453900d9d47ca23bc6b9aa61817d62ec5f3660ff28de816312` |
| `冉政-设计思路文档.md` | 14,510 | `6beaa245e3bc8317b7c4871032a550e9c724755e08a1787836ca077671757e4c` |
| `冉政-迭代优化过程文档.md` | 27,398 | `779b21711235f8638b71297fe0ae7fd8cf1827114a31483aa433d14934f04ed1` |
| `dist/build_manifest.json` | 835 | `dd2db2bdeee32ef248409b549c84cee6c4f98fad180f775cadae31a51f1b6a04` |

已建冻结副本 `verification/frozen_t13/`（`Copy-Item` 实测）+ 两份 C 交叉验证输出；复现命令：

```powershell
$ErrorActionPreference='Stop'
New-Item -ItemType Directory -Force -Path 'verification\frozen_t13' | Out-Null
Copy-Item 'dist\冉政-游戏本体\index.html' 'verification\frozen_t13\dist_index.html'
Copy-Item '冉政-游戏本体.zip'               'verification\frozen_t13\release.zip'
Copy-Item 'tools\levels.json'               'verification\frozen_t13\levels_10levels.json'
Copy-Item 'tools\report.md'                 'verification\frozen_t13\report_10levels.md'
Copy-Item 'docs\SPEC.md'                    'verification\frozen_t13\SPEC_v1.2.md'
Copy-Item '冉政-设计思路文档.md'              'verification\frozen_t13\design_doc.md'
Copy-Item '冉政-迭代优化过程文档.md'           'verification\frozen_t13\iteration_doc.md'
Copy-Item 'dist\build_manifest.json'        'verification\frozen_t13\build_manifest.json'
```

本轮脚本清单（均在 `verification/` 下，未触碰 `game/ tools/ docs/ research/` 与根目录两份 `冉政-*.md`）：

- `t13_level_check.py` —— A/B/C 主检查（自写）
- `_t13_c_xcheck.py` —— C 的第二实现互证（复制自 `c_uniqueness.py`，仅改输出路径；其内部为"行模式 DFS + 列前缀剪枝"与"行模式全展开暴力"两套方法互为交叉验证）
- `t13_play_sequences.json` —— B 求解器产出的 10 关逐步动作序列（供 D 驱动 UI）
- 日志：`logs/t13_a.txt`、`logs/t13_b.txt`、`logs/t13_c.txt`、`logs/t13_c_xcheck.txt`

复现环境（本机）：

```powershell
$env:PYTHONIOENCODING='utf-8'
$PY='C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
```

---

## 1. A. 关卡数据自洽 —— **通过**

复现命令：

```powershell
& $PY verification\t13_level_check.py a
```

真实输出（`verification/logs/t13_a.txt`）：

```text
== A. 关卡数据自洽 ==
数据源: D:\AI-Native casual game\tools\levels.json
关卡数=10 ｜ 内嵌 LEVELS==levels.json: True ｜ game 外壳==dist 外壳: True
  第 1关 6x6 雷 6 showRuns=False 开局展开14 格 teach=有 OK
  第 2关 6x6 雷 7 showRuns=True  开局展开 6 格 teach=有 OK
  第 3关 6x6 雷 8 showRuns=True  开局展开 8 格 teach=无 OK
  第 4关 7x7 雷 8 showRuns=True  开局展开 6 格 teach=无 OK
  第 5关 7x7 雷 9 showRuns=True  开局展开15 格 teach=无 OK
  第 6关 7x7 雷10 showRuns=True  开局展开 6 格 teach=有 OK
  第 7关 8x8 雷11 showRuns=True  开局展开12 格 teach=无 OK
  第 8关 8x8 雷12 showRuns=True  开局展开11 格 teach=无 OK
  第 9关 8x8 雷13 showRuns=True  开局展开20 格 teach=无 OK
  第10关 8x8 雷14 showRuns=True  开局展开 9 格 teach=无 OK
A 判定: PASS（失败项 0）
```

逐项核对（脚本内实现：`expected_row_runs/expected_col_runs` 由 `mines` 现算后与声明比对）：

- 10 关、id 严格 1..10，`mines` 无重复/越界；
- 每关 `rowRuns`/`colRuns` 与 `mines` **完全一致**，行/列线索数字和 = 雷数；
- 每关 `opening` 是安全格且**邻域雷数 = 0**；开局 flood fill 展开 6–20 格（全部 ≥ SPEC §5 的 ≥5 要求）；
- 每关 `lives = 3`；
- **数织线索位置**：第 1 关 `showRuns=false`、第 2–10 关 `showRuns=true` —— 与用户改动 ①「第 2 关就引入数织」一致（10/10）；
- `teach` 非空关卡为 **1、2、6**（第 2 关确实带"左边和上面的数字"教学）；第 6 关为空行教学；
- dist 内嵌 `const LEVELS` **逐字段等于** `tools/levels.json`（`embedded_levels_equal: true`，10 关）；
- `game/index.html` 外壳（去掉 `LEVELS_INJECT` 块后）与 dist 外壳**逐字节相同**（`shell_equal_modulo_levels: true`）→ 发布产物确由当前外壳 + 当前数据构建。

> 上一轮 T11 的 A 结论同样成立，但本轮对象数据已重排（尺寸 6×6→8×8、雷数 6→14），故重新实测。

---

## 2. B. 零猜测可解性 + 教学带意图 —— **通过（10/10）**

复现命令：

```powershell
& $PY verification\t13_level_check.py b
```

求解器口径（自写，逐条说明）：模拟一个**只做可靠推理、绝不猜**的玩家；每步只落实一条推理：
- **A 规则（邻域计数传播）**：对每个已翻开格 `数字 == 已标雷数 + 未知邻居数` → 未知邻居全是雷；`数字 == 已标雷数` → 未知邻居全安全；
- **B 规则（数织行列枚举）**：对每行/列**暴力枚举全部 2^n 种摆放**（n≤8，显然正确、无剪枝 bug 面），保留"块序列 == 该行/列线索、已知雷位=1、已翻开格=0"的方案，取交集：在所有方案中都是雷 → 强制雷，都是安全 → 强制安全格；
- 每判定出一个安全格即翻开并触发 flood fill（与 UI 的 `floodReveal` 同语义：跳过雷与已插旗格）。
- 若禁用 B 时 A 无任何可推格 → 记"卡住"（该关只用邻域推理无法继续）。

真实输出（`verification/logs/t13_b.txt`，节选全部 10 行）：

```text
  第 1关 6x6 showRuns=False 仅邻域:通关     全推理:通关    | A步22 B步 0(雷 0/探 0) 探格16 总步22 | 意图:OK
  第 2关 6x6 showRuns=True  仅邻域:卡住     全推理:通关    | A步14 B步12(雷 0/探12) 探格19 总步26 | 意图:OK
      仅邻域卡住时：已翻开 6、已标雷 0、剩余 30 格
  第 3关 6x6 showRuns=True  仅邻域:卡住     全推理:通关    | A步17 B步11(雷 1/探10) 探格20 总步28 | 意图:OK
  第 4关 7x7 showRuns=True  仅邻域:卡住     全推理:通关    | A步26 B步12(雷 0/探12) 探格30 总步38 | 意图:OK
  第 5关 7x7 showRuns=True  仅邻域:卡住     全推理:通关    | A步25 B步 7(雷 0/探 7) 探格23 总步32 | 意图:OK
  第 6关 7x7 showRuns=True  仅邻域:卡住     全推理:通关    | A步19 B步13(雷 4/探 9) 探格22 总步32 | 意图:OK
  第 7关 8x8 showRuns=True  仅邻域:卡住     全推理:通关    | A步29 B步15(雷 1/探14) 探格33 总步44 | 意图:OK
  第 8关 8x8 showRuns=True  仅邻域:卡住     全推理:通关    | A步33 B步 9(雷 0/探 9) 探格30 总步42 | 意图:OK
  第 9关 8x8 showRuns=True  仅邻域:卡住     全推理:通关    | A步33 B步 8(雷 1/探 7) 探格28 总步41 | 意图:OK
  第10关 8x8 showRuns=True  仅邻域:卡住     全推理:通关    | A步37 B步 9(雷 0/探 9) 探格32 总步46 | 意图:OK
B 判定: PASS（失败项 0）
```

结论：

- **第 1 关**：仅 A 规则即可推完全盘（A 步 22、探格 16、B 步 0）→ **数织贡献 = 0 格**，符合"第 1 关纯扫雷"的教学意图；
- **第 2–10 关**：禁用 B 时**全部卡住**（无任何可证明的下一步），启用 B 后**全部通关**（`full_solved=true`，无矛盾）→ "仅邻域推理会卡住、加数织线索可通关" 对第 2–10 关**全部成立**；
- **第 2 关数织贡献 = 12 格 ≥ 5**（B 步 12，其中探格 12 / 判雷 0）→ 用户要求"第二关的数织引入必须实打实"**满足**；
- 全 10 关 `contradiction = null`，且最终 36/49/64 格全部判定完毕（`revealed + known == n²`）。

与 `tools/report.md` 对账（同一口径下逐关比对）：本实现判定数为 `A/B = 22/0, 14/12, 17/11, 26/12, 25/7, 19/13, 29/15, 33/9, 33/8, 37/9`，报告表为 `22/0, 14/12, 17/11, 26/12, 25/7, 19/13, 29/15, 33/9, 33/8, 36/10`；**总步数、探格次数全部一致**，仅第 10 关 A/B 归属差 1 步（属报告 §口径说明 1 已事先披露的"归类口径差异"，不影响可解性）。报告 §0 "第 1 关 ✅ 能 / 第 2–10 关 ❌ 会卡住 / L2 连续块 12 格" 与实测一致。

---

## 3. C. 开局相容方案数 —— **通过（10/10 全部判定，无"未判定"）**

复现命令（两套实现互证）：

```powershell
# 实现1（本轮自写）：逐行 DFS + 列线索前缀剪枝 + 可见数字即时校验
& $PY verification\t13_level_check.py c
# 实现2（上一轮独立实现，原样复制、仅改输出路径）：行模式 DFS + 列前缀剪枝 + 数字校验；内部另有行模式全展开暴力交叉验证
$env:T8_LEVELS='D:\AI-Native casual game\tools\levels.json'
& $PY verification\_t13_c_xcheck.py
```

实现 1 真实输出（`logs/t13_c.txt`）：

```text
== C. 开局相容方案数（可见数字 + 雷总数 [+ 行列连续块]）==
  第 1关 showRuns=False 开局可见14格 ｜ 解数=26 节点=74613 用时=0.09s 真布局合法=True
  第 2关 showRuns=True  开局可见 6格 ｜ 解数=1 节点=21 用时=0.0s 真布局合法=True
  第 3关 showRuns=True  开局可见 8格 ｜ 解数=1 节点=44 用时=0.0s 真布局合法=True
  第 4关 showRuns=True  开局可见 6格 ｜ 解数=8 节点=584 用时=0.02s 真布局合法=True
  第 5关 showRuns=True  开局可见15格 ｜ 解数=1 节点=59 用时=0.0s 真布局合法=True
  第 6关 showRuns=True  开局可见 6格 ｜ 解数=2 节点=160 用时=0.0s 真布局合法=True
  第 7关 showRuns=True  开局可见12格 ｜ 解数=20 节点=863 用时=0.0s 真布局合法=True
  第 8关 showRuns=True  开局可见11格 ｜ 解数=68 节点=17285 用时=0.05s 真布局合法=True
  第 9关 showRuns=True  开局可见20格 ｜ 解数=1 节点=137 用时=0.0s 真布局合法=True
  第10关 showRuns=True  开局可见 9格 ｜ 解数=11 节点=16512 用时=0.03s 真布局合法=True
C 判定: PASS（失败项 0）
```

实现 2 交叉验证（`logs/t13_c_xcheck.txt` 关键行）：

```text
第 1 关：DFS full 解数=26 ｜ 暴力(组合枚举) 解数=26 ｜ 一致=True
第 2 关：DFS full 解数=1  ｜ 暴力(行模式全展开 480) 解数=1 ｜ 一致=True
第 3 关：DFS full 解数=1  ｜ 暴力(144) 解数=1 ｜ 一致=True
第 4 关：DFS full 解数=8  ｜ 暴力(18900) 解数=8 ｜ 一致=True
第 5 关：DFS full 解数=1  ｜ 暴力(1920) 解数=1 ｜ 一致=True
第 6 关：DFS full 解数=2  ｜ 暴力(15750) 解数=2 ｜ 一致=True
第 7 关：DFS full 解数=20 ｜ 暴力(2333772) 解数=20 ｜ 一致=True
第 8 关：DFS full 解数=68 ｜ 暴力超 300 万展开上限未执行 → 两套 DFS 均=68（一致）
第 9 关：DFS full 解数=1  ｜ 暴力(370440) 解数=1 ｜ 一致=True
第10 关：DFS full 解数=11 ｜ 暴力超上限未执行 → 两套 DFS 均=11（一致）
```

两套**不同实现**（不同剪枝、不同代码来源）在 10 关全部给出**相同解数**；其中 8 关另有"行模式全展开暴力"第三重验证一致。另每关都做了"真实布局满足全部约束"自检（`真布局合法=True`，防止枚举漏解）→ 数据可信。

**实测开局相容方案数（v0.3 新数据）**：

| 关 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 解数 | **26** | **1** | **1** | **8** | **1** | **2** | **20** | **68** | **1** | **11** |

> 这与"零猜测可完成"不冲突（SPEC §2 口径）：第 1/4/6/7/8/10 关开局线索有歧义，玩家靠探格获得新数字收敛，B 部分已证明它们仍零猜测可通关。
> **重要**：该结果与两份交付文档/SPEC 中写死的旧数字**不一致**（那些是 v0.2 旧数据集的测量值），详见 §6 文档对账——这是本轮主要"不通过"来源。

---

## 4. D. UI 运行时（v0.3 新 UI：爱心 / 结算 modal / 失败 modal / 键盘 / dataset） —— **通过（157/158）**

对象：`dist/冉政-游戏本体/index.html`（sha256 `f9c7d69c…`，48,555 B）。**未 npm install**，用自写最小 DOM stub（`verification/t13_ui_check.js`，基于对 `d_runtime_check.js` 的 stub 思路重写并扩展 `document.activeElement`/事件冒泡/静态标签解析等），把 HTML 内 10 关数据与全部脚本在 Node `vm` 中真实执行；通关驱动使用**本轮自写求解器**（§2）产出的逐步动作序列 `verification/t13_play_sequences.json`。

复现命令：

```powershell
& 'D:\develop\NodeJS\node.exe' verification\t13_ui_check.js
```

真实输出摘要（完整 `verification/logs/t13_d.txt`，157 PASS / 1 FAIL）：

```text
[PASS] D1 初始关卡=1 / 总关数=10 :: level=1 totalLevels=10
[PASS] D1 初始 hearts=❤❤❤ :: {"label":"剩余命数 3 / 3","text":"❤❤❤","count":3,...}
[PASS] D2 踩 1 雷：lives=2 / ❤❤♡ / aria-label 2/3 / 仍 playing
[PASS] D2 踩 2 雷：lives=1 / ❤♡♡ / aria-label 1/3
[PASS] D3 踩爆 3 雷：lives=0 / status=lost / ♡♡♡ / aria-label 0/3
[PASS] D3 modal 有 role=dialog / aria-modal=true / 有 aria-labelledby
[PASS] D3 失败标题含「雷」 :: 标题="踩到雷了"
[PASS] D4 第1关通关：status=won / lives=3        ← 10 关逐关同样通过
[PASS] D4 第10关 modal 标题正确 :: "全部通关！"
[PASS] D4 第10关 modal 按钮正确 :: [{"text":"↻ 重来本关","disabled":false},{"text":"全部通关","disabled":true}]
[PASS] D5 点「重来本关」：留在第2关、重置开局、命数 3、modal 关闭
[PASS] D5 点 disabled 的「下一关位」无任何反应
[PASS] D6 Tab 从按钮1 → 按钮2（焦点不跑出 modal）
[PASS] D6 Tab 从按钮2 → 循环回按钮1 / Shift+Tab 反向循环
[PASS] D6 Esc 关闭 modal；结算条出现并含「结算」再次打开入口
[PASS] D6 Enter 触发「下一关」→ 进入第2关、modal 关闭
[PASS] D7 初始 dataset 字段齐全 :: 9/9 齐全
[PASS] D7 初始 playing 时 DOM 不泄露雷坐标 :: 0 处泄露
[FAIL] D0 <title> 与 10 关版本一致（不应写「3 关体验」） :: 实测 <title>="雷线谜图 · 3 关体验"
===== D 汇总：157/158 通过 =====
```

逐项结论：

| 验收点 | 判定 | 实测证据 |
|---|---|---|
| 10 关全部可玩到 `status="won"`（每关用独立序列驱动；步数 22/26/28/38/32/32/44/42/41/46） | **通过** | 每关终态 `{status:"won", lives:3}`；逐关 modal 均出现 |
| 通关 modal：`role="dialog" aria-modal="true"`、标题含关卡号、按钮「重来本关」「下一关」 | **通过** | 1–9 关标题 `第 N 关 · 通关！`，按钮 `↻ 重来本关` + `下一关 →` |
| 最后一关：标题「全部通关！」且第二个按钮 `disabled=true`（非死按钮） | **通过** | `[{"text":"↻ 重来本关","disabled":false},{"text":"全部通关","disabled":true}]`；点击无反应 |
| 「重来本关」= 重置本关、「下一关」= 进下一关且 modal 关闭 | **通过** | 第 2 关实测：重置后 `{level:2,status:playing,revealed:6,lives:3,modal:closed}`；下一关后 `{level:N+1,status:playing,modal:closed}` |
| 爱心：初始 3 实心，踩 1/2/3 雷依次 `❤❤❤`→`❤❤♡`→`❤♡♡`→`♡♡♡`，`aria-label="剩余命数 n / 3"`，0 颗时 `status="lost"` | **通过** | 见上输出；全程容器保持 3 槽、每槽单字符 |
| 爱心不换行/不跳动 | **通过（近似）** | CSS `.hearts{min-width:calc(3 * 1.15em)}` + `.hearts .heart{width:1.15em}` 实测存在；3→0 期间 `childNodes.length` 恒为 3、每颗 `text.length==1`。**限制**：DOM stub 无真实排版引擎，这是固定槽宽 + 节点数近似，非像素级布局测量 |
| 失败 modal：踩爆 3 雷 → `status="lost"` + modal 标题含「雷」+「重来本关」可用；失败后规则行为不变 | **通过** | 标题 `踩到雷了`；失败后继续点雷 `lives` 仍 0、`revealed` 不变；失败 modal 无「下一关」 |
| 键盘：Tab/Shift+Tab 在 modal 内循环；Esc 关闭后有「结算」入口可再次打开；Enter 触发按钮 | **通过（Enter 为近似验证）** | Tab/Shift+Tab 实测循环于两个按钮；Esc 后 `result` 条含「结算」点击重开。**限制**：Enter 触发 click 是 HTML 原生 `<button>` 默认行为，DOM stub 不实现浏览器默认动作，故验证方式为：确认按钮是原生 `BUTTON` 且绑定 click → 桩内模拟 Enter→click → 路由正确进入下一关。**不是**对真实浏览器按键行为的像素级证明 |
| `document.body.dataset.gameState` 字段齐全（level/revealed/totalSafe/flagged/mines/lives/status + totalLevels/clearedLevels） | **通过** | 9/9 字段齐全；例 `{"level":1,"revealed":14,"totalSafe":30,"flagged":0,"mines":6,"lives":3,"status":"playing","totalLevels":10,"clearedLevels":0}` |
| `status!=lost` 时 DOM 不泄露雷坐标 | **通过** | 逐关逐步扫描：无 `class=mine` 格、无 `💣`、`dataset` 无 `mineSet`/`mines` 坐标数组（游玩全程 0 处） |
| 进度记忆/降级 | **通过（附加）** | 通关 10 关后 localStorage 写入；新会话从第 10 关继续；localStorage 抛异常时静默降级仍可玩 |
| `<title>` 文案 | **不通过（文案）** | 10 关版仍写 `<title>雷线谜图 · 3 关体验</title>`（发布 HTML 第 6 行） |

---

## 5. 发布包层 —— **通过（29/29）**

复现命令：

```powershell
& $PY verification\t13_release_check.py
```

真实输出（`verification/logs/t13_z.txt`，节选）：

```text
[PASS] Z2 ZIP 根目录含 index.html（无目录前缀） :: namelist=['index.html', 'README.txt']
[PASS] Z3 ZIP 内 index.html 与 dist 版本 sha256 一致 :: zip=f9c7d69ca249c067 dist=f9c7d69ca249c067
[PASS] Z3 ZIP 内 index.html 字节数一致 :: zip=48555 dist=48555
[PASS] Z4 零外部引用 'http://' :: 出现次数=0
[PASS] Z4 零外部引用 'https://' :: 出现次数=0
[PASS] Z4 零外部引用 'fetch(' :: 出现次数=0
[PASS] Z4 零外部引用 'XMLHttpRequest' :: 出现次数=0
[PASS] Z4 零外部引用 'WebSocket' :: 出现次数=0
[PASS] Z4 零外部引用 '<img' :: 出现次数=0
[PASS] Z4 零外部引用 '<link' :: 出现次数=0
[PASS] Z4 零外部引用 'import(' :: 出现次数=0
[PASS] Z4 只有 1 段内联 <script> 且无 src :: script 标签=1
[PASS] Z5 dist HTML == 当前 game 外壳 + 当前 levels.json 注入（逐字节可复现） :: rebuild=f9c7d69ca249c067 dist=f9c7d69ca249c067
[PASS] Z6 确定性打包：同内容+固定元数据重打包，sha256 与实测 ZIP 一致 :: rebuild=bdea61a74973bfc5 actual=bdea61a74973bfc5
[PASS] Z7 manifest.zip_sha256 == 实测 ZIP sha256 :: manifest=bdea61a74973bfc5 实测=bdea61a74973bfc5
[PASS] Z7 manifest.build_sha256 == 实测 dist sha256 :: manifest=f9c7d69ca249c067 实测=f9c7d69ca249c067
[PASS] Z7 manifest.levels_sha256 == 实测 levels.json sha256 :: manifest=891b416c1ac53e58 实测=891b416c1ac53e58
[PASS] Z7 manifest.ui_sha256 == 实测 game/index.html sha256 :: manifest=97161ea8844b7f01 实测=97161ea8844b7f01
[PASS] Z7 manifest.html_bytes == 实测 dist 字节数 :: manifest=48555 实测=48555
[PASS] Z7 manifest.zip_bytes == 实测 ZIP 字节数 :: manifest=12977 实测=12977
[PASS] Z7 manifest.level_count == 实测关数 :: manifest=10 实测=10
[PASS] Z7 manifest.zip_root_entries == 实测 namelist :: manifest=['index.html', 'README.txt'] 实测=['index.html', 'README.txt']
[PASS] Z7 manifest.checks 全为 true :: {"levels_roundtrip": true, "offline_selfcontained": true, "node_syntax": true, "clue_selfconsistent": true, "zip_root_index": true}
== Z 汇总：29/29 通过 ==
```

结论：ZIP 根目录含 `index.html`（另有 `README.txt`，不违反"根目录含 index.html"）；ZIP 内 `index.html` 与 `dist` **逐字节同 sha256**；零外部引用 8 类全 0；`build_manifest.json` 的 sha256/字节数/关数/条目/checks 与实测**全部一致**（含 `zip_sha256`）；构建为确定性打包——用同一内容 + 固定时间戳/属性独立重打包，sha256 与实测 ZIP **一致**；`dist` 也可由当前 `game` 外壳 + 当前 `levels.json` 逐字节复现（注意 Windows 文本模式 `\n→\r\n`，复现时已按同样换行处理）。

---

## 6. 文档对账 —— **不通过（多项陈旧/互相矛盾；游戏本体不受影响）**

> **复核期间对象发生变动**：`冉政-设计思路文档.md` 在我冻结后被改动（冻结版 sha256 `6beaa245…`，14,510 B，mtime 16:46；复核中实测 live 版 sha256 `7618dd2c5d3d5e275fb8f025258ec2e27f09a0022d1a65de91c567afcce8a631`，16,521 B，mtime **17:18:18**）。live 版新增 §3.1/§3.2（竞品核查，属另一条线的修复），并因此顺带提到爱心与"第 2 关 12 格 / 第 10 关 10 格"，但**第 6 节的陈旧项在 live 版中仍然存在**（仅行号下移 24 行）。其余对象（dist/ZIP/levels.json/report.md/SPEC.md/迭代文档/manifest）在复核期间 sha 未变。提交前请重新核对最终冻结 sha。

### 6.1 `tools/report.md` —— **部分不通过**

**通过项**：逐关尺寸/雷数/`showRuns`/是否需要数织/探格次数与实测一致；推理序列 **10 关共 351 步**经本轮"干净暴力枚举逐步重放"全部可复现、能推完全盘、雷位与真值一致（`verification/t13_report_replay.py`，见下）；`tools/report.md` 的探格次数 16/19/20/30/23/22/33/30/28/32 与本轮实测 10/10 相同。

```text
== 重放 tools/report.md 的逐关推理序列（干净暴力枚举） ==
  第 1关 报告步数=22 ｜ 逐步可复现=是 推完全盘=是 雷位与真值一致=是
  ...
  第10关 报告步数=46 ｜ 逐步可复现=是 推完全盘=是 雷位与真值一致=是
重放判定：PASS（失败关数 0）
```

**不通过/矛盾项（文档说 X、实测 Y）**：

| # | 位置（冻结版行号） | 文档说 X | 实测 Y | 判定 |
|---|---|---|---|---|
| R1 | `tools/report.md:1` | 标题 `# 雷线谜图 v0.1 — 生成与校验报告` | 发布对象是 **v0.3**（爱心/modal/重排 10 关） | 版本头陈旧 |
| R2 | `tools/report.md:12–20` 表"开局相容方案数" | 第 2–10 关全部"未判定（含连续块线索，组合空间过大）" | **全部可判定**且空间极小（本轮两套实现 + 暴力交叉验证，耗时 0.0–0.2s/关）：`1/1/8/1/2/20/68/1/11` | 陈旧 |
| R3 | `tools/report.md:24` | "开局线索下有多个相容方案的关卡：第1关=26" | 实测 >1 的关卡为 **第 1、4、6、7、8、10 关**（26/8/2/20/68/11） | 披露不完整 |
| R4 | `tools/report.md:483` | "…改为**转述独立复核另写实现的实测值**（出处 `tools/independent_counts.json`）" | `tools/independent_counts.json` **不存在**；实际文件是 `tools/independent_counts_v1_10关.json`，且其 `basis_levels_sha256=a7a1dd3b…`、`basis_html_sha256=de013c5b…` 均为 **v0.2 旧版**，数值 26/8/5985/1/1/1/2/1/1/4 与 v0.3 实测不符 | 引用路径错误 + 数据基于旧版 |
| R5 | 同上 + `tools/report.md:12–20` | 报告一边说"转为转述独立实测值"，一边表里仍写"未判定" | 自相矛盾的两种口径并存（且转述源已过期） | 表述不一致 |
| R6 | 连续块判定格数（表 L11–20） | 0/12/11/12/7/13/15/9/8/10 | 本轮独立实现 0/12/11/12/7/13/15/9/8/**9**，第 10 关 A/B 归属差 1 步（总步 46、探格 32 一致） | **通过（已披露口径）**：报告 §口径说明 1 已写明归类随执行次序变化 |
| R7 | 逐关推理序列 | 10 关 351 步 | 干净枚举逐步重放 **351/351 可复现**，推完全盘、雷位与真值一致；其中第 2、10 关与本轮求解器步序不同但每步均可由声明规则推出 | **通过** |

### 6.2 `docs/SPEC.md`（v1.2）—— **不通过（改动 ① 未同步；相容方案数陈旧）**

**已同步/通过项**：§1 状态栏爱心（`❤❤❤`→`❤♡♡`→`♡♡♡`、`aria-label`、不逐颗朗读）与 §4.4；§4.6 结算 modal（role=dialog/aria-modal、重来/下一关、最后一关无死按钮、失败复用同一 modal、键盘可达、按钮 ≥44px）—— 与 D 实测一致（**②③ 已同步**）。

**不通过项**：用户改动 ①「数织提前到第 2 关」**完全没有同步进 SPEC**，且与发布数据直接矛盾：

| # | 位置 | 文档说 X | 实测 Y |
|---|---|---|---|
| S1 | `docs/SPEC.md:20` | "10 关初版中第 1–3 关不显示、第 4–10 关显示" | 第 1 关 false、**第 2–10 关 true** |
| S2 | `docs/SPEC.md:56` 字段表 | "第 1–3 关 `false`，第 4–10 关 `true`" | 同上（虽然同句写了"以数据为准"，但实例映射是旧的） |
| S3 | `docs/SPEC.md:77–81` §3 难度带表 | "1–3 教学带只有邻域数字 / 第 4 关引入第二套线索 / 5–7…" | 第 1 关纯邻域、**第 2 关即引入**、第 2–10 关都必须用数织 |
| S4 | `docs/SPEC.md:83` | "教学文案只在第 1、4、8 关非空" | 实测 `teach` 非空关卡为 **1、2、6** |
| S5 | `docs/SPEC.md:68` | "第 1 关 26、第 2 关 8、第 3 关 5985、第 7 关 2、第 10 关 4，其余 5 关为 1" | 实测 **26/1/1/8/1/2/20/68/1/11**；>1 的关卡是 **1、4、6、7、8、10** |
| S6 | `docs/SPEC.md:79` | "5–7…**只用邻域推理会推死、必须用连续块线索**" | 实测第 **2** 关即已必须（范围写小了） |

> 契约文件 §2 末尾还写着"必须如实披露（>1 的关卡不得被描述成唯一解）"——按本轮实测，现文档披露的清单本身就不如实（漏了 4/6/8 关，且 2/3 关旧值反而 >1）。

### 6.3 `冉政-设计思路文档.md` —— **不通过（① 部分同步但自相矛盾；②③ 未完整同步；多处旧数字）**

冻结版 sha256 `6beaa245…`（14,510 B）；live 17:18 版 sha256 `7618dd2c…`（16,521 B）。下表行号以**冻结版**为准；live 版在 §3 新增两小节后，**§3 之后的行号整体 +24**（L145→L169 等）。

| # | 位置（冻结版行号） | 文档说 X | 实测 Y | 判定 |
|---|---|---|---|---|
| D1 | L5 | `- **版本**：v0.2（10 关初版）` | 交付是 **v0.3**（三项改动已进游戏） | 版本头陈旧（live 版仍 v0.2） |
| D2 | L27 | "线索显示：第 1–3 关**不显示**行列线索（纯扫雷教学），第 4 关起显示" | L1 false、**L2–10 true**；与同文档 L63/L72 的"第 2 关立刻上融合"**自相矛盾** | 不通过（live 仍在） |
| D3 | L38、L158 | "本作的第 4–10 关用求解器证明…" | 应为 **第 2–10 关** | 陈旧（live 仍在） |
| D4 | L145 | "约 34 KB 文本 / 37 KB UTF-8 字节" | 发布 HTML **48,555 B**（46,056 字符，含 CRLF；归一化 44,038 字符） | 陈旧（live 仍在） |
| D5 | L149 | "本作 <40 KB" | 48,555 B ≈ **48.6 KB** | 陈旧（live 仍在） |
| D6 | L159 | "第 1、4、8 关给教学文案" | 实测 teach 非空：**1、2、6** | 陈旧（live 仍在） |
| D7 | L167、L168 | "第 1–3 关 26 / 8 / 5985，第 4–10 关 1 / 1 / 1 / **2** / 1 / 1 / **4**；第 7、10 关歧义" | 实测 **26/1/1/8/1/2/20/68/1/11**；歧义关卡 **1、4、6、7、8、10** | 陈旧（live 仍在） |
| D8 | L63、L87 | "第 2 关就引入行列线索 / 早期版本…用户建议提前到第 2 关" | 与数据一致 | **通过（① 叙述已同步）** |
| D9 | live 版 L75、L76 | 新段提到"3 颗爱心 ❤❤❤→♡♡♡"与"第 2 关 12 格、第 10 关 10 格" | 爱心实测 ✓；L2 数织贡献 12 ✓；L10 本轮实现 9（报告口径 10，属已披露归类差） | **② 已同步（仅 live 版）**；L10 为口径差 |
| D10 | 全文 | 未提及结算 modal | 实测 modal 已实现（D 全通过） | **③ 未同步（缺失）** |
| D11 | §5.1 表（L76–89） | 尺寸/雷数/数织需求 | 与实测一致（L1 6/6、L2 6/7 且必须数织…L10 8/8/14） | **通过** |

### 6.4 `冉政-迭代优化过程文档.md` —— **不通过（三项改动已记录，但数据附录整表是 v0.2）**

| # | 位置 | 文档说 X | 实测 Y | 判定 |
|---|---|---|---|---|
| I1 | L81–97 §2.8 | 三项改动（① 数织提前 + 第 2 关 `min_runs=5` 且贡献 12；② 爱心；③ 结算 modal） | ① 实测 L2 `showRuns=true` 且数织贡献 **12**（≥5 ✓）；② 爱心 3→2→1→0 ✓；③ modal 全路径 ✓ | **通过（三项改动已记录）** |
| I2 | L5 | `- **版本**：v0.2` | 交付 v0.3（同文档 §2.8 已写 v0.3） | 版本头陈旧 |
| I3 | L57 | "只有第 1 关、第 4 关、第 8 关给教学文案" | 实测 **1、2、6** | 陈旧 |
| I4 | L207–218 §5 数据附录整表 | 尺寸 `6,6,6,6,6,7,7,7,8,8`；雷数 `6,6,7,7,8,8,9,10,11,12`；第 1–3 关"行列线索 —"；连续块判定 `0,0,0,14,14,16,15,14,37,24`；探格 `16,12,21,14,14,18,26,29,39,32` | 实测尺寸 `6,6,6,7,7,7,8,8,8,8`；雷数 `6,7,8,8,9,10,11,12,13,14`；仅第 1 关无线索；连续块判定 `0,12,11,12,7,13,15,9,8,9(报告 10)`；探格 `16,19,20,30,23,22,33,30,28,32` —— **整表仍是 v0.2 数据** | 不通过（严重：与 `tools/report.md`/实测全面不符） |
| I5 | L221 | "第 1–3 关（无行列线索）接受率显著更低" | 只有第 1 关无线索 | 陈旧 |
| I6 | L230 §6.3 | "第 1–3 关 26 / 8 / 5985，第 4–10 关 1 / 1 / 1 / 2 / 1 / 1 / 4；其中第 1、2、3、7、10 关 >1" | **26/1/1/8/1/2/20/68/1/11**；>1 为 **1、4、6、7、8、10** | 陈旧 |
| I7 | L148–149、L168 | 历史段引用"第 2 关 8 / 第 3 关 5985 / 1/1/1/2/1/1/4"并称报告"已改为转述独立实测值（出处 tools/independent_counts.json）" | 旧数据；引用文件不存在（见 R4） | 陈旧（历史叙述未标注"已随 v0.3 数据失效"） |
| I8 | L97 | "v0.3 交付状态：外壳 39.9 KB…发布包 48.6 KB / ZIP 13.0 KB…" | `game/index.html` 39,913 B；dist 48,555 B；ZIP 12,977 B | **通过**（四舍五入一致） |
| I9 | L228、L232 | T11 复核结论/P1 关闭表述 | 与 `report_t11.md` §13 一致；本轮未重复判定（不属于 v0.3 三项改动） | **未判定（超出本轮范围）** |

### 6.5 发布 HTML 文案

| # | 位置 | 文档/页面说 X | 实测 Y | 判定 |
|---|---|---|---|---|
| H1 | `dist/冉政-游戏本体/index.html:6` | `<title>雷线谜图 · 3 关体验</title>`（ZIP 内同一文件） | 实际 **10 关**；页内关卡数、manifest 均为 10 | **不通过（文案陈旧，非玩法缺陷）** |

---

## 7. 总体判定

### 7.1 分项判定

| 层 | 判定 | 依据 |
|---|---|---|
| A 关卡数据自洽 | **通过** | 10/10；内嵌 LEVELS == levels.json；外壳可复现 |
| B 零猜测可解 + 教学带意图 | **通过（10/10）** | 第 1 关仅邻域通关且数织贡献 0；第 2–10 关仅邻域全部卡住、加数织全部通关；**第 2 关数织贡献 12 ≥ 5** |
| C 开局相容方案数 | **通过（10/10 全部判定）** | 两套独立实现 + 8 关暴力交叉验证一致：`26/1/1/8/1/2/20/68/1/11` |
| D UI 运行时（v0.3 新 UI） | **通过（157/158）** | 10 关全部玩到 won、逐关 modal、爱心递减、失败 modal、键盘、dataset、无雷坐标泄露；唯一失败为 `<title>` 文案 |
| 发布包 | **通过（29/29）** | ZIP 根 `index.html`、与 dist 同 sha256、零外链、manifest 全字段一致、确定性打包可复现 |
| 文档对账 | **不通过** | SPEC 改动①未同步 + 相容解数陈旧；report.md 版本头/引用文件/未判定；设计/迭代文档旧数字、旧数据附录、教学关清单、体积数字；HTML 标题陈旧 |
| 文档对账中的"游戏本体正确性" | 不受影响 | 上述全部是文字/数字同步问题，A–D 实测游戏本体与发布包均正常 |

### 7.2 最终结论

- **游戏本体 + 提交 ZIP：通过**（v0.3 三项改动全部在真实 DOM 桩中验证成立，10 关可零猜测通关，发布包结构与自包含性全通过；仅 `<title>` 文案陈旧，建议改但不阻断）。
- **整个交付物（游戏 + 文档）：有条件通过**。阻断评审观感的是**文档与实测不一致**：用户改动 ①（数织提前到第 2 关）没有同步进 `docs/SPEC.md`（契约文件仍写"1–3 关纯扫雷、第 4 关引入"），且 `tools/report.md`、SPEC、两份交付文档里的"开局相容方案数/教学关清单/数据附录/体积数字/版本号"仍混用 v0.2 旧数据；`tools/report.md` 还引用了一个**不存在的文件**并保留"未判定"口径。

### 7.3 仍不通过清单（按严重度）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| P1 | `docs/SPEC.md:20,56,77–83` | 改动 ① 未同步：仍写第 1–3 关无线索、第 4 关引入、teach 只在 1/4/8 关 | 改为"第 1 关 false、第 2–10 关 true；第 1 关纯邻域、第 2 关引入数织；teach 非空 = 1/2/6" |
| P2 | `docs/SPEC.md:68`；`冉政-设计思路文档.md:192`；`冉政-迭代优化过程文档.md:230` | 开局相容方案数仍写旧值（26/8/5985；1/1/1/2/1/1/4；"其余 5 关为 1"） | 用本轮两套实现互证实测值替换：**26/1/1/8/1/2/20/68/1/11**，并披露 >1 的关卡 = **1、4、6、7、8、10** |
| P3 | `tools/report.md:1,12–20,24,483` | 版本头 v0.1；第 2–10 关仍标"未判定"且与"已转述独立实测值"自相矛盾；引用不存在的 `tools/independent_counts.json`（实际为 `independent_counts_v1_10关.json` 且基于 v0.2 旧 sha） | 升版本头；把第 2–10 关改为实测值+出处（重测后更新/重命名独立计数文件并写明 basis sha），删除"未判定"或明确标注"生成器未枚举、独立复核已实测" |
| P4 | `冉政-迭代优化过程文档.md:207–218,221,57,5` | §5 数据附录整表仍是 v0.2（尺寸/雷数/线索/判定格/探格/接受率全不对）；§2 教学关 1/4/8；版本头 v0.2 | 按 v0.3 数据重算整表；教学关改 1/2/6；版本头升 v0.3 |
| P5 | `冉政-设计思路文档.md:5,27,38,159,169,173,182,183,192`（live 版对应 +24 行） | 版本头 v0.2；L27 与 L63 自相矛盾；第 4–10 关/教学关 1/4/8；34 KB/37 KB 与 <40 KB；旧解数；未提结算 modal | 统一为 v0.3 口径：L2 起必须数织、teach = 1/2/6、字节数 48.6 KB、解数用实测值；补一句结算 modal |
| P6 | `dist/冉政-游戏本体/index.html:6`（ZIP 内同一文件） | `<title>` 仍为"雷线谜图 · 3 关体验" | 改为"雷线谜图 · 10 关"（或去掉关数），重新 `build_release.py` 出包并更新 manifest |

> 注意：P6 的修改会改变 HTML sha256 ⇒ ZIP、manifest 的 `build_sha256/zip_sha256` 必须重新生成（当前构建脚本已自动处理，但重新打包后需再跑一次 `verification/t13_release_check.py` 对账）。

### 7.4 上线前必须修的 top 3

1. **修 `docs/SPEC.md` 的改动 ①（契约与数据矛盾，最容易被评审抓）**：`showRuns` 的旧映射、§3 难度带表、教学关清单全部按"第 2 关引入数织"重写；同时把 §2 的开局相容方案数旧值换成本轮实测值。
2. **重写 `tools/report.md` 的相容方案数披露与引用**：第 2–10 关不再是"未判定"（实测可算且极小），把不存在的 `tools/independent_counts.json` 引用改为真实文件并更新为 v0.3 基准（或按新数据重测后写回），消除"未判定 vs 已实测"的自相矛盾；版本头升 v0.3。
3. **按 v0.3 数据重算迭代文档 §5 数据附录整表，并统一三份文档的旧数字/旧版本号**（尺寸、雷数、行列线索、数织判定格、探格、教学关 1/2/6、体积 48.6 KB），顺带修 HTML `<title>` 后重新出包并复核 manifest。

---

## 8. 复现命令汇总（全部真实执行过）

```powershell
$env:PYTHONIOENCODING='utf-8'
$PY='C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$NODE='D:\develop\NodeJS\node.exe'

# A 数据自洽（10 关、内嵌==文件、外壳可复现）
& $PY verification\t13_level_check.py a
# B 零猜测可解性 + 教学带意图（第1关纯邻域/第2-10必须数织/第2关贡献≥5）
& $PY verification\t13_level_check.py b
# C 开局相容方案数（自写实现）
& $PY verification\t13_level_check.py c
# C 第二实现互证（行模式 DFS + 全展开暴力；原样复制 c_uniqueness.py，仅改输出路径）
$env:T8_LEVELS='D:\AI-Native casual game\tools\levels.json'
& $PY verification\_t13_c_xcheck.py

# D UI 运行时（自写 DOM stub；10 关全玩到 won / 爱心 / modal / 键盘 / dataset / 不泄露雷）
& $NODE verification\t13_ui_check.js

# 发布包（ZIP 根 index.html / 与 dist 同 sha / 零外链 / manifest / 确定性打包）
& $PY verification\t13_release_check.py

# 报告推理序列逐步重放（干净暴力枚举，351 步）
& $PY verification\t13_report_replay.py

# 文本/文档核对所引用的关键行（只读）
Select-String docs\SPEC.md -Pattern '第 1–3 关|第 4|teach|26|5985'
Select-String tools\report.md -Pattern 'v0\.1|未判定|independent_counts'
Select-String 冉政-设计思路文档.md -Pattern 'v0.2|第 1–3 关|第 4–10 关|34 KB|40 KB|1、4、8|5985'
Select-String 冉政-迭代优化过程文档.md -Pattern 'v0.2|第 1 关|第 4 关|第 8 关|207|26 / 8 / 5985|1 / 1 / 1 / 2'
```

产物清单（`verification/` 下，本报告与脚本未触碰 `game/ tools/ docs/ research/` 及根目录两份 `冉政-*.md`）：

- `report_t13.md`（本文件）
- `t13_level_check.py`、`_t13_c_xcheck.py`、`t13_ui_check.js`、`t13_release_check.py`、`t13_report_replay.py`
- `t13_out_a.json`、`t13_out_b.json`、`t13_out_c.json`、`t13_out_c_xcheck.json`、`t13_out_d.json`、`t13_out_z.json`、`t13_out_report_replay.json`、`t13_play_sequences.json`
- `logs/t13_a.txt`、`logs/t13_b.txt`、`logs/t13_c.txt`、`logs/t13_c_xcheck.txt`、`logs/t13_d.txt`、`logs/t13_z.txt`、`logs/t13_report_replay.txt`
- `frozen_t13/`（本轮冻结快照；设计文档另存 `frozen_t13/design_doc_17h18.md` 为复核中变动后的 live 版本）

---

## 9. 本轮方法与"防假阳性"自证

- **C 计数**：两套**不同来源**的实现（本轮自写 DFS vs 上一轮 `c_uniqueness.py` 的 DFS）+ 8 关"行模式全展开暴力"第三重验证，10 关解数完全相同；每关附加"真实布局必须满足全部约束"自检（若枚举漏解会被发现）。
- **B 可解性**：求解器的"数织规则"用 2^n 全枚举这一显然正确的实现（不写剪枝逻辑）；并额外用**干净暴力枚举逐步重放** `tools/report.md` 的 351 步序列，逐条验证"声明的规则确实强制该格"，未发现报告夸大。本报告不引用上一轮 `b_solver.py` 的 `line_placements`（`report_t11.md` §13 已证实其有 bug 会造成假阳性）。
- **D**：DOM stub 是对 v0.3 新 UI 的独立重写，断言均从**实测 DOM 状态**读取；关键行为另用源码阅读交叉确认。限制（无真实排版引擎、Enter 依赖原生 button 语义）已在 §4 明示，不夸大为"真机通过"。
- **发布包**：ZIP 结构与 sha 用 Python `zipfile` 独立读取；确定性打包靠"同内容 + 固定元数据重打包后 sha256 相同"证明，而非只看 manifest 自述。