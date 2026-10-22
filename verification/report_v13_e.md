# v13-e 复核报告：星座图鉴关卡号映射 bug 修复验证

**结论：通过。** 独立复算（不调用也不信任 `tools/build_sky.py`）结构 7/7、运行时 31/31 全部通过，并有负向对照证明断言非空洞。
数据基准：`dist/星织-游戏本体/index.html` 内嵌 `SKY`/`LEVELS`、`tools/sky.json`、`星织-游戏本体.zip` 三方一致（注：`D:\AI-Native casual game` 是指向 `D:\Asterweave` 的 junction，两者为同一目录）。

## 1. 结构断言 — `verification/v13_e_struct.py`（7/7 PASS）
- S1/S2 条数：`len(SKY)=50` `len(LEVELS)=50`
- S3 `SKY[].level == LEVELS[theme.id].id`：`mismatch=[]`；反查表 50 条、`重复 theme.id=[]`
- S4/S5 无孤儿 id、无 `null` level；level 唯一，`min=1 max=50 missing=[]`（恰覆盖 1..50）
- S6 dist 内嵌 `SKY` 与 `tools/sky.json` 完全相同（规范化 JSON 逐字节相等），tools 侧 level 同样无 mismatch
- S7 zip 内 `index.html` 与 dist 内 SHA256 一致：`b70363c501434395…`
- 三个旧值均已修正：`ophiuchus=29`(旧21)、`carina=26`(旧22)、`hydra=30`(旧23)；`capricornus=21`、`grus=22`
- 第 26..31 关 = `carina, aquarius, pisces, ophiuchus, hydra, aries`

## 2. 运行时断言 — `verification/v13_e_dom.js`（自写 DOM stub，无 npm，31/31 PASS）
做法：预置应用自身的 localStorage 进度 `leixian.migong.progress.v1`（`cleared` 键 = 关卡下标，app 约定 `isCleared(level-1)`）→ 在 vm 里执行发布包真实内联脚本 → 点 `#skyBtn` → 读 `#skyCount` 文本、天球图节点、详情卡 HTML。
- R1 `#skyCount` 文本 == 实际通关数（`dataset.gameState.clearedLevels`）== `SKY.filter(level∈cleared)` 条数，六态全等：
  `{}→0`、`{1}→1`、`{1,21}→2`、`前21关→21`、`前49关→49`、`全部50关→50`
- R1 天球图亮起节点集合恰好 == 已通关关卡对应星座，六态全等（不多亮别的关）：
  如 `cleared={1,21} → lit=["capricornus","crux"]`；`前49关 → lit 49 个，缺 eridanus`
- R2 `cleared={1,21}` 点选未通关的蛇夫/船底/长蛇座：卡片 `gstar=false gline=false gnoise=false const-svg=false`，`len=255–259`；
  卡片不含任何别的星座中文名、不含其它关卡的 fact 文案；文案 = `未观测 … 第 29/26/30 关 · 通关后点亮`
  （旧值 21/22/23 已不再出现，卡片自带关卡号与真实关卡一致）
- R2b 已通关的第 21 关摩羯座渲染的是**自己**的 9 颗星坐标（坐标集与 `LEVELS[20].theme` 完全一致）与自己的 fact，不冒充蛇夫座
- R3 单独通关第 26/29/30 关：各只点亮 1 个节点 `carina` / `ophiuchus` / `hydra` 且 `skyCount=1`（奖励不重复）；
  三关一起 → 恰好亮 3 个、`skyCount=3`，对应星座详情含星图而其未通关邻居不含
- R4 负向对照：把内嵌 `SKY` 里 `ophiuchus.level` 改回 `21` → 立刻复现旧症状：
  `cleared={1,21}` 时 `skyCount=3` 而真实通关 `=2`；未通关蛇夫座卡片泄露 `gstar=true` 且渲染出摩羯座 fact
  （"名字=蛇夫座、星图/文案=摩羯座"）。说明 R1/R2 断言对旧 bug 有检出能力，不是空洞通过。

## 3. 复现命令
```
& 'C:\Users\JJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' 'D:\AI-Native casual game\verification\v13_e_struct.py'
& 'D:\develop\NodeJS\node.exe' 'D:\AI-Native casual game\verification\v13_e_dom.js'
```
（前者末行 `ALL_PASS`；后者末行 `SUMMARY pass=31 fail=0 note=1`，退出码 0）

## 4. 备注（不影响结论，未改任何代码）
- 顺带发现：`skyEls.btnNum/btnTotal` 从未定义，`refreshSkyBadge()` 实际是 no-op（有 `if` 守卫，不报错）；`#skyCount` 只在图鉴打开时由 `renderSky()` 刷新。与本次 level 映射 bug 无关。
- 上一轮 `verification/v13_d_dom.js` 的方法基本正确（真脚本 + 真点击，非硬编码），但其 `expectSky` 是用 `SKY` 自身算期望（须靠同文件第 508 行 `SKY↔LEVELS` 断言才不成循环），E3 靠重放通关而非直接构造进度，且没有第 26/29/30 关奖励断言，`freshContext()` 是死代码。本报告未复用它任何结论。
