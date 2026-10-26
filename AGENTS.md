# AGENTS.md — Asterweave 多会话协作须知

这个仓库**同时有多个 agent 会话在改**。动手之前请先读
[`tools/coord/PROTOCOL.md`](tools/coord/PROTOCOL.md)（完整协议）。

## 最快上手

```powershell
# 1) 看现在谁在动什么（只读，随时可跑）
powershell -NoProfile -File tools\coord\coord.ps1 status

# 2) 声明你这轮要动的路径
powershell -NoProfile -File tools\coord\coord.ps1 claim -Session <你的会话名> -Paths <路径1>,<路径2>

# 3) 干完只提交你列出的路径（绝不 git add -A）
powershell -NoProfile -File tools\coord\coord.ps1 commit -Session <会话名> -Message "说明" -Paths <路径1>,<路径2>
powershell -NoProfile -File tools\coord\coord.ps1 push   -Session <会话名>
powershell -NoProfile -File tools\coord\coord.ps1 release -Session <会话名>
```

## 五条铁律

1. **改之前先 `claim`**；别人已声明的路径不要碰。
2. **禁止 `git add -A` / `git add .` / `git commit -a`** —— 会把别的会话没写完的东西卷进你的提交。
3. **禁止 `git push --force`**（含 `--force-with-lease`）；落后就 `git fetch` + `git rebase` 再推。
4. **禁止 `git commit --amend` 已推送的提交。**
5. **改 `game/index.html` 的会话独占构建**：`index.html`、`dist/`、`星织-游戏本体.zip` 都是生成的，
   你跑构建会覆盖别人正在编辑的生成物；别人改源码时也不要构建。

## 两条已装好的护栏（自动生效）

- `pre-push`：拦下非快进推送和删除远端分支 —— **对所有会话生效，无需配置**。
- `pre-commit`：设置了 `COORD_SESSION` 时才生效，会把 `git add -A` 挡下。
  临时绕过 `COORD_BYPASS=1 git commit …`。

## 想彻底不互相干扰：用独立工作区

```powershell
powershell -NoProfile -File tools\coord\new-session.ps1 -Name <会话名>
# 在 D:\Asterweave-sessions\<会话名> 里干活，推到自己的 session/<会话名> 分支
```

## 环境（本机特有，照做就行）

- **没有 `pwsh`，用 `powershell`（Windows PowerShell 5.1）。**
- 改过仓库里的 `.ps1` 之后跑 `powershell -NoProfile -File tools\coord\fix-bom.ps1`
  （含中文的脚本必须 UTF-8 带 BOM，否则 5.1 会按 GBK 解码导致语法报错）。
- 改了协调器或 hook 之后跑 `powershell -NoProfile -File tools\coord\selftest.ps1` 自检。
