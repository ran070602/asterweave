# T11 独立复核（接手）报告：10 关发布包 · 结构与 3 项文档类遗留闭环

> 复核者：**verify-t12**（接手 task-11；前一位复核者 **verify-t8** 已完成 A–D 原始测量，但两次在写汇总报告前中断）
> 复核日期：2026-10-21
> 交付物：本文件（只写 `verification/` 下）

## 0. 复核对象、来源说明与本次改动

### 0.1 被复核对象（以 sha256 为准）

| 对象 | 路径 | sha256 | 字节 |
|---|---|---|---|
| 游戏本体（发布 HTML） | `dist/冉政-游戏本体/index.html` | `de013c5bafd78c15ed97f3008e7ef1dc4407bb5725fdbe8b3968d83facea8a60` | 37,675 |
| 提交包 | `冉政-游戏本体.zip` | `12c3ade14a69b87cabba7084c38a94f430adf3ef974b48a1ea57a3c0bb3a0530` | 10,112 |
| 关卡数据 | `tools/levels.json` | `a7a1dd3b50dd86d972c5c95b51a875a51a350d6ec1c625a5fe505c1e8093e18c` | 10,707 |
| 生成报告 | `tools/report.md` | `b7ca7b3e559174ec4b5c01405a45a3037643d623e2016d91f274d87381174104` | 24,359 |
| 规则契约 | `docs/SPEC.md`（v1.2） | `524ab1f02e2cc4efa94af753a516fcc108c9d07cc395cd4876d70070893f6393` | 9,794 |
| 设计思路文档 | `冉政-设计思路文档.md` | `2a31ebaf2bee31c1c4b40bd7e33772dbe00680a7184edffe01adb1b10990aac8` | 13,907 |
| 迭代优化过程文档 | `冉政-迭代优化过程文档.md` | `057ce916fb7d20ce0a480eefb0e15633417ba7c06076ffe6051d98c142339544` | 20,973 |
| 构建清单 | `dist/build_manifest.json` | `15acccb43bda186778583b5449e63069e2058840ee2cd58ab4da24f747e39e4a` | 835 |
| 独立计数（作者转述我的前一位复核者实测） | `tools/independent_counts.json` | `17e67ae0caef231d16e1ef54cdc5eeb6d8ec8ab9a501c2b68ceb0fd8a567cef0` | 874 |

任务书给出的三个预期 sha256（HTML `de013c5b…`、`levels.json` `a7a1dd3b…`、ZIP sha256 见 manifest）与上表**逐一对上**；`de013c5b…` 是 T8/T11 冻结副本 `verification/frozen10/dist_index_snapshot.html` 的同一修订，也是本次复核期间未再变动的修订。

### 0.2 来源说明（必须分清谁的劳动）

- **A–D 四组原始测量的脚本、设计口径与第一轮输出，均由前一位复核者 verify-t8 产出**（`verification/a_data_check.py`、`b_solver.py`、`b2_compare_report.py`、`b3_replay_report.py`、`c_uniqueness.py`、`d_runtime_check.js`、`t11_release_check.py`；原始输出 `verification/out_*.json` 与 `verification/logs/*_10.txt`）。**这些脚本不是我写的，我也不主张其设计归我。**
- **本次（T11 接手轮）由我 verify-t12 做的是**：① 审计这些脚本与生成器无代码复用；② 用它们**指向当前 10 关产物复跑全部关键测量**，取得新鲜证据（日志 `verification/logs/*_t12.txt`，输出 `out_a/b/b2/b3/c/d/t11_release.json` 已按本次复跑覆盖）；③ 逐项判定发布包与 3 项文档类遗留的闭环；④ 补做两处前一轮未做完的核对（ZIP 内文件逐条 sha256、`debug` 级序列重放定位）。
- verify-t8 的**第一轮原始输出已在我复跑前整份留档**到 `verification/prev_verify_t8_raw/`（含 `out_*.json`、`logs/*10.txt`、以及全部脚本原件 `scripts/`），以免复跑覆盖后无法追溯。
- 两轮冻结快照并存：`verification/frozen10/`（verify-t8，15:30–15:32 抓取，其 `report.md`/`SPEC_v1.1.md`/`build_manifest.json`/`release.zip` 均为**作者本轮修复前**的版本）、`verification/frozen11/`（我，抓取上表当前版本，供复现）。

### 0.3 我对前一位复核者脚本做的改动（仅 `verification/` 内，原件已留档）

只改了 `verification/t11_release_check.py`，共 3 处，全部在文件内以 `T12 改动` 注释标出：

1. 冻结目录可用环境变量覆盖：`FROZEN = Path(os.environ.get("T11_FROZEN", ROOT/"verification"/"frozen10"))`（不设变量时与原版行为一致）。
2. `SPEC` 文件名随修订号自适应（`frozen11` 下取 `SPEC_v1.2.md`）。
3. 把两处**写死在断言文本里的结论**改为按当前文档动态判定：
   - 原 `check("manifest 记录了 ZIP 的 sha256", "zip_sha256" in manifest, ...)` → 追加一条 `manifest.zip_sha256 == 实测 zip_sha256`（这正是本次要闭环的第 3 项）。
   - 原 `check("报告是否披露了所有 >1 解的关卡（L1-L3 之外）", False, "…仅披露 L1/L2/L3…")`（**硬编码 False**，且断言文本写死了旧报告的缺陷）→ 改为「正文披露段必须点名全部 >1 解关卡，且表格数字与独立实测一致」。

原件：`verification/prev_verify_t8_raw/scripts/t11_release_check.py`；改后：`verification/t11_release_check.py`（sha256 `248730545e6e5af943febcb2e30e1f4f5b3e91763169d38c7b9ce8db5db70ff7`）。

**未改**：`a_data_check.py` / `b_solver.py` / `b2/b3` / `c_uniqueness.py` / `d_runtime_check.js` 一字未动。

---

## 1. 脚本独立性审计 —— **通过**

要求「不得 import 或复制 `tools/generate_levels.py`」。核实方式与证据：

```powershell
Select-String -Path verification\*.py,verification\*.js -Pattern 'generate_levels|from tools|import tools'
```

输出只有注释/文档字符串里的"不 import…"声明，**没有任何脚本真的 import 生成器**：

```
b3_replay_report.py:24:  # 复用我自己（T8）写的求解器原语：合法，因为它不是 tools/generate_levels.py 的代码
b_solver.py:10:  独立性声明：本文件完全自写，不 import、不复制 tools/generate_levels.py 的任何代码。
```

关键实现逐处对照（结构不同，非复制）：

| 能力 | 生成器 `tools/generate_levels.py` | 复核脚本 |
|---|---|---|
| 行列连续块枚举 | `line_patterns(n, runs, fixed)`：`fixed` 是**索引集合**；内部 `place(ci, ri, cur)` 累积 | `b_solver.line_placements(n, runs, known)`：`known[]` 是 `None/0/1` **逐格三态**，返回 `(placements, contradictory)`；`c_uniqueness.row_patterns_exact/row_patterns_free` 又是另一套（按行生成候选模式） |
| 邻域推理 | `solve()` 内嵌闭包 `flood/nb_pass/runs_pass/apply` | `b_solver.Player` 类 + `apply_a/apply_b`，`reveal()` 用显式栈 BFS |
| 计数 | `_count_noruns_dfs` + `count_solutions_exact(cap=5_000_000)` | `c_uniqueness.method_dfs`（列前缀剪枝）+ `method_bruteforce`（`itertools.product` 全展开）+ `method_comb`（组合枚举），**且用后两者交叉验证前者** |

