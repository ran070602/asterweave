# 协作须知：继续扩关卡（交给"关卡扩展"会话）

> 本文件写给**另一个正在扩关卡的会话**。目的：让两边不互相踩文件，且扩完不会出现"关卡变了、文档没变、图鉴缺数据"。

## 1. 谁改什么（避免并发写坏）

| 文件 / 目录 | 谁负责 | 说明 |
|---|---|---|
| `tools/fit_constellation_levels.py` | **关卡扩展会话** | 星座定义（RAW）、PLAN（每关棋盘/探格目标）、拟合逻辑 |
| `tools/levels.json` | **关卡扩展会话**（由脚本写出） | 不要手改，永远由 `fit_constellation_levels.py` 生成 |
| `tools/build_sky.py`、`tools/sky.json` | 图鉴会话（当前 lead） | 新增星座时需要**在图鉴里补一行**，见 §3 |
| `game/index.html` | UI 会话 | 含 `LEVELS_INJECT` / `SKY_INJECT` 两个占位块，**不要手写关卡数据进去** |
| `dist/`、`index.html`（根）、`*.zip` | 由 `tools/build_release.py` 自动生成 | 不要手改 |
| 两份 `冉政-*.md`、`README.md`、`docs/SPEC.md` | 图鉴/文档会话 | 表格请用 `tools/sync_docs_tables.py` 自动同步，不要手改 |
| `verification/` | 独立复核者 | 其他人不要写 |

**不要同时改 `tools/fit_constellation_levels.py`**：如果两边都要动它，先在对话里说清楚谁改哪一段，或者一方改完 push、另一方 rebase。

## 2. 扩一关的标准流程

```bash
# 1) 在 fit_constellation_levels.py 里加星座（真实星位 + 视星等 + 连线）和 PLAN 条目
# 2) 生成（会自动跑求解器验收）
python tools/fit_constellation_levels.py

# 3) 自检：零猜测可解 / 孤立雷 / 空行空列 / 密度 / 图鉴覆盖
python tools/check_levels.py

# 4) 同步两份文档的关卡表（不要手改表格）
python tools/sync_docs_tables.py

# 5) 打包（会注入 levels.json + sky.json，并自动同步根目录 index.html 供 Pages 用）
python tools/build_release.py

# 6) 提交
git add tools/levels.json tools/fit_constellation_levels.py dist/ index.html 星织-游戏本体.zip
git commit -m "关卡：扩到 N 关（...）"
git push origin main     # Pages 1–2 分钟后自动更新
```

## 3. 新增星座后，图鉴会缺数据（重要）

图鉴（`✦ 图鉴`）的数据来自 `tools/sky.json`，由 `tools/build_sky.py` 里的 `RAW` 表生成。**每加一个星座，就要在 `RAW` 里补一行**：

```python
("constellation-id", "中文名", "English", "Latin", "Abbr", 关卡号, 赤经小时, 赤纬度,
 面积排名, "最亮星中文", "Brightest EN", 视星等, ["相邻拉丁名", ...]),
```

- `constellation-id` 必须等于关卡数据里的 `theme.id`（如 `orion`、`ursa-major`）；
- 相邻星座用**拉丁名**写，若该星座也在游戏内，图鉴会自动变成可点击跳转；
- 补完运行 `python tools/build_sky.py`。
- 忘了补不会让游戏坏掉，但 `check_levels.py` 会警告，且图鉴里那一关不会出现。

## 4. 关卡必须满足的约束（历史教训，直接照抄）

1. **零猜测可解**：求解器从开局能纯推理推完；否则不许进关卡。`check_level(d, static=False)` 里的 `static=False` **必须保留**——静态枚举是组合爆炸，开了会卡死（尤其 ≥10×10）。
2. **雷密度 ≈20%**：太低会出现"开局连锁翻掉大半盘"（玩起来像白送），太高会变成纯插旗。
3. **尽量没有孤立雷**（周围 8 格无雷的雷）：玩家"一眼就知道是雷"，推理感被削弱。目标 ≤2，最好 ≤1。
4. **尽量不要有空行/空列**：会显得边缘很空（用户明确反馈过）。第 1 关可以例外（走降级）。
5. **探格次数要有目标带**：太低=太短，太高=枯燥。目前 19–76 次，随关卡上升。
6. **所有关卡 `showRuns: true`**（2026-10-26 起第 1 关也显示行列线索，首关即引入数织）。
7. **星座不能重复**（一关一个星座）；`check_levels.py` 会检查。

## 5. 已知会失败的星座（别浪费时间硬试）

以下星座在 8×8–13×13、常见杂星数量下**找不到零猜测可解**的摆法（已实测）：

- 天鹰座 Aquila、大犬座 Canis Major、金牛座 Taurus、鲸鱼座 Cetus

可用备用：**武仙 Her、天龙 Dra、半人马 Cen、蛇夫 Oph、船底 Car、长蛇 Hya、牧夫 Boo、英仙 Per** 等。
另外：小棋盘（6×6–7×7）放不下 9 颗以上的星（缩放到格子会重合，`scale_centre` 直接返回 `None`）。

## 6. 两个健壮性机制（别删）

- **写入保护**：`fit_constellation_levels.py` 末尾有"生成结果少于 3 关就不覆盖 `levels.json`"，防止一次失败把数据清空（真的发生过，数据被写成 0 关）。
- **松紧阶梯**：先"无空行空列 + 孤立雷 ≤2"，压不住再逐级放宽（`require_filled` / `iso_cap`），并在输出里标注"上限/满"。不要为了完美约束把整轮 generate 卡死。

## 7. 需要有人收尾时

关卡扩完后如果来不及同步文档/图鉴/打包，把 `tools/levels.json` 和 `tools/fit_constellation_levels.py` 提交即可，然后在对话里说一声"关卡已扩到 N 关，需要同步文档与图鉴数据"，由文档/图鉴会话接手执行 §2 的第 3–6 步。