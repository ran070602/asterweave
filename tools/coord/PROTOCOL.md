# Asterweave 多会话协作协议

> **适用对象**：所有在 Asterweave 仓库里干活的会话（人 / agent 都算）。
> **要解决的问题**：多个会话同时改这个仓库时，不互相覆盖、不互相卷走半成品、不互相冲掉提交。
> **工具**：`tools\coord\coord.ps1`（提交/推送串行化）与 `tools\coord\new-session.ps1`（开独立工作区）。

---

## 0. 风险从哪来

历史上这个仓库**只有一个工作目录、一个 worktree、所有人共用 `main`**，于是有四类事故：

| 事故 | 怎么发生 | 后果 |
|---|---|---|
| **A. 构建产物覆盖源码改动** | `index.html`、`dist/`、`星织-游戏本体.zip` 都是由 `game/index.html` **生成**的。A 在编辑源码，B 跑了一次构建 → A 的改动被生成物覆盖 | 静默丢工作 |
| **B. `git add -A` 卷走别人的半成品** | 甲 `git add -A` 时乙的文件也是 modified → 乙没写完的东西进了甲的提交 | 提交污染 |
| **C. 非快进推送冲掉远端提交** | 甲已推送；乙 amend/rebase 后 `git push --force` → 甲的提交从远端消失 | 远端丢历史 |
| **D. 提交时序互相打断** | 两人同时 `git add`/`commit` 撞 `index.lock`；或一方 `--amend` 掉另一方已依赖的提交 | 操作失败、基线漂移 |

**A 类事故 git 层面完全看不见，也是最容易真丢东西的一类。**

---

## 1. 推荐工作方式：一个会话一个 worktree

这是唯一能**根治** A 类与 C 类事故的办法：工作区文件物理隔离。

```powershell
# 给会话开一个独立工作区（独立目录 + 独立分支 session/<名字>）
powershell -NoProfile -File tools\coord\new-session.ps1 -Name game-a
# 默认建在 D:\Asterweave-sessions\game-a

# 看看现在有哪些工作区、谁在动什么
powershell -NoProfile -File tools\coord\new-session.ps1 -List

# 用完清掉
powershell -NoProfile -File tools\coord\new-session.ps1 -Remove -Name game-a
```

然后在**自己的工作区目录里**干活：

```powershell
cd D:\Asterweave-sessions\game-a
$env:COORD_SESSION = 'game-a'     # 设一次，后续命令可省略 -Session

powershell -NoProfile -File tools\coord\coord.ps1 status
powershell -NoProfile -File tools\coord\coord.ps1 claim  -Paths game/index.html
#  ... 干活 ...
powershell -NoProfile -File tools\coord\coord.ps1 commit -Message "说明" -Paths game/index.html,index.html
powershell -NoProfile -File tools\coord\coord.ps1 push     # 推到自己的 session/game-a
```