`c_uniqueness.py` 的交叉验证在本次复跑中 10/10 一致（见 §4），说明它至少有两套互相独立的实现，而不是把生成器结论抄一遍。

---

## 2. A. 数据自洽 —— **通过**（含一节已过期的文档对账项）

```
python verification\a_data_check.py "dist\冉政-游戏本体\index.html"
```

- 逐关 `rowRuns`/`colRuns` 与 `mines` 重算：**10/10 一致**（含历史 bug「列线索退化为最后一列」的专项检查 `A1-x-5 列线索未退化为「所有列相同」`，10/10 PASS）。
- `opening` 为安全格且邻域雷数 = 0：10/10 PASS（实测 flood 展开 14/17/8/15/11/15/8/6/9/14 格）。
- 行/列线索数字和 == 雷数：10/10 PASS。
- **内嵌 LEVELS == `tools/levels.json`**：`A3-3` / `A3-4` PASS（规范化 JSON 长度 3326 vs 3326）。
- 断言计数：`out_a.json` 共 **172 项，166 PASS / 6 FAIL**；其中 164 项（A1/A2 逐关 160 + A3 注入块 4）**全部 PASS**，6 项 FAIL 全部来自脚本里名为「SPEC v1.1 文档 vs 10 关实测数据」的一节。

**这 6 项 FAIL 的性质必须说清（避免误判）**：它们是上一轮针对 **v1.1** 写的"文档说 X == 数据"断言，断言文本硬编码在脚本里（`a_data_check.py:214-239`，`SPEC_SIZE_3LV`、`"仅第 2、3 关显示"` 等）。SPEC 已升 v1.2 泛化后，这 6 项**必然 FAIL**，属于脚本口径过期，**不等于当前文档仍有 6 处残留**。当前文档的真实残留由 §7 逐行核查给出（结论：6 处中 5 处已修，1 处残留）。

```
[FAIL] SPEC §1 措辞「连续块线索仅第 2、3 关显示」== 10 关数据 :: …实测 showRuns=true 的关卡=[4,5,6,7,8,9,10]
[FAIL] SPEC §4.5「第 3 关 teach 为空」== 10 关数据 :: …实测 teach 为空的关卡=[2,3,5,6,7,9,10]
（其余 4 项同类，全部是旧版措辞断言）
A 部分总判定: 存在不通过项   ← 退出码 1，原因即上述 6 项过期断言
```

复现：`python verification\a_data_check.py "dist\冉政-游戏本体\index.html"`（日志 `verification/logs/a_data_check_t12.txt`）。

---

## 3. B. 零猜测可解性与教学带 —— **通过（10/10）**

```
python verification\b_solver.py
```

本次复跑（`verification/logs/b_solver_t12.txt`）逐关结论：

```
第 1 关[教学带:纯(a)]: 只用(a)通关=True ; (b)贡献格数=0 ; => 通过
第 2 关[教学带:纯(a)]: 只用(a)通关=True ; (b)贡献格数=0 ; => 通过
第 3 关[教学带:纯(a)]: 只用(a)通关=True ; (b)贡献格数=0 ; => 通过
第 4 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=16 ; => 通过
第 5 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=15 ; => 通过
第 6 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=18 ; => 通过
第 7 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=25 ; => 通过
第 8 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=27 ; => 通过
第 9 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=41 ; => 通过
第 10 关[教学带:需(b)]: 只用(a)通关=False ; 加(b)通关=True ; (b)贡献格数=37 ; => 通过
B 部分总判定: 10 关教学带意图全部满足
```

- 第 1–3 关「只用邻域推理(a)」即推完全盘，且 (b) 贡献 = 0 —— 符合 SPEC §3「教学带」。
- 第 4–10 关「只用 (a) 会彻底卡住 / 加上 (b) 可推完全盘」。
- 每关(a)+(b) 推完后：`判定雷数 == 真实雷数`、`已翻开格与真雷不冲突`、`剩余未判定 = 0`，10/10。
- 无超时（单关耗时 0.000–0.016s），无"未判定"，无矛盾。

---

## 4. C. 开局相容方案数 —— **通过（10/10 全部判定，无"未判定"）**

```
python verification\c_uniqueness.py        # 每关预算 120s
```

本次复跑（`verification/logs/c_uniqueness_t12.txt`）结果与任务书预期 **26/8/5985/1/1/1/2/1/1/4 完全一致**：

| 关 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| 本轮实测相容方案数 | 26 | 8 | 5985 | 1 | 1 | 1 | **2** | 1 | 1 | **4** |
| DFS 节点数 | 17813 | 28 | 1216360 | 7 | 10 | 9 | 29 | 18 | 16 | 19 |
| 用时 | 0.28s | 0.00s | 15.95s | 0.00s | 0.00s | 0.00s | 0.00s | 0.00s | 0.00s | 0.00s |
| 方法1 vs 方法2/3 交叉验证 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 是否超预算 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 | 否 |

- 10 关**全部在预算内穷尽**，没有"未判定"；含连续块线索的 4–10 关也给出了确切数字（第 3 关 DFS 121.6 万节点 / 15.95s 是最大开销）。
- 每关均有 `自检：真实布局满足全部约束`，且两种独立枚举方法给出的解数一致（第 1/3 关还用第三套组合枚举复核）。
- 与 `tools/report.md` §0/§1、`docs/SPEC.md` L68、`tools/independent_counts.json` 与两份交付文档的数字**逐关一致**。
- `tools/independent_counts.json` 的 `basis_levels_sha256` / `basis_html_sha256` 与当前 `tools/levels.json` / `dist` HTML 实测 sha256 **相等**（已用脚本核对），出处标注真实。
- 脚本小结里的措辞「解数=1 才算唯一；'未判定'不算通过」是**上一轮判据**的遗留标签；本作已把判据改为「零猜测可完成 + 如实披露方案数」（SPEC v1.2 §2/§6.1），因此"不唯一（不通过）"字样**不应**读作关卡缺陷——可解性由 §3 独立证明。

---

## 5. D. DOM 桩运行时 —— **通过（194/194）**

```
node verification\d_runtime_check.js "dist\冉政-游戏本体\index.html"
```

```
== D 部分小结：194/194 通过，0 不通过 ==
被复核的 game/index.html: sha256=de013c5bafd78c15ed97f3008e7ef1dc4407bb5725fdbe8b3968d83facea8a60 bytes=36035 …
```

> 说明：脚本这一行打印的 `bytes=36035` 实为 JS 字符串长度（字符数，脚本变量名沿用 `html.length` 属误标）；同一文件的 UTF-8 字节数实测为 **37,675**（见 §0）。

关键子项（均在 `verification/logs/d_runtime_check_t12.txt` 可查）：

- **10 关全部玩到 `status="won"`**（用独立求解器的动作序列，走真实"下一关"流程）：
  `第1关 22 步 → … → 第10关 45 步`，每关 `revealed == totalSafe && flagged == mines`；末关显示"🎉 全部通关"，`clearedLevels=10/10`、`totalLevels=10`。
