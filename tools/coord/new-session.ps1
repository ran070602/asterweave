<#
.SYNOPSIS
  Asterweave 会话工作区助手：给一个会话开独立 worktree（独立目录 + 独立分支），
  让多个会话在物理上不再改同一批文件。

.DESCRIPTION
  为什么需要它：只要两个会话共用 D:\Asterweave 这一个工作目录，
  同一个文件被两边同时编辑、或被构建产物覆盖，就是防不住的。
  每个会话一个 worktree 之后：
    * 工作区文件完全独立 —— 「构建覆盖别人源码」这类事故从根本消失；
    * 各自推自己的分支 session/<名字> —— main 只由协调会话合并推送，
      「强推冲掉别人提交」也消失。
  协调状态（锁、租约）放在共享的 .git\asterweave-coord 下，所以各 worktree
  之间仍然能互相看见、互相避让；tools\coord 是 tracked 的，新 worktree 自动就有。

.EXAMPLE
  powershell -NoProfile -File tools\coord\new-session.ps1 -Name game-a
  powershell -NoProfile -File tools\coord\new-session.ps1 -List
  powershell -NoProfile -File tools\coord\new-session.ps1 -Remove -Name game-a
#>
[CmdletBinding()]
param(
  [string]$Name,
  [string]$Base = 'main',
  [string]$Root,
  [switch]$List,
  [switch]$Remove,
  [switch]$Force,
  [switch]$RequireFetch
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

function Get-Git {
  param([string[]]$GitArgs)
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $raw = & git -C $script:Repo @GitArgs 2>&1
    $code = $LASTEXITCODE
  } finally { $ErrorActionPreference = $old }
  $text = @(); foreach ($o in $raw) { $text += [string]$o }
  return [pscustomobject]@{ Code = $code; Out = $text }
}