- 各会话**只推自己的分支**，`main` 由协调会话合并（`git checkout main; git merge --no-ff session/game-a`）后推送。
- 协调状态（锁 + 租约）放在 **`.git\asterweave-coord\`**，也就是 git 公共目录里，**所有 worktree 共享同一份**——
  所以各 worktree 之间仍然能互相看见、互相避让，不会各说各话。
- `tools\coord\` 是仓库里的 tracked 文件，新 worktree 自动就有，不用额外拷贝。

### 还没上 worktree 时（所有人共用 D:\Asterweave）

也能用，但只能降低 D 类与 C 类风险，**A 类与「同一文件同时编辑」仍然防不住**。此时至少做到：

```powershell
powershell -NoProfile -File tools\coord\coord.ps1 status
powershell -NoProfile -File tools\coord\coord.ps1 claim -Session <名字> -Paths game/index.html,docs/SPEC.md
```

---

## 2. 五条铁律

1. **动手改之前先 `claim`。** 别人已声明的路径不要碰。
2. **不许 `git add -A` / `git add .` / `git commit -a`。** 只暂存显式列出的路径（用协调器提交，它替你保证）。
3. **不许 `git push --force`（含 `--force-with-lease`）。** 落后就先 rebase 再推。
4. **不许 `git commit --amend` 已推送的提交。**
5. **改 `game/index.html` 的会话独占构建。** 构建会重写 `index.html` / `dist/` / zip；
   构建期间别人别动这些生成物，也**不要在别人改源码时构建**。

---

## 3. 命令参考

| 命令 | 作用 | 退出码 |
|---|---|---|
| `status` | 只读。HEAD、领先/落后、活跃租约、每个未提交改动的归属与风险 | 0 |
| `claim -Session S -Paths p1,p2` | **追加式**声明作用域，默认 45 分钟（`-LeaseMinutes` 可调） | 冲突 3 |
| `release -Session S` | 清空该会话的全部租约（不动别人的） | 0 |
| `commit -Session S -Message "…" -Paths …` | 拿锁 → 校验索引干净 → 拒绝与他方租约重叠 → 自动追加认领 → 只暂存列出的路径 → 提交 | 脏索引 4 / 冲突 3 / 无改动 5 / 失败 6 |
| `push -Session S` | 拿锁 → fetch → 落后则拒绝 → 快进推送（从不 force） | fetch 失败 7 / 落后 8 / push 失败 9 |
| `watch` | 快照对比：抓出「上次快照之后谁动了什么」，用来发现别的会话 | 0 |
| `selftest` | 体检：git 可用性、租约、锁、两个 hook 是否在位 | 0 |

通用开关：`-DryRun`（commit/push 只报告不执行）、`-Force`（允许覆盖别人的租约声明，谨慎）、
`-RepoRoot <路径>`（指定仓库，便于脚本化）。

---

## 4. 冲突了怎么办

| 现象 | 处理 |
|---|---|
| `claim` 报「已被 X 声明」 | 换路径 / 等 X `release` / 找 X 约定分工。**不要**直接 `-Force`。 |
| `commit` 报「索引里已有暂存内容」 | 有人先你一步暂存了。先 `git status` 看清归属，**别替别人 unstage**。 |
| `commit` 报「路径不在本会话租约范围内」 | 补一次 `claim`（或直接用 `coord.ps1 commit`，它会自动认领）。 |
| `push` 报「本地落后 N 个提交」 | `git fetch origin` → `git rebase origin/main` → 重跑 `push`。 |
| hook 报「非快进推送已拦下」 | 同上。别用 `--force`。 |
| 文件被别人的构建覆盖了 | **立刻停止构建**（避免二次覆盖）。`git reflog`、`git fsck --lost-found` 找回过版本；`.scratch/` 里的脚本可能还有中间产物。 |

---

## 5. 哪些是机械强制的，哪些靠自觉

**已装好的两道 git hook（放在 `.git/hooks/`，所有 worktree 共享，自动生效）：**

- **`pre-push`**：拦下**非快进推送**和**删除远端分支**。不需要任何环境变量就生效，正常快进推送不受影响。
  确需强推：`git push --no-verify …`，但先确认没人依赖那段历史。

- **`pre-commit`**：**只在设置了 `COORD_SESSION` 时生效**（未设置则完全放行，不打扰不参与协调的会话）。
  生效时要求：暂存区每个路径都在你自己的租约内，且不落在别人的活跃租约内 ——
  也就是一旦加入协调，`git add -A` 会被直接挡下。
  临时绕过：`COORD_BYPASS=1 git commit …`

**靠自觉（工具管不了）：**

- 不跑构建就不会覆盖生成物 —— 这条没有任何 hook 能把关；
- 不用协调器、直接 `git commit`/`git push` 时，`pre-commit` 的归属检查会退化为放行；
- `--no-verify` / `COORD_BYPASS=1` 是随时可用的后门（故意的，否则卡住时无路可走）。

---

## 6. 本机环境坑（都实际踩过，别再踩）

1. **没有 `pwsh`，只有 Windows PowerShell 5.1。**
   所有命令写 `powershell -NoProfile -File …`；写 `pwsh` 会直接报「无法识别」。

2. **含中文的 `.ps1` 必须存成 UTF-8 带 BOM。**
   5.1 对无 BOM 的脚本按系统 ANSI（GBK）解码 → 中文乱码 → **语法解析失败**。
   注意 DSH 的 write/edit 工具重写文件会**丢掉 BOM**，所以改完脚本跑一次：
   ```powershell
   powershell -NoProfile -File tools\coord\fix-bom.ps1   # 自动发现本目录所有 .ps1
   ```

3. **`& git … | Select-Object -First 1` 之后不能再信 `$LASTEXITCODE`。**
   管道被提前截断，5.1 会把它记成 **-1**，导致判断永远为假。先整体赋值，再取首项。

4. **`leases.tsv` 必须 LF 换行。** CRLF 会让 sh 版 hook 读到的路径尾部多一个 `\r`，
   **路径匹配静默失效、冲突检测形同虚设**（最隐蔽的一个坑：看着在防护，其实没防）。
   协调器已改用 LF 写出，hook 也做了 `\r` 容错。

5. **`git rev-list --left-right --count A...B` 的左右含义**：
   左 = 只有 A 有（`origin/main...HEAD` 时即「落后」），右 = 只有 B 有（即「领先」）。读反会拦下每一次合法推送。

6. **PowerShell 单元素退化**：管道只返回一项时结果是标量，`$x[0]` 会取到**首字符**、`.Count` 可能为空。
   一律用 `@()` 包住。

7. **PS 5.1 里 `$ErrorActionPreference='Stop'` 时，native 命令写 stderr 会被当成终止性错误。**
   调 git 时要临时降到 `Continue`（见 `coord.ps1` 的 `Invoke-GitText`）。

8. **`Write-Host '文本' + $var` 缺括号**会把 `+` 当成独立参数打出来。要写 `Write-Host ('文本' + $var)`。

---

## 7. 自检

改了协调器或 hook 之后跑这个（在隔离的临时仓库里验证，**不碰真实仓库**）：

```powershell
powershell -NoProfile -File tools\coord\selftest.ps1
```

当前基线：**32 项断言全部通过**。覆盖：租约冲突（含目录/文件父子重叠）、脏索引拒绝、只提交显式路径、
`git add -A` 拦截、CRLF 回归、未启用协调器时零干扰、领先/落后方向、落后拒绝推送、force push 拦截、
rebase 后正常推送且历史不丢、release 语义。

---

## 8. 记录与追溯

协调状态放在 **git 公共目录**下（`D:\Asterweave\.git\asterweave-coord\`），
因此它：① 被所有 worktree 共享；② 永远不出现在 `git status` 里；③ 不可能被别人的 `git add -A` 卷进提交。

- `leases.tsv` —— 当前租约（`session<TAB>过期时间戳<TAB>作用域`）
- `coord.lock` —— 协调锁（含持锁会话、PID、开始时间）
- `coord.log` —— 所有拿锁/认领/提交/推送/新建 worktree 的时间线
- `watch.json` —— `watch` 的上一份快照

---

## 9. 能力边界（写清楚，不要说满）

- **防不住不参与协调的会话**：未设 `COORD_SESSION` 时 `pre-commit` 完全放行。
- **防不住 `--no-verify` / `COORD_BYPASS=1`**：后门是故意留的。
- **共用一个工作目录时防不住同文件同时编辑与构建覆盖**：git 层面只能「发现得早、恢复得快」。
  **要根治就必须上 worktree 隔离（见 §1）。**
- 协调器只看得见「效果」（文件 mtime、reflog、git 状态），看不见别的会话的「意图」。