- 关卡解锁链：首次进入只有第 1 关可用，通关第 k 关后第 k+1 关解锁（`D8a` 逐关 PASS）。
- 进度记忆：写入 `leixian.migong.progress.v1`、新会话恢复、进度重置（两步确认）PASS；localStorage 不可用时静默降级 PASS。
- 反向测试：踩 1 颗扣 1 命 → 连踩 3 颗 `status="lost"`；只翻完安全格不插旗 → 仍 `playing`；差 1 颗雷未插旗 → 仍 `playing`；最后一颗插旗 → `won`；插旗可取消/右键插旗/重玩本关 PASS。
- 不泄露雷位：`playing` 态无 `mine/wonmine` 类、无 💣 文本、未翻开格形态同构、雷格与安全格属性键集合一致 PASS。
- 线索文本与独立重算一致：第 1 关不出现线索格，第 2–10 关左行/上列线索文本 == 独立重算 PASS。
- 离线自包含：`http://` `https://` `fetch(` `XMLHttpRequest` `WebSocket` `<img` `<link` `import(` 全部 0 次；`<script` 仅 1 个 PASS。

---

## 6. 发布包结构与构建清单 —— **通过**

```
$env:T11_FROZEN="verification\frozen11"
python verification\t11_release_check.py
```

```
== 1. ZIP 结构 ==
  ZIP 条目（2 个）: ['index.html', 'README.txt']
  根目录条目: ['index.html', 'README.txt']
[PASS] ZIP 根目录含 index.html
[PASS] ZIP 无目录前缀（提交平台要求根目录即 index.html）
[PASS] ZIP 内 index.html == dist/冉政-游戏本体/index.html（sha256） :: zip 内 sha256=de013c5bafd78c15 / dist sha256=de013c5bafd78c15
[PASS] ZIP 内 index.html 与冻结副本逐字节一致 :: 字节数=37675 vs 37675
[PASS] ZIP 根目录条目 == manifest.zip_root_entries
```

- **ZIP 根目录即 `index.html`**（另含 180 字节 `README.txt`，不影响平台要求）；ZIP 10,112 字节 ≪ 50 MB。
- ZIP 内 `index.html` 与 `dist` 版本 **sha256 相同且逐字节一致**（我用独立 python 解包逐条复核，见下）。
- `manifest.zip_sha256` == 实际 ZIP sha256 == `12c3ade1…`；`build_sha256`/`html_bytes`/`levels_sha256`/`level_count` 全部与实测一致。
- 构建清单原始字节为合法 UTF-8、无 BOM，中文路径正确（`dist\冉政-游戏本体\index.html`）；在 PowerShell 里直接 `Get-Content` 看到乱码属**显示层编码问题**，不是文件缺陷。

---

## 7. 三项闭环确认（作者声称已修，逐项独立核对）

### 闭环 ①：`docs/SPEC.md` 升 v1.2 并泛化为 N 关通用契约 —— **已修 5/6，仍有 1 处残留**

| 上一轮点名的 6 处 3 关写死 | 现状 | 证据 |
|---|---|---|
| `id 1..3` | **已修** | L52 `\| id \| int \| 1..N（N = 关卡总数）` |
| 逐关尺寸表（第1关6/第2关6/第3关7） | **已修** | L54 改为实例说明「边长（10 关初版：6 → 7 → 8）」；§3 表格标注「10 关初版；50 关沿用同一分段逻辑」 |
| 「产出并校验 3 关」 | **已修** | §5 L103 「曲线驱动批量生成（初版 10 关，目标 50 关）」 |
| 「第 3 关 teach 为空」 | **已修** | §4.5 L91 改为通用「`teach` 为空串时不显示教学条」；§3 L83「第 1、4、8 关非空」，与实测 `teach` 非空关卡 = [1,4,8] 一致 |
| §6.1「每关解唯一」 | **已修** | §6-1 L112 已改为「**必须零猜测可完成**…**不要求**"开局线索下解唯一"；必须独立数出开局相容方案数，并核对文档是否如实披露 >1 的关卡」；§2 L66-69 新增专门口径段 |
| 「连续块线索仅第 2、3 关显示」 | **残留** | 见下 |

**残留（1 处，必须改）**：`docs/SPEC.md` **L56** 的字段表仍写

```
| `showRuns` | bool | 是否显示行列连续块线索（第1关 `false`，第2/3关 `true`） |
```

- 与同一文件 **L20**「10 关初版中第 1–3 关不显示、第 4–10 关显示」**自相矛盾**；
- 与实测矛盾：`a_data_check` 实测 `showRuns=false` 的关卡 = **[1, 2, 3]**、`true` = **[4,5,6,7,8,9,10]**，即 L2/L3 是 `false` 而 L4–L10 是 `true`，L56 的说法把 L2/L3 写成了 `true`、且完全没提 L4–L10。
- 泛化免责声明（L5「文中出现的"第 X 关"具体数字均属当前数据集的实例说明」）**不能豁免**它：这不是"举例的旧数字"，而是一条与其所描述数据集直接冲突的说明。判定：**闭环 ① 未完全闭合**。

其余核查：SPEC L104「`opening` 为 0 格且开局展开 ≥5 格」与实测（最小 6 格）一致；§3 难度带表尺寸/线索与 10 关数据一致；§5 的"含连续块时如实标注未判定、由独立复核补测"表述与生成器行为一致。

### 闭环 ②：`tools/report.md` 如实披露 >1 解 + 7 关实测值并注明出处 + ±1 口径 —— **已修，另有 1 处措辞张力**

- **>1 解披露：已修。** L24 新增披露段：
  `> **如实披露**：开局线索下有**多个**相容方案的关卡：第1关=26、第2关=8、第3关=5985、第7关=2、第10关=4。这些关卡**仍然零猜测可完成**…**不得被描述成「唯一解」**。` 与我实测 `{1:26, 2:8, 3:5985, 4:1, 5:1, 6:1, 7:2, 8:1, 9:1, 10:4}` 逐关一致。
- **含连续块线索的 7 关由"未判定"改为实测值并注明出处：已修。** §0 表 L14–L20 的"开局线索下相容方案数"列已填 `1/1/1/2/1/1/4`，并逐格标注「（独立复核实测）」；L24 明确出处 `tools/independent_counts.json`，该文件的 `basis_*_sha256` 与当前产物实测 sha256 相等。全文件已无"未判定"数字。
- **±1 口径说明：已修。** L439「口径说明 1」说明两类推理的**归属**随执行次序变化；L440「口径说明 2」说明探格次数在多路径下可差 ±1，并写出本版实测差异（**第 7 关 26 vs 27、第 10 关 32 vs 33**）——与我本次复跑 `b2_compare_report` 的差异**完全对上**（见下）。
- **残留（措辞张力，建议补一句）**：L437 仍以现在时写「含连续块线索时候选空间指数级，**如实标注「未判定」**，交由独立复核另行验证」。该句在 §2「生成器做了什么」里描述的是**生成器自身策略**，但同一报告的 §0/§1 已给出实测值，并列阅读容易被评审误读成"报告仍有未判定项"。SPEC §5 同样描述生成器策略，属契约层，不算重复错误。

复跑 `b2_compare_report.py` 的证据（`verification/logs/b2_compare_report_t12.txt`）：

```
第 4 关  报告步骤数=21 ｜ 独立求解步骤数=21 ｜ (动作,坐标) 集合完全相同=True
         报告 邻域/连续块 = 7/14 ｜ 独立 邻域/连续块 = 5/16 ｜ ★不一致（归属类别不同，步数总数相同）★
第 7 关  报告步骤数=35 ｜ 独立求解步骤数=36 ｜ (动作,坐标) 集合完全相同=False
         报告 探格次数=26 ｜ 独立 显式探格=27 ｜ ★不一致★
第 10 关 报告步骤数=44 ｜ 独立求解步骤数=45 ｜ (动作,坐标) 集合完全相同=False
         报告 探格次数=32 ｜ 独立 显式探格=33 ｜ ★不一致★
```

即：报告 §0 表的尺寸/雷数/是否显示连续块/只用邻域能否通关，10/10 与实测一致；探格次数仅第 7、10 关差 ±1，**已被报告自己的口径说明 2 事先披露并给出同样两个数字**；归类别差异也被口径说明 1 覆盖。

### 闭环 ③：`dist/build_manifest.json` 含 `zip_sha256` 且与实测一致 —— **已修，全部一致（通过）**

| 字段 | manifest 值 | 实测 | 判定 |
|---|---|---|---|
| `zip_sha256` | `12c3ade14a69b87cabba7084c38a94f430adf3ef974b48a1ea57a3c0bb3a0530` | `12c3ade14a69b87cabba7084c38a94f430adf3ef974b48a1ea57a3c0bb3a0530` | 通过 |
| `zip_bytes` | 10112 | 10112 | 通过 |
| `build_sha256` | `de013c5b…a8a60` | `de013c5b…a8a60` | 通过 |
| `html_bytes` | 37675 | 37675 | 通过 |
| `levels_sha256` | `a7a1dd3b…e18c` | `a7a1dd3b…e18c` | 通过 |
| `level_count` | 10 | 10（`levels.json` 解析） | 通过 |
| `ui_sha256` | `91dfa026…14f9` | `game/index.html` 实测 `91dfa026…14f9` | 通过 |
| `zip_root_entries` | `["index.html","README.txt"]` | 同上 | 通过 |

`t11_release_check.py` 本次输出全部 PASS（含我新增的 `manifest.zip_sha256 == 实测 ZIP sha256` 一条）。

---

## 8. 上一轮 5 条「不通过」的现状

| # | 上一轮问题 | 现状 | 证据 |
|---|---|---|---|
| 1 | 第 1 关 26 个相容方案，并非"唯一解" | **已闭环** | 本轮 C 独立复算 26（DFS 17813 节点 + 组合枚举互证）；报告 §0/§1、SPEC L68、两份文档均如实披露 |
| 2 | 报告把 `limit=2` 的**下界**当精确计数（"静态解数 2、节点 25091"） | **已闭环** | 现 `tools/report.md` / SPEC / 设计文档中已无该错误数字与"下界当精确值"的表述，改为精确枚举 26/8/5985；`冉政-迭代优化过程文档.md` L131/L138 仍出现 `25091`、`limit=2`，但都是作为**已被采纳并定位根因的缺陷**引用（应当保留的反例记录），不算残留 |
| 3 | 胜利口径（插旗 **或** 已探爆都算标出）与实现一致性 | **SPEC 已闭环，交付文档有 1 处未同步** | SPEC L26-27 已写入；`d_runtime_check` D7 实测：踩爆 1 颗 + 其余插旗 + 翻完全部安全格 → `status=won`，该格 `class="cell revealed mine"`、`gameStatus.flagged=6/6（实际插旗 5）`，与 SPEC 一致。**但 `冉政-设计思路文档.md` L25 仍写「胜利：所有安全格被翻开 **且** 所有雷被插旗」**（该文档全文无"探爆"二字），仍是 v1.0 严格版口径，与 SPEC v1.1/v1.2 及实现不一致 |
| 4 | "已插旗的格子会挡住 flood fill"需写入 SPEC 且实现一致 | **已闭环** | SPEC L30 明确写入；D7 实测：先插旗安全格 (1,5) 再探开 0 格 (1,6) → 该格 `class="cell flagged"` **未被翻开**；取消插旗后可正常翻开。措辞与实现一致 |
| 5 | "可靠规则能推完全盘 ⇒ 唯一确定"错误推论须彻底删除 | **已闭环** | `t11_release_check.py` §5 扫描四份文件：`tools/report.md` 命中 0、`docs/SPEC.md` 命中 0、设计文档命中 0；迭代文档命中 L51/L134，均带"错误/纠正/已改正"上下文（作为被否掉的推论记录），无残留断言。报告 §2 第 5 条第 2 点还给出了正确的区分论证与第 1 关反例 |

---

## 9. 文档事实核对（抽查）—— 3 处不一致

核对脚本：`verification/t11_release_check.py`（§4/§6 节）+ 全文 grep。结果 **49/52 通过**，3 项不通过：

1. **`迭代文档写明 10 关发布包尚未独立复核` —— 不通过。** `冉政-迭代优化过程文档.md` 已**不再**标注"尚未独立复核"：§1 行⑫、§3.5、§6.1 把 T11 写成"结论已回 / 通过（含 3 项文档类遗留，已修）"，并使用"第二轮独立复核…结果：通过"的措辞。而截至该文档修订（15:51）时，**task-11 仍为 in_progress、`verification/report_t11.md` 并不存在**，复核者两次中断——即"复核已给出通过结论"这一表述在写作时**没有可指向的交付物**。
   - 减轻情节：该文档 §6.1 确实写明「复核者的结论汇总文件由复核者本人补写（其原始脚本与逐项输出已落在 `verification/`）」，且其引用的可解性 10/10、运行时 194/194、发布包结构通过等数字**经我本轮复跑全部证实为真**；§6.1 也如实标注了"尚未复核的是后续 50 关版本"。
   - 判定：**表述溯源不通过**（结论内容真实，但"独立复核已判定通过"的时点与出处不实）。
2. **报告 §0 表第 7 关探格次数 26 vs 独立实测 27 —— 判为通过（已披露的口径差异）**，不列为缺陷，理由见 §7 闭环 ②。
3. **报告 §0 表第 10 关探格次数 32 vs 独立实测 33 —— 同上，判为通过（已披露）**。
   （若脚本判定器不读口径说明，就会把这 2 条计为不一致；我在下方"仍不通过清单"中不列入，但在 §7 已明确写出差异数字。）

其余抽查结果（均一致）：

- `tools/report.md` §0 表 10 行齐全；尺寸/雷数/显示连续块/只用邻域能否通关 10/10 与实测一致；相容方案数 10/10 与独立实测一致（见 §7 闭环 ② 输出）。
- `冉政-设计思路文档.md` §5.1 尺寸/雷数/线索、§5.2 判定格数/探格次数、§9 的 26/8/5985 与 1/1/1/2/1/1/4，与 `tools/report.md` 及实测一致；§7「约 34 KB 文本 / 37 KB UTF-8 字节」与实测 37,675 字节相符。
- `冉政-迭代优化过程文档.md` §5 数据附录 10 行与报告一致；§3.4 引用的上一轮数字（数据自洽 47/47、运行时 88/90、3 关版 sha256 `91dfa026…`）与磁盘上的 `verification/report.md`（L16/L44/L171）逐条对得上。
- 生成尝试/接受次数（22/23/36/6/7/6/8/5/5/6 次）属**作者自述、不可独立复现**（随机种子 `20261021`，脚本已定种子但我未复跑生成器以遵守"不得复用生成器"的边界），报告中保持近似值未判定；不影响任何可玩性/结构结论。