# 注意：不要写成 `& git ... | Select-Object -First 1` 之后再看 $LASTEXITCODE。
# Select-Object -First 1 会提前截断管道，PS 5.1 会把 $LASTEXITCODE 记成 -1，
# 于是「是否在仓库内」的判断永远为假。先整体赋值，再取首项。
$ErrorActionPreference = 'Continue'
$rawRepo = & git rev-parse --show-toplevel 2>&1
$repoCode = $LASTEXITCODE
$Repo = [string](@($rawRepo | Where-Object { "$_" -ne '' }) | Select-Object -First 1)
if ($repoCode -ne 0 -or -not $Repo) { throw '当前目录不在 git 仓库内（先 cd 到仓库，或从仓库内运行本脚本）' }
$Repo = ($Repo -replace '/', '\')
$script:Repo = $Repo

$rawCommon = & git -C $Repo rev-parse --path-format=absolute --git-common-dir 2>&1
$CommonRaw = [string](@($rawCommon | Where-Object { "$_" -ne '' }) | Select-Object -First 1)
if (-not $CommonRaw) { $CommonRaw = Join-Path $Repo '.git' }
$StateDir = Join-Path ([string]$CommonRaw) 'asterweave-coord'

$Parent = Split-Path -Parent $Repo
if (-not $Root) { $Root = Join-Path $Parent 'Asterweave-sessions' }

function Test-WorktreeRegistered {
  param([string]$Path)
  # worktree list --porcelain 里的路径用的是正斜杠，而传进来的多半是反斜杠，
  # 直接做字符串或正则匹配会永远匹配不到。统一成正斜杠再比。
  $fwd = ($Path -replace '\\', '/').TrimEnd('/')
  foreach ($line in (Get-Git @('worktree', 'list', '--porcelain')).Out) {
    if ($line -match '^worktree (.+)$') {
      if ((($Matches[1] -replace '\\', '/').TrimEnd('/')) -ieq $fwd) { return $true }
    }
  }
  return $false
}

function Show-Sessions {
  Write-Host ''
  Write-Host '=== 当前 git worktree ===' -ForegroundColor Cyan
  $raw = (Get-Git @('worktree', 'list', '--porcelain')).Out
  $rows = New-Object System.Collections.ArrayList
  $cur = @{}
  foreach ($line in $raw) {
    if ($line -match '^worktree (.+)$') {
      if ($cur.Count -gt 0) { [void]$rows.Add([pscustomobject]$cur) }
      $cur = @{ Path = $Matches[1]; Branch = '(detached)'; Detached = $false }
    } elseif ($line -match '^branch (.+)$') {
      $cur.Branch = ($Matches[1] -replace '^refs/heads/', '')
    } elseif ($line -match '^detached') {
      $cur.Detached = $true
    }
  }
  if ($cur.Count -gt 0) { [void]$rows.Add([pscustomobject]$cur) }
  foreach ($w in $rows) {
    $tag = ''
    if ($w.Branch -like 'session/*') { $tag = '  <- 会话工作区' }
    Write-Host ('  ' + $w.Branch.PadRight(22) + ' ' + $w.Path + $tag)
  }

  $lease = Join-Path $StateDir 'leases.tsv'
  Write-Host ''
  Write-Host '=== 活跃作用域租约（跨所有 worktree 共享）===' -ForegroundColor Cyan
  if (-not (Test-Path -LiteralPath $lease)) {
    Write-Host '  （无：还没有会话声明作用域）' -ForegroundColor DarkGray
  } else {
    $now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    $any = $false
    foreach ($line in [System.IO.File]::ReadAllLines($lease, [Text.Encoding]::UTF8)) {
      if (-not $line -or $line.StartsWith('#')) { continue }
      $c = $line -split "`t"
      if ($c.Count -lt 3) { continue }
      $exp = 0L
      if (-not [long]::TryParse($c[1], [ref]$exp)) { continue }
      if ($exp -le $now) { continue }
      $any = $true
      $mins = [math]::Round(([DateTimeOffset]::FromUnixTimeSeconds($exp).LocalDateTime - (Get-Date)).TotalMinutes, 1)
      Write-Host ('  ' + $c[0].PadRight(16) + ' 剩余 ' + ('{0,7}' -f $mins) + ' 分钟   ' + $c[2])
    }
    if (-not $any) { Write-Host '  （无活跃租约）' -ForegroundColor DarkGray }
  }
  Write-Host ''
}

function New-Session {
  if (-not $Name) { throw '需要 -Name，例如 -Name game-a' }
  if ($Name -notmatch '^[A-Za-z0-9][A-Za-z0-9._-]*$') { throw '名字只能包含字母、数字、点、下划线、连字符，且以字母或数字开头' }

  $branch = 'session/' + $Name
  $path = Join-Path $Root $Name

  if (Test-WorktreeRegistered -Path $path) { throw ('这个路径已经是 worktree 了：' + $path) }
  if (Test-Path -LiteralPath $path) { throw ('目标目录已存在且不是 worktree，请先处理：' + $path) }
  if ((Get-Git @('rev-parse', '--verify', '--quiet', $branch)).Code -eq 0) { throw ('分支已存在：' + $branch + '（换名字，或用 -Remove 清掉旧会话）') }

  Write-Host ('-> fetch origin/' + $Base + ' …') -ForegroundColor Gray
  $f = Get-Git @('fetch', 'origin', '--prune')
  $baseRef = 'origin/' + $Base
  if ($f.Code -ne 0) {
    Write-Host '! fetch 失败（网络或凭据问题）：' -ForegroundColor Yellow
    $f.Out | Select-Object -First 3 | ForEach-Object { Write-Host ('   ' + $_) -ForegroundColor Yellow }
    if ($RequireFetch) {
      Write-Host 'X 指定了 -RequireFetch，未创建任何东西。' -ForegroundColor Red
      exit 7
    }
    Write-Host ('  降级：基于本地 ' + $Base + ' 创建。基线可能不是最新，之后 git fetch && git rebase 补上即可。') -ForegroundColor Yellow
    $baseRef = $Base
  }
  if ((Get-Git @('rev-parse', '--verify', '--quiet', $baseRef)).Code -ne 0) { $baseRef = $Base }

  New-Item -ItemType Directory -Force -Path $Root | Out-Null
  Write-Host ('-> 创建 worktree：' + $path + '   分支：' + $branch) -ForegroundColor Gray
  $a = Get-Git @('worktree', 'add', '-b', $branch, $path, $baseRef)
  if ($a.Code -ne 0) {
    Write-Host 'X 创建失败：' -ForegroundColor Red
    $a.Out | ForEach-Object { Write-Host ('   ' + $_) -ForegroundColor Red }
    exit 1
  }
  $a.Out | ForEach-Object { Write-Host ('   ' + $_) }

  New-Item -ItemType Directory -Force -Path $StateDir | Out-Null
  $log = Join-Path $StateDir 'coord.log'
  try {
    [System.IO.File]::AppendAllText($log, ('[' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '] [worktree] 新建会话 ' + $Name + ' -> ' + $path + ' (' + $branch + ') 基线 ' + $baseRef + "`n"), (New-Object System.Text.UTF8Encoding($false)))
  } catch { }

  Write-Host ''
  Write-Host '✓ 会话工作区就绪' -ForegroundColor Green
  Write-Host ('   目录：' + $path)
  Write-Host ('   分支：' + $branch + '   （基线 ' + $baseRef + '）')
  Write-Host ''
  Write-Host '在该目录里这样干活：' -ForegroundColor Cyan
  Write-Host ('   cd ' + $path)
  Write-Host ('   $env:COORD_SESSION = ''' + $Name + '''')
  Write-Host '   powershell -NoProfile -File tools\coord\coord.ps1 status'
  Write-Host '   powershell -NoProfile -File tools\coord\coord.ps1 claim -Paths game/index.html'
  Write-Host '   powershell -NoProfile -File tools\coord\coord.ps1 commit -Message "..." -Paths game/index.html'
  Write-Host ('   powershell -NoProfile -File tools\coord\coord.ps1 push      # 推到自己的 ' + $branch)
  Write-Host ''
  Write-Host '注意：这里 push 的是你自己的分支，不要直接推 main。' -ForegroundColor Yellow
  Write-Host ('  合并回 main 由协调会话完成：git checkout main; git merge --no-ff ' + $branch) -ForegroundColor Yellow
  Write-Host ''
}

function Remove-Session {
  if (-not $Name) { throw '需要 -Name' }
  $branch = 'session/' + $Name
  $path = Join-Path $Root $Name
  $list = (Get-Git @('worktree', 'list', '--porcelain')).Out -join "`n"
  if (-not (Test-WorktreeRegistered -Path $path)) { throw ('不是已注册的 worktree：' + $path + '（本脚本只管理 ' + $Root + ' 下的会话工作区）') }
  if ((Resolve-Path -LiteralPath $path).Path -eq (Resolve-Path -LiteralPath $Repo).Path) { throw '拒绝操作主工作区' }

  $dirty = @((Get-Git @('-C', $path, 'status', '--porcelain')).Out)
  if ($dirty.Count -gt 0 -and -not $Force) {
    Write-Host 'X 该会话工作区还有未提交改动，拒绝删除：' -ForegroundColor Red
    $dirty | Select-Object -First 15 | ForEach-Object { Write-Host ('   ' + $_) -ForegroundColor Red }
    Write-Host '  确认不要了再加 -Force。' -ForegroundColor Yellow
    exit 4
  }
  Write-Host ('-> 移除 worktree：' + $path) -ForegroundColor Gray
  $rmArgs = @('worktree', 'remove')
  if ($Force) { $rmArgs += '--force' }
  $rmArgs += $path
  $r = Get-Git $rmArgs
  if ($r.Code -ne 0) {
    Write-Host 'X 移除失败：' -ForegroundColor Red
    $r.Out | ForEach-Object { Write-Host ('   ' + $_) -ForegroundColor Red }
    exit 1
  }
  $r.Out | ForEach-Object { Write-Host ('   ' + $_) }
  if ((Get-Git @('rev-parse', '--verify', '--quiet', $branch)).Code -eq 0) {
    Write-Host ('   分支 ' + $branch + ' 仍保留（还没合并进 main 的话别急着删）') -ForegroundColor Yellow
  }
  Write-Host '✓ 已移除' -ForegroundColor Green
}

if ($List) { Show-Sessions; exit 0 }
if ($Remove) { Remove-Session; exit 0 }
if (-not $Name) { Show-Sessions; Write-Host '用 -Name <会话名> 创建会话工作区。' -ForegroundColor Yellow; exit 0 }
New-Session