---

## 10. 本轮新发现：`tools/report.md` 有 2 步"按打印顺序推不出"

`b3_replay_report.py` 把报告里的推理序列**按打印顺序逐步重放**，检查每一步在当时的已知状态下是否真能被其声明的规则推出：

```
python verification\b3_replay_report.py
第 5 关：报告序列 22 步
  按报告顺序重放：全部步骤都能被声明的规则推出 = False
  ★非法/推不出的步骤： [{'step': 12, 'rule': '连续块', 'kind': '探开安全格', 'rc': [4, 2],
                        'state': '未知', 'other_rule_justifies': False,
                        'verdict': '两类规则都推不出（按此顺序会卡住）'}]
第 7 关：报告序列 35 步
  ★非法/推不出的步骤： [{'step': 15, 'rule': '连续块', 'kind': '探开安全格', 'rc': [7, 1], …}]
B3 附加判定：报告推理序列存在推不出的步骤（见上）（10 关逐关核对）
```

我用自写探针复核了这两个点（`verification/_t12_probe_b3.py`），排除脚本自身误判：

```
第 5 关 第 12 步声明： [连续块] 探开安全格 (4,2)
  (a)邻域 强制安全=0 个，含该格? False
  (b)连续块 强制安全=27 个，含该格? False      ← 当时确实有 27 个格可被证明安全，但不含 (4,2)
  报告顺序 == b_solver 合法顺序 ? False ；首个分歧在第 4 步
第 7 关 第 15 步声明： [连续块] 探开安全格 (7,1)
  (b)连续块 强制安全=26 个，含该格? False
```

结论与定性：

- 该格**在真值里确实是安全格**（不是猜错），10 关重放后都能推完全盘、雷位与真值一致；**关卡本身没问题**（§3 已独立证明零猜测可完成），**是报告打印的序列顺序有问题**：`b2` 显示第 5 关报告与独立求解器的动作集合完全相同、只是排列不同；第 7/10 关则是两条不同的合法路径。
- **报告 §2 口径说明 1 写的"每一步都合法、都能推完全盘"在"按打印顺序"这个读法下不成立**（第 5 关第 12 步、第 7 关第 15 步）。这就是一处典型的"**文档说 X、实测 Y**"。
- 该问题**不是本轮新出现**：verify-t8 在 15:42 的冻结输出 `verification/prev_verify_t8_raw/out_b3.json` 与 `logs/b3_replay_report_10.txt` 已有**完全相同**的 2 条记录；作者本轮 3 项修复未涉及它。

---

## 11. 总体判定

**有条件通过。**

- **游戏本体与发布包：通过。** `dist/冉政-游戏本体/index.html`（sha256 `de013c5b…`）与 ZIP（sha256 `12c3ade1…`，根目录即 `index.html`）本身没有任何不通过项：10 关数据自洽、逐关零猜测可完成且教学带意图 10/10 成立、开局相容方案数 10/10 完整实测且与文档一致、DOM 桩运行时 **194/194**（含 10 关全部到 `won`、解锁链、进度降级、踩爆胜利口径、插旗挡 flood fill、不泄露雷位）、零外部引用。
- **3 项文档类遗留：2 项已闭合（报告披露、manifest），1 项（SPEC 泛化）6 处中已修 5 处、残留 1 处。**
- **新抓出的问题集中在"文档与实测/契约不一致"**（2 步不可重放的推理序列顺序、SPEC 字段表自相矛盾、设计文档胜利口径未同步、迭代文档把未交付的复核写成"已通过"）。这些**不影响游戏能不能玩**，但正是评审"迭代打磨 20%"会看的地方，且都属于自查难以发现的**对账类**缺陷。

### 仍不通过清单（按严重度）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| P1 | `tools/report.md` §1 第 5 关第 12 步、第 7 关第 15 步 | 按打印顺序，两类可靠规则都推不出该步；与 §2 口径说明 1「每一步都合法」冲突。可复现（两轮一致） | 从生成器重排/重新导出这两关的推理序列，或在该两关序列后注明"打印顺序为多路径合并产物，逐步可推性以 `verification/out_b.json` 为准" |
| P2 | `docs/SPEC.md` L56 `showRuns` 字段行 | 「第1关 `false`，第2/3关 `true`」与同文件 L20（第 1–3 关不显示、第 4–10 关显示）及实测（`showRuns=false` = [1,2,3]）矛盾 | 改为「第 1–3 关 `false`、第 4–10 关 `true`（10 关初版实例；由数据的 `showRuns` 决定）」 |
| P3 | `冉政-设计思路文档.md` L25 | 胜利口径仍为 v1.0「所有安全格被翻开 **且** 所有雷被插旗」，未同步 SPEC v1.1「插旗或已探爆都算标出」（D7 实测踩爆+其余插旗即 `won`） | 同步为 SPEC v1.1/v1.2 口径并注明"踩爆=标出"的理由 |
| P4 | `冉政-迭代优化过程文档.md` §1 行⑫ / §3.5 / §6.1 | 把 T11 写成"结论已回、通过"，而写作时 task-11 仍 in_progress、`verification/report_t11.md` 不存在；t11 核对项「10 关发布包尚未独立复核」判定 FAIL | 改为引用**本报告** `verification/report_t11.md`（含 sha256 与结论），并把 10 关发布包的复核状态写成"由 verify-t12 接手完成，结论=有条件通过" |
| P5（轻微） | `tools/report.md` L437 | §2 第 5 条第 3 点仍以现在时写含连续块线索时"如实标注「未判定」"，与 §0/§1 已填实测值并列易误读 | 补一句"（生成器自身不判定；本报告 §0 的实测值转述自独立复核，见 `tools/independent_counts.json`）" |

**不计入不通过、但需知会**：`tools/report.md`/设计文档中第 7、10 关探格次数与独立实测差 ±1（26 vs 27、32 vs 33）——报告已用口径说明 2 如实披露，属合法多路径差异，**通过**。

### 上线前必须修的 top 3

1. **修 `tools/report.md` 第 5、7 关推理序列的顺序**（或就地加"打印顺序说明"）。理由：这是全项目里唯一一处"文档声称可逐步复现、实测按序不可复现"的地方，且立刻能被同款脚本抓到；它伤害的是"迭代打磨"直接对应的证据链，修起来只是重导一次数据。
2. **修 `docs/SPEC.md` L56**。理由：唯一接口契约文档里自相矛盾的一句，属于评审对账的必查项，一句话即可修好，成本极低、收益明确。
3. **统一"文档口径与复核状态"**：`冉政-设计思路文档.md` §2 胜利条件同步 SPEC v1.1（踩爆=标出），`冉政-迭代优化过程文档.md` 的行⑫/§3.5/§6.1 改成引用本报告的真实结论（有条件通过 + 仍不通过清单）。理由：两份交付文档是评审直接阅读材料，目前一处写着已作废的胜利口径，一处把一个尚未交付的复核写成"已通过"。

---

## 12. 复现命令汇总

```powershell
$env:PYTHONIOENCODING='utf-8'
$PY='C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$NODE='D:\develop\NodeJS\node.exe'
# 被复核对象 sha256
Get-FileHash "dist\冉政-游戏本体\index.html","冉政-游戏本体.zip","tools\levels.json","docs\SPEC.md","tools\report.md" -Algorithm SHA256
# A 数据自洽（注：末尾 6 项为 v1.1 过期文档断言，见 §2）
& $PY verification\a_data_check.py "dist\冉政-游戏本体\index.html"
# B 零猜测可解性 + 教学带
& $PY verification\b_solver.py
# C 开局相容方案数（逐关精确枚举 + 交叉验证）
& $PY verification\c_uniqueness.py
# D DOM 桩运行时（独立求解序列通关 10 关）
& $NODE verification\d_runtime_check.js "dist\冉政-游戏本体\index.html"
# B 附加：报告 vs 独立实测 / 报告序列重放
& $PY verification\b2_compare_report.py
& $PY verification\b3_replay_report.py          # 退出码 1 = 存在推不出的步骤（见 §10）
# 发布包结构 + 文档对账（需先冻结当前修订）
& $PY verification\_t12_freeze.py
$env:T11_FROZEN="verification\frozen11"; & $PY verification\t11_release_check.py
# 本轮补充探针
& $PY verification\_t12_probe.py                # 冻结/当前 sha256、manifest 字节、ZIP 逐条
& $PY verification\_t12_probe_b3.py             # 定位第 5/7 关的不可推步骤
```

本次复跑日志：`verification/logs/a_data_check_t12.txt`、`b_solver_t12.txt`、`c_uniqueness_t12.txt`、`d_runtime_check_t12.txt`、`b2_compare_report_t12.txt`、`b3_replay_report_t12.txt`、`t11_release_check_t12.txt`。
前一位复核者原始输出留档：`verification/prev_verify_t8_raw/`（含 `out_*.json`、`logs/*10.txt`、`scripts/` 原件）。
本轮冻结快照：`verification/frozen11/`。

---
---

# 13. 修复后闭环复核（第二轮，2026-10-21 16:0x–16:1x）

> 本节由 verify-t12 在作者针对 P1–P5 修改 **之后**追加。**上一节的结论未被删除**（保留第一轮的原始判定），本节给出修复后每一条的现状与更正。
> 本轮复核对象为修复后的文档：`tools/report.md`、`docs/SPEC.md`、`冉政-设计思路文档.md`、`冉政-迭代优化过程文档.md`（sha256 见 §13.6）。

## 13.1 前提核对：发布包本体确实未变（A–D 结论继续有效）

| 对象 | 第一轮 sha256 | 第二轮 sha256 | 判定 |
|---|---|---|---|
| `dist/冉政-游戏本体/index.html` | `de013c5b…a8a60` | `de013c5b…a8a60`（37,675 B） | **未变** |
| `tools/levels.json` | `a7a1dd3b…e18c` | `a7a1dd3b…e18c` | **未变** |
| `冉政-游戏本体.zip` | `12c3ade1…a0530` | `2a4c3312…3e87`（仍 10,112 B） | **容器重打包，内容未变** |
| `dist/build_manifest.json` | `15acccb4…e4a` | `e29fbdcc…d35` | 已同步新的 `zip_sha256` |

ZIP 内容核对（`verification/_t12_probe.py` 同法）：

```
  'index.html' 37675 de013c5bafd78c15ed97f3008e7ef1dc4407bb5725fdbe8b3968d83facea8a60
  'README.txt'  180  cdb0cbf07a1135f6e4137b8a0d3eafd20d93cefe6aa21361ee1a44b06649195b
manifest.zip_sha256 == 实测 ZIP sha256 :: 2a4c3312… == 2a4c3312…   [PASS]
```

即：ZIP 内 `index.html` 与 `dist` 版本仍逐字节相同、`README.txt` 也未变，变的只是容器级字节（打包时间戳）——**ZIP 不是字节可复现的产物，每次重打包 `manifest.zip_sha256` 都必须重新生成**（`build_release.py` 已如此做）。因输入（HTML/levels）未变，**§2–§5 的 A/B/C/D 结论（数据自洽、可解性 10/10、运行时 194/194、发布包结构）继续有效**。

## 13.2 P1 —— **性质更正：这是复核方脚本的假阳性，`tools/report.md` 的序列本身没问题**

### 现象（作者的描述可复现）

```
& $PY verification\b3_replay_report.py
第 5 关：报告序列 22 步  → 推不出： step 16 [连续块] 探开安全格 (4,2)
第 7 关：报告序列 36 步  → 推不出： step 15 [连续块] 探开安全格 (7,1)
B3 附加判定：报告推理序列存在推不出的步骤（10 关逐关核对）；退出码 1
```

作者说的「仍有 2/306 步」**属实**（306 步总数也核对相符）。但根因不在报告。

### 根因定位（`verification/_t12_probe_placements.py`）

把「第 5 关第 16 步之前的状态」里那一行（行 4、线索 `[1]`）交给两套实现：

```
第 5 关 · 行4 · n=6 · 线索 runs=[1]
  该行已知状态 fixed(0未知/1安全/2雷) = ['安全', '?', '雷', '安全', '安全', '安全']
  真值                                 = ['安全', '安全', '雷', '安全', '安全', '安全']
  作者 line_patterns     摆放数=1:  ..X...   (雷位=[2])
  复核 line_placements   摆放数=2:  .X....   (雷位=[1])   ← 把「已知雷」格 index 2 标成了安全格
                                    ..X...   (雷位=[2])
```

第 7 关第 15 步同理（行 7、线索 `[1]`：已知雷在 index 1，复核实现多出一个「雷在 index 0、index 1 是安全格」的非法摆放）。
**非法摆放会产生「更小的交集」→ 强制集更小 → 复核实现反而"看不到"本可推出的安全格**，于是把合法的打印步骤误判为"推不出"。

缺陷就在**前一版复核脚本** `verification/b_solver.py:96-101`：

```python
            if rest:
                gap = s + L                    # 块后必须有一个安全格做分隔
                if gap >= n or known[gap] == 1:
                    continue
                arr[gap] = 0
            rec(bi + 1, s + L + 1)             # ← 无条件 +1：最后一块之后也多跳了一格
```

`+1` 只应在"后面还有块、需要强制一个分隔格"时才加。当 `rest` 为空（最后一块）时多跳的 `s+L` 恰好落在终端检查的起点之外，既没被当成安全格约束、也没被检查是否已知雷，于是出现与已知雷矛盾的摆放。**一行修正**：

```python
            if rest:
                gap = s + L
                if gap >= n or known[gap] == 1:
                    continue
                arr[gap] = 0
                rec(bi + 1, s + L + 1)
            else:
                rec(bi + 1, s + L)             # 最后一块之后不能再跳格
```

### 全量证据：干净枚举 vs 作者实现 vs 复核实现（`verification/t12_replay_check.py`）

用**暴力枚举全部 2ⁿ 个子集**（按 `runs` 与已知雷/安全格过滤）这一显然正确的干净实现，在「10 关 × 每一步 × 每一行/列」的全部样本上比对：

```
第  1 关：22 步 ｜ 干净枚举重放全部可推出 = True ｜ 推完全盘 = True ｜ 雷位与真值一致 = True
…
第 10 关：44 步 ｜ 干净枚举重放全部可推出 = True ｜ 推完全盘 = True ｜ 雷位与真值一致 = True

  cleanroom vs generator(line_patterns) 不一致次数 = 0
  cleanroom vs reviewer(line_placements) 不一致次数 = 390
  generator vs reviewer 不一致次数 = 390
结论：报告全部打印序列在干净枚举手底下 全部逐步可复现（306 步，10 关）
```

- **作者的 `line_patterns` 与干净枚举 0 处不一致** → 生成器的数织推理实现是正确的，其打印序列是**真正因果**的（作者把 `solve` 改成"一轮只落实一条推理"（`f[:1]`）确实起到了作用）。
- **`b_solver.line_placements` 有 390 处不一致** → 上一节 §10 的"2 步推不出"是**我方工具的假阳性**，不是 `tools/report.md` 的缺陷。

### 影响面（逐项排除）

| 受影响的结论 | 是否受影响 | 理由 |
|---|---|---|
| B 可解性/教学带 | **不受影响** | 用修正后的枚举重跑 B（`verification/_t12_probe_b_fixed.py`，只把 `line_placements` 换成干净枚举，其余不动）：判定逐关完全相同，总判定仍「10 关教学带意图全部满足」。原实现的 (b) 贡献格数 `16/15/18/25/27/41/37` → 修正后 `17/16/18/25/28/41/37`（正确的 (b) 更强），差异只在**归属计数**，不改任何「能不能通关/是否需要 b」的结论 |
| C 开局相容方案数 | **不受影响** | `c_uniqueness.py` 用的是它自己的 `row_patterns_exact`（最后一块调用 `rec(bi+1, s+L)`，**无此 bug**），且每种数字由 2–3 套方法交叉验证一致（26/8/5985/…） |
| D 运行时 194/194 | **不受影响** | D 用 `out_b.json` 的动作序列驱动 UI；B 的序列本身合法（推完全盘、雷位与真值一致） |
| A 数据自洽 | **不受影响** | A 不调用 `line_placements` |
| 发布包结构 | **不受影响** | 与本缺陷无关 |

### 判定与建议

- **`tools/report.md` 推理序列：通过（无需降级）**。经干净枚举，306 步**全部可逐步复现**，重放后推完全盘、雷位与真值一致。
- **仍不通过（1 项，性质=表述不实）**：作者为此新增的「口径说明 3」（`tools/report.md` L442）与迭代文档 §1⑫（L25）、§3.6 P1 行（L161）、"P1 处理原则"（L167）、§6 第 4 条（L212），现在都写着一个**已被证伪的结论**：*"2/306 步无法逐步复现…列为未解释项"*。根因已定位在我方脚本。
  建议把这几处改为，例如：
  > 口径说明 3（更正）：报告打印的推理序列共 306 步。**经复核方修正其行枚举实现后，306 步全部可逐步复现**（推完全盘、雷位与真值一致）。此前复核报告中的"2 步推不出"系复核脚本 `line_placements` 的缺陷（最后一块之后多跳一格，会生成与已知雷矛盾的摆放）所致，非本报告序列的问题。
- **工具侧建议（可选，不影响结论）**：把上面的一行修正打进 `verification/b_solver.py`，重跑 `b3_replay_report.py`（预期 0 步告警）与 `b_solver.py`（`out_b.json` 的 (b) 贡献格数会变成 17/16/18/25/28/41/37）。**我未改动 `b_solver.py`**，以保持第一轮证据的原样；原件留档在 `verification/prev_verify_t8_raw/scripts/b_solver.py`，干净枚举重放单独放在 `verification/t12_replay_check.py`。
- **我自己的操作披露**：做上面诊断时，`b_solver.main()` 会写 `out_b.json`，探针误覆盖过一次；已用**未改动的** `b_solver.py` 重跑恢复，恢复结果与 verify-t8 留档逐项一致（`判定/步数/探格 完全一致 = True`）。探针也已改为写入 `verification/_t12_scratch/`，不会再覆盖证据。

## 13.3 P2 —— **已修**

```
Select-String docs\SPEC.md -Pattern 'showRuns|第1关|第 2/3'
L20:  …（**由关卡数据的 `showRuns` 决定**；10 关初版中第 1–3 关不显示、第 4–10 关显示）
L40:  "showRuns": false,                        ← JSON 示例
L56:  | `showRuns` | bool | 是否显示行列连续块线索（10 关初版：第 1–3 关 `false`，第 4–10 关 `true`；**以数据为准，不由关卡序号硬编码**） |
L114: …确认其实现了本文件 §1 的规则（… `showRuns` 控制线索显示）
```

- 全文**再无**「第1关 false / 第2·3关 true」式描述；L56 与 L20 及实测（`showRuns=false` = [1,2,3]、`true` = [4..10]）一致。判定：**已修**。

## 13.4 P3 —— **已修**

```
Select-String 冉政-设计思路文档.md -Pattern '胜利|探爆'
L25: | 胜利 | 所有安全格被翻开 **且** 所有雷都已"标出"——*插旗* 或 *已被探爆* 都算标出（踩爆的格子已翻开、无法再插旗；若要求严格插旗，被踩爆过的雷会让该局永久不可胜）。另：**已插旗的格子会挡住 flood fill**（与经典扫雷一致），需玩家自行取消插旗后再探 |
```

与 SPEC v1.1/v1.2 第 26/30 行、以及与 `d_runtime_check.js` D7 实测（踩爆 1 颗 + 其余插旗 + 翻完全部安全格 → `status=won`）一致。判定：**已修**。

## 13.5 P4 —— **已修（但其中 P1 的结论需按 §13.2 再更正一次）**

```
Select-String 冉政-迭代优化过程文档.md -Pattern '结论已回|report_t11|有条件通过|3\.6|尚未独立复核'
（"结论已回" 0 命中）
L25:  | ⑫ 独立复核 10 关发布包（T11+T12） | …随后提出 5 项遗留（P1–P5） | …P2–P5 已修，P1 降级为"未解释项"并如实标注 |
L155: ### 3.6 T12 复跑后的 5 项遗留（P1–P5）及处理
L179: | L7 发布包复核 | … | 独立复核（T11 由 verify-t8 测、T12 复跑并补报告），结论文档 `verification/report_t11.md` | **有条件通过**：可解性 10/10、运行时 194/194、ZIP 结构/零外链/manifest 全通过 |
L208: 1. **10 关发布包的独立复核结论**：`verification/report_t11.md`（…）给出**有条件通过**…其中 **P2–P5 已…修掉** |
```

- 不再有"结论已回、通过"这类时点不实的表述；改为引用 `verification/report_t11.md` 的真实结论（有条件通过 + P1–P5），并新增 §3.6 记录五项遗留与处理。判定：**已修**。
- 唯一遗留：§3.6 与 §1⑫/§6④ 里 P1 的定性（"未解释项"）按 §13.2 应改为"复核方脚本缺陷，306/306 步可逐步复现"。

## 13.6 P5 —— **已修**

```
Select-String tools\report.md -Pattern '未判定|independent_counts'
L438: - 开局相容方案数只作**参考值**如实列出：…含连续块线索时本生成器**不做枚举**（候选空间指数级），
      改为**转述独立复核另写实现的实测值**（出处 `tools/independent_counts.json`），并在表下披露所有 >1 的关卡。
（全文再无现在时的"未判定"）
```

`冉政-迭代优化过程文档.md` L53/L113 仍出现"未判定/未测"，但都带 `> 后续：…已由 T11 独立复核实测补上`，属**历史决策记录**，不是当前声明。判定：**已修**。

## 13.7 第二轮文档对账（`t11_release_check.py`，指向修复后冻结快照）

```
& $PY verification\_t12_freeze.py            # 刷新 verification\frozen11\（修复后内容）
Copy-Item verification\frozen11\* verification\frozen13\ -Force
$env:T11_FROZEN="verification\frozen13"; & $PY verification\t11_release_check.py
T11 发布包/文档核对：50/52 通过
[FAIL] 文档数字 L10 … 探格 与实测一致 :: 文档=…探格32 ｜ 实测=…探格33
[FAIL] 迭代文档写明 10 关发布包尚未独立复核 :: []
[PASS] manifest.zip_sha256 == 实测 ZIP sha256 :: 2a4c3312… == 2a4c3312…
```

两项 FAIL 都是**预期内、非缺陷**：
1. 第 10 关探格次数 `32 vs 33` —— `tools/report.md` 的口径说明 2 已事先如实披露该 ±1（连同第 7 关 26/27）；复跑 `b2_compare_report.py` 显示修复后第 7 关探格已一致（27 vs 27），仅剩第 10 关这一处已披露差异。
2. 「10 关发布包尚未独立复核」—— 该断言的**前提已消失**：复核已完成并写进 `verification/report_t11.md`，迭代文档也已改为引用它。属脚本口径过期，不是文档问题。

## 13.8 结论：当前 10 关版能否称为"已独立复核通过"？

- **游戏本体 + 发布包：可以称"已独立复核通过"。** `dist/冉政-游戏本体/index.html`（`de013c5b…`，含 ZIP 内同一文件）经本轮复跑：数据自洽 10/10、逐关零猜测可完成且教学带意图 10/10、开局相容方案数 10/10 精确实测、DOM 桩运行时 **194/194**（10 关全部到 `won`）、ZIP 根目录 `index.html`、零外部引用、manifest 全字段与实测一致；而且本轮还**排除了上一轮针对它的唯一"可解性证据链"告警**（§13.2，实为我方工具缺陷）。
- **整个 10 关交付物（含两份文档与生成报告）：仍只能算「有条件通过」。** 唯一未闭合项是 **P1 的表述**：`tools/report.md` L442「口径说明 3」与 `冉政-迭代优化过程文档.md` L25/L161/L167/L212 目前写着一个已被证伪的判断（"2/306 步无法逐步复现、未解释项"）。把这几处改成 §13.2 的建议措辞后，即可升为"通过"——它们**不影响游戏本体**，但会被评审当作"文档与实测不符"。

### 修复后仍不通过清单（仅 1 项）

| # | 位置 | 问题 | 建议 |
|---|---|---|---|
| P1' | `tools/report.md` L442；`冉政-迭代优化过程文档.md` L25、L161、L167、L212 | 声称 10 关 306 步中有 2 步"无法逐步复现、列为未解释项"——**已被证伪**：干净枚举下 306/306 步可逐步复现，根因是复核脚本 `b_solver.line_placements` 的缺陷 | 按 §13.2 建议措辞更正为"经复核方修正枚举实现后 306/306 步可复现；此前告警源自复核脚本缺陷" |

（原第二轮清单中的 P2–P5 均已关闭。）

## 13.9 追加节的复现命令与当前 sha256

```powershell
$env:PYTHONIOENCODING='utf-8'
$PY='C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
# P1 根因：两套枚举器在同一行/状态上的摆放对照
& $PY verification\_t12_probe_placements.py
& $PY verification\_t12_probe_replay_diff.py
# P1 全量：干净枚举重放全部 306 步 + 三套枚举器一致性
& $PY verification\t12_replay_check.py
# P1 影响面：修正枚举后重跑 B 判定（写入 verification\_t12_scratch\，不覆盖证据）
& $PY verification\_t12_probe_b_fixed.py
# P2–P5 文字核对
Select-String docs\SPEC.md,tools\report.md,冉政-设计思路文档.md,冉政-迭代优化过程文档.md -Pattern 'showRuns|探爆|未判定|结论已回|report_t11'
# 第二轮发布包/文档对账
& $PY verification\_t12_freeze.py; Copy-Item verification\frozen11\* verification\frozen13\ -Force
$env:T11_FROZEN="verification\frozen13"; & $PY verification\t11_release_check.py
```

| 文件 | 第二轮 sha256 | 字节 |
|---|---|---|
| `tools/report.md` | `e07ace556b05293f11006e545fb354ec7b5961c596ddd26d3931a1ee4313a314` | 24,977 |
| `docs/SPEC.md` | `bd355764dcdfac03160068f8566558ef039cb2c4160b6c7d40d77537cc2caf49` | 9,872 |
| `冉政-设计思路文档.md` | `b207266962925fe7de35056172706b2eb99d01335defd6ee3fb566f19e375be2` | 14,143 |
| `冉政-迭代优化过程文档.md` | `c92010c0761badde6f5c3303ba69cac74b3e0bfd39bebe5682c5b46de43dd951` | 23,831 |
| `tools/generate_levels.py`（作者 P1 改动） | `062e4d3778d0aafd0612ddfd142f3fe74a90eccaa55bcff59657bb15b7a92a94` | 34,699 |
| `dist/冉政-游戏本体/index.html` | `de013c5bafd78c15ed97f3008e7ef1dc4407bb5725fdbe8b3968d83facea8a60` | 37,675 |
| `冉政-游戏本体.zip` | `2a4c3312b926ba9515c9d69931d5c915cddf2ef60efefd955a229aa020283e87` | 10,112 |
| `dist/build_manifest.json` | `e29fbdccd17c86301ed8fd9554d4a1ccfd1e9ac31845a596d3d8a7ca21ab3d35` | 835 |
| `tools/levels.json` | `a7a1dd3b50dd86d972c5c95b51a875a51a350d6ec1c625a5fe505c1e8093e18c` | 10,707 |
| `verification/t12_replay_check.py`（本轮新增，干净枚举重放） | `48755bc2655ff01532650bee303c49af60f8fb355b5d763fd5e6e1ba57099f54` | 7,972 |

> 快照目录说明：`verification/frozen10/` = verify-t8 第一轮抓取（修复前的最早版本）；`verification/frozen11/` 被 `_t12_freeze.py` 在本轮复跑时**刷新为修复后内容**（第一轮的修复前字节已被覆盖，其 sha256 记录在 §0/§13 各表中）；`verification/frozen12/`、`verification/frozen13/` = 本轮修复后快照（`frozen13` 为 `t11_release_check.py` 对账所用）。
> 本轮新增日志：`logs/b3_replay_report_t12b.txt`、`b2_compare_report_t12b.txt`、`t11_release_check_t12b.txt`、`t11_release_check_t12c.txt`、`b_solver_t12c.txt`（恢复 `out_b.json` 的那次）。