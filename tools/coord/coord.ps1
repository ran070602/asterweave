<#
.SYNOPSIS
  Asterweave 多会话 git 协调器：把「提交 / 推送」串行化，防止会话之间互相覆盖。

.DESCRIPTION
  机制（完整规则见 tools/coord/PROTOCOL.md）：
    * 单一协调锁 state/coord.lock —— 提交/推送前先原子拿锁，带过期接管。
    * 作用域租约 leases.tsv —— 会话声明自己这段时间要动哪些文件；别人声明重叠路径会被拒。
    * commit 要求索引事先干净，且只暂存显式列出的路径，绝不把别人的半成品卷进来。
    * push 先 fetch，落后就拒绝（要求先 rebase），从不 force。

.EXAMPLE
  powershell -NoProfile -File tools\coord\coord.ps1 status
  powershell -NoProfile -File tools\coord\coord.ps1 claim -Session a -Paths game/index.html
  powershell -NoProfile -File tools\coord\coord.ps1 commit -Session a -Message "..." -Paths game/index.html,index.html
  powershell -NoProfile -File tools\coord\coord.ps1 push -Session a
#>
[CmdletBinding()]
param(
  [Parameter(Position = 0)][string]$Action = 'status',
  [string]$Session = $env:COORD_SESSION,
  [string]$Message,
  [string[]]$Paths = @(),
  [int]$LeaseMinutes = 45,
  [int]$LockTimeoutSec = 120,
  [string]$RepoRoot,
  [switch]$Force,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch { }

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Get-RepoRootPath {
  param([string]$Override)
  if ($Override) {
    if (-not (Test-Path -LiteralPath (Join-Path $Override '.git'))) { throw "指定的 RepoRoot 不是 git 仓库：$Override" }
    return (Resolve-Path -LiteralPath $Override).Path
  }
  $r = & git rev-parse --show-toplevel 2>&1
  if ($LASTEXITCODE -ne 0 -or -not $r) { throw '当前目录不在 git 仓库内（或 git 不可用）' }
  return ((($r | Select-Object -First 1) -replace '/', '\'))
}

$Repo      = Get-RepoRootPath -Override $RepoRoot
# 协调状态放在 git 公共目录（.git）下，而不是工作区里，原因有两个：
#   1) 多个 worktree 共享同一个 .git，因此也共享同一份锁与租约——否则 worktree 之间无法协调；
#   2) 永远不会出现在 git status 里，也不可能被别人的 git add -A 卷进提交。
$CommonDir = $null
$oldEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
  $cand = (& git -C $Repo rev-parse --path-format=absolute --git-common-dir 2>&1 | Select-Object -First 1)
  if ($cand -and (Test-Path -LiteralPath ([string]$cand))) { $CommonDir = [string]$cand }
} catch { }
$ErrorActionPreference = $oldEap
if (-not $CommonDir) { $CommonDir = Join-Path $Repo '.git' }
$ScriptDir = Split-Path -Parent $PSCommandPath
$StateDir  = Join-Path $CommonDir 'asterweave-coord'
$LeaseFile = Join-Path $StateDir 'leases.tsv'
$LockFile  = Join-Path $StateDir 'coord.lock'
$LogFile   = Join-Path $StateDir 'coord.log'
$SnapFile  = Join-Path $StateDir 'watch.json'
$LockTtlMinutes = 10

New-Item -ItemType Directory -Force -Path $StateDir | Out-Null

function Write-Log {
  param([string]$Text)
  $who = if ($Session) { $Session } else { 'unknown' }
  $line = '[{0}] [{1}] {2}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $who, $Text
  try { [System.IO.File]::AppendAllText($LogFile, $line + "`r`n", $Utf8NoBom) } catch { }
}

function Invoke-GitText {
  param([string[]]$GitArgs)
  # PS 5.1：git 往 stderr 写正常信息时，若 ErrorActionPreference=Stop 会被当成
  # 终止性错误。这里临时降到 Continue，并把输出统一转成字符串。
  $old = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $raw = & git -C $Repo @GitArgs 2>&1
    $code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $old
  }
  $text = @()
  foreach ($o in $raw) { $text += [string]$o }
  return [pscustomobject]@{ Code = $code; Out = $text }
}

function Get-GitLines {
  param([string[]]$GitArgs)
  $r = Invoke-GitText $GitArgs
  return @($r.Out | Where-Object { $_ -ne $null -and "$_" -ne '' })
}

function Get-CurrentBranch {
  return ((Get-GitLines @('rev-parse', '--abbrev-ref', 'HEAD')) | Select-Object -First 1)
}

# ---------------------------------------------------------------- 协调锁

function Test-LockStale {
  if (-not (Test-Path -LiteralPath $LockFile)) { return $true }
  $age = (Get-Date) - (Get-Item -LiteralPath $LockFile).LastWriteTime
  if ($age.TotalMinutes -gt $LockTtlMinutes) { return $true }
  $txt = [System.IO.File]::ReadAllText($LockFile, [Text.Encoding]::UTF8)
  if ($txt -match 'pid=(\d+)') {
    $proc = Get-Process -Id ([int]$Matches[1]) -ErrorAction SilentlyContinue
    if (-not $proc) { return $true }
  }
  return $false
}

function Enter-CoordLock {
  param([string]$Why)
  $deadline = (Get-Date).AddSeconds($LockTimeoutSec)
  while ($true) {
    try {
      $fs = [System.IO.File]::Open($LockFile, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
      try {
        $who = if ($Session) { $Session } else { 'unknown' }
        $bytes = $Utf8NoBom.GetBytes("session=$who`npid=$PID`nstarted=$((Get-Date).ToString('o'))`nwhy=$Why`n")
        $fs.Write($bytes, 0, $bytes.Length)
      } finally { $fs.Close() }
      Write-Log "LOCK+ $Why"
      return
    } catch [System.IO.IOException] {
      if (Test-LockStale) {
        $old = ''
        try { $old = [System.IO.File]::ReadAllText($LockFile, [Text.Encoding]::UTF8) } catch { }
        Write-Warning ("接管过期锁（超过 " + $LockTtlMinutes + " 分钟或持有进程已退出）：" + ($old -replace "`r?`n", ' | '))
        Write-Log 'LOCK! 接管过期锁'
        Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
        continue
      }
      if ((Get-Date) -gt $deadline) {
        $holder = ''
        try { $holder = [System.IO.File]::ReadAllText($LockFile, [Text.Encoding]::UTF8) } catch { }
        throw ("等待协调锁超时（" + $LockTimeoutSec + " 秒）。持锁方：" + ($holder -replace "`r?`n", ' | '))
      }
      Start-Sleep -Milliseconds 400
    }
  }
}

function Exit-CoordLock {
  Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
  Write-Log 'LOCK-'
}

# ---------------------------------------------------------------- 作用域租约

$Tab = [string][char]9

function Get-Leases {
  if (-not (Test-Path -LiteralPath $LeaseFile)) { return @() }
  $rows = New-Object System.Collections.ArrayList
  $lines = @()
  try { $lines = [System.IO.File]::ReadAllLines($LeaseFile, [Text.Encoding]::UTF8) } catch { return @() }
  foreach ($line in $lines) {
    if (-not $line) { continue }
    if ($line.StartsWith('#')) { continue }
    $p = $line -split $Tab
    if ($p.Count -lt 3) { continue }
    $exp = 0L
    if (-not [long]::TryParse($p[1], [ref]$exp)) { continue }
    [void]$rows.Add([pscustomobject]@{ Session = $p[0]; Expires = $exp; Scope = $p[2] })
  }
  return $rows.ToArray()
}

function Test-LeaseLive {
  param($Lease)
  return ($Lease.Expires -gt [DateTimeOffset]::UtcNow.ToUnixTimeSeconds())
}

function Save-Leases {
  param($Leases)
  # 必须用 LF 换行：sh 版 hook 用 read 逐行解析，CRLF 会让 scope 尾部多一个 \r，
  # 导致路径匹配全部失效（冲突检测形同虚设）。
  $sb = New-Object System.Text.StringBuilder
  [void]$sb.Append('# session' + $Tab + 'expires_unix' + $Tab + 'scope' + "`n")
  foreach ($l in $Leases) {
    if ($l.Session -match $Tab -or $l.Scope -match $Tab) { continue }
    [void]$sb.Append($l.Session + $Tab + $l.Expires + $Tab + $l.Scope + "`n")
  }
  [System.IO.File]::WriteAllText($LeaseFile, $sb.ToString(), $Utf8NoBom)
}

function Normalize-Path {
  param([string]$P)
  if (-not $P) { return $P }
  $n = ($P -replace '\\', '/')
  while ($n.StartsWith('./')) { $n = $n.Substring(2) }
  return $n.TrimEnd('/')
}

function Test-ScopeMatch {
  param([string]$Scope, [string]$Path)
  $s = Normalize-Path $Scope
  $p = Normalize-Path $Path
  if ($s -eq '') { return $true }
  if ($p -eq $s) { return $true }
  return $p.StartsWith($s + '/', [StringComparison]::OrdinalIgnoreCase)
}

# 双向重叠：目录级租约与文件级租约互为父子时也算冲突
function Test-ScopeOverlap {
  param([string]$A, [string]$B)
  if (Test-ScopeMatch -Scope $A -Path $B) { return $true }
  return (Test-ScopeMatch -Scope $B -Path $A)
}

function Get-LiveLeases { return @(Get-Leases | Where-Object { Test-LeaseLive $_ }) }

# 追加式认领：保留已有租约，只补上还没认领的路径。
# claim 与 commit 都用它，保证「协调器的判断口径」与「pre-commit hook 的判断口径」一致。
function Add-MyLeases {
  param([string[]]$NewPaths, [int]$Minutes)
  $live = @(Get-Leases | Where-Object { Test-LeaseLive $_ })
  $exp = [DateTimeOffset]::UtcNow.AddMinutes($Minutes).ToUnixTimeSeconds()
  $keep = New-Object System.Collections.ArrayList
  foreach ($l in $live) { [void]$keep.Add($l) }
  foreach ($p in $NewPaths) {
    $np = Normalize-Path $p
    $exists = @($keep | Where-Object { $_.Session -eq $Session -and $_.Scope -eq $np })
    if ($exists.Count -gt 0) { continue }
    [void]$keep.Add([pscustomobject]@{ Session = $Session; Expires = $exp; Scope = $np })
  }
  Save-Leases $keep.ToArray()
}

function Remove-ExpiredLeases {
  $all = @(Get-Leases)
  $live = @($all | Where-Object { Test-LeaseLive $_ })
  if ($live.Count -ne $all.Count) { Save-Leases $live }
  return $live
}

# ---------------------------------------------------------------- 读取工作区

function Get-DirtyFiles {
  $out = Get-GitLines @('-c', 'core.quotepath=false', 'status', '--porcelain')
  $res = New-Object System.Collections.ArrayList
  foreach ($line in $out) {
    if (-not $line -or $line.Length -lt 4) { continue }
    $code = $line.Substring(0, 2)
    $path = $line.Substring(3).Trim()
    if ($path -match '^".*"$') { $path = $path.Trim('"') }
    if ($path -match ' -> ') { $path = ($path -split ' -> ')[-1].Trim('"') }
    [void]$res.Add([pscustomobject]@{ Code = $code; Path = Normalize-Path $path })
  }
  return $res.ToArray()
}

function Get-Divergence {
  $branch = Get-CurrentBranch
  $up = $null; $ahead = 0; $behind = 0
  $r = Invoke-GitText @('rev-parse', '--abbrev-ref', ($branch + '@{upstream}'))
  if ($r.Code -eq 0) {
    $up = (($r.Out | Where-Object { "$_" -ne '' }) | Select-Object -First 1)
    $c = Invoke-GitText @('rev-list', '--left-right', '--count', ($up + '...HEAD'))
    $line = (($c.Out | Where-Object { "$_" -ne '' }) | Select-Object -First 1)
    if ($line) {
      $parts = @($line -split '\s+' | Where-Object { $_ -ne '' })
      # rev-list --left-right --count "up...HEAD" 输出两列：
      #   左 = 只有 upstream 有（即本地「落后」）  右 = 只有 HEAD 有（即本地「领先」）
      if ($parts.Count -ge 2) { $behind = [int]$parts[0]; $ahead = [int]$parts[1] }
    }
  }
  return [pscustomobject]@{ Branch = $branch; Upstream = $up; Ahead = $ahead; Behind = $behind }
}

function Show-Status {
  $head = ((Get-GitLines @('log', '-1', '--format=%h %ad %s', '--date=format:%Y-%m-%d %H:%M:%S')) | Select-Object -First 1)
  $div = Get-Divergence
  # 必须 @() 包住：只有一项时 PowerShell 会退化成标量，.Count 会显示为空。
  $live = @(Get-LiveLeases)
  $dirty = @(Get-DirtyFiles)

  Write-Host ''
  Write-Host '=== Asterweave 协调状态 ===' -ForegroundColor Cyan
  Write-Host ("仓库   : " + $Repo)
  Write-Host ("分支   : " + $div.Branch + "  ->  " + $div.Upstream)
  Write-Host ("HEAD   : " + $head)
  $color = 'Gray'
  if ($div.Behind -gt 0) { $color = 'Red' } elseif ($div.Ahead -gt 0) { $color = 'Yellow' }
  Write-Host ("与上游 : 领先 " + $div.Ahead + " / 落后 " + $div.Behind) -ForegroundColor $color
  if (Test-Path -LiteralPath $LockFile) {
    $lk = ''
    try { $lk = [System.IO.File]::ReadAllText($LockFile, [Text.Encoding]::UTF8) } catch { }
    Write-Host ("协调锁 : 占用 -> " + ($lk -replace "`r?`n", ' | ')) -ForegroundColor Yellow
  } else {
    Write-Host '协调锁 : 空闲' -ForegroundColor Gray
  }

  Write-Host ''
  Write-Host ("--- 活跃租约（" + $live.Count + "）---") -ForegroundColor Cyan
  if ($live.Count -eq 0) { Write-Host '（无：当前没有会话声明作用域）' -ForegroundColor DarkGray }
  foreach ($l in ($live | Sort-Object Session, Scope)) {
    $mins = [math]::Round(([DateTimeOffset]::FromUnixTimeSeconds($l.Expires).LocalDateTime - (Get-Date)).TotalMinutes, 1)
    Write-Host ("  " + $l.Session.PadRight(14) + " 剩余 " + ("{0,7}" -f $mins) + " 分钟   " + $l.Scope)
  }

  Write-Host ''
  Write-Host ("--- 工作区未提交改动（" + $dirty.Count + "）---") -ForegroundColor Cyan
  if ($dirty.Count -eq 0) { Write-Host '（干净）' -ForegroundColor DarkGray }
  $warn = 0
  foreach ($d in $dirty) {
    $owners = @($live | Where-Object { Test-ScopeOverlap -A $_.Scope -B $d.Path } | ForEach-Object { $_.Session } | Select-Object -Unique)
    $item = Get-Item -LiteralPath (Join-Path $Repo $d.Path) -ErrorAction SilentlyContinue
    $mt = '        --        '
    if ($item) { $mt = $item.LastWriteTime.ToString('MM-dd HH:mm:ss') }
    if ($owners.Count -gt 1) {
      Write-Host ("  [" + $d.Code + "] " + $mt + "  " + $d.Path + "   <== 多个会话同时声明！" + ($owners -join ',')) -ForegroundColor Red
      $warn++
    } elseif ($owners.Count -eq 1) {
      $mine = ''
      if ($Session -and $owners[0] -eq $Session) { $mine = '（本会话）' }
      Write-Host ("  [" + $d.Code + "] " + $mt + "  " + $d.Path + "   <- " + $owners[0] + $mine)
    } else {
      Write-Host ("  [" + $d.Code + "] " + $mt + "  " + $d.Path + "   <- 未声明（无会话认领）") -ForegroundColor Yellow
      $warn++
    }
  }

  Write-Host ''
  if ($warn -gt 0) {
    Write-Host ("! 有 " + $warn + " 处风险：未声明或多方声明的改动。") -ForegroundColor Yellow
    Write-Host '  在让任何会话提交之前，先按 PROTOCOL.md 认领作用域。' -ForegroundColor Yellow
  } else {
    Write-Host 'OK 未发现作用域冲突。' -ForegroundColor Green
  }
  Write-Host ''
}

# ---------------------------------------------------------------- 动作

function Invoke-Claim {
  if (-not $Session) { throw 'claim 需要 -Session（或设置环境变量 COORD_SESSION）' }
  if ($Paths.Count -eq 0) { throw 'claim 需要 -Paths，例如 -Paths game/index.html,docs/SPEC.md' }
  Enter-CoordLock ("claim by " + $Session)
  try {
    $live = Remove-ExpiredLeases
    $conflicts = New-Object System.Collections.ArrayList
    foreach ($p in $Paths) {
      foreach ($l in $live) {
        if ($l.Session -eq $Session) { continue }
        if (Test-ScopeOverlap -A $l.Scope -B $p) { [void]$conflicts.Add($p + "  已被 " + $l.Session + " 声明（" + $l.Scope + "）") }
      }
    }
    if ($conflicts.Count -gt 0 -and -not $Force) {
      Write-Host 'X 作用域冲突，未认领：' -ForegroundColor Red
      foreach ($c in $conflicts) { Write-Host ('   ' + $c) -ForegroundColor Red }
      Write-Host '  换路径，或等对方 release，或与对方约定分工后再 -Force 覆盖声明。' -ForegroundColor Yellow
      Write-Log ("CLAIM-REJECT conflicts=" + $conflicts.Count)
      exit 3
    }
    $exp = [DateTimeOffset]::UtcNow.AddMinutes($LeaseMinutes).ToUnixTimeSeconds()
    Add-MyLeases -NewPaths $Paths -Minutes $LeaseMinutes
    Write-Log ("CLAIM paths=" + ($Paths -join ','))
    Write-Host ("OK 已认领 " + $Paths.Count + " 个路径，租约 " + $LeaseMinutes + " 分钟（追加式）：") -ForegroundColor Green
    foreach ($p in $Paths) { Write-Host ('   ' + (Normalize-Path $p)) }
  } finally { Exit-CoordLock }
}

function Invoke-Release {
  if (-not $Session) { throw 'release 需要 -Session' }
  Enter-CoordLock ("release by " + $Session)
  try {
    $live = Remove-ExpiredLeases
    $mine = @($live | Where-Object { $_.Session -eq $Session })
    $keep = @($live | Where-Object { $_.Session -ne $Session })
    Save-Leases $keep
    Write-Log ("RELEASE n=" + $mine.Count)
    Write-Host ("OK 已释放 " + $mine.Count + " 条租约（" + $Session + "）") -ForegroundColor Green
  } finally { Exit-CoordLock }
}

function Invoke-Commit {
  if (-not $Message) { throw 'commit 需要 -Message "提交说明"' }
  if ($Paths.Count -eq 0) { throw 'commit 需要 -Paths，只能提交你显式列出的路径' }
  if (-not $Session) { throw 'commit 需要 -Session（或设置环境变量 COORD_SESSION）' }

  Enter-CoordLock ("commit by " + $Session)
  try {
    $live = Remove-ExpiredLeases

    $preStaged = @(Get-GitLines @('diff', '--cached', '--name-only'))
    if ($preStaged.Count -gt 0) {
      Write-Host 'X 索引里已有暂存内容，拒绝提交（可能来自另一个会话）：' -ForegroundColor Red
      foreach ($p in $preStaged) { Write-Host ('   ' + $p) -ForegroundColor Red }
      Write-Host '  本工具不会替你 unstage 别人的东西。' -ForegroundColor Yellow
      Write-Log 'COMMIT-REJECT dirty-index'
      exit 4
    }

    $conflicts = New-Object System.Collections.ArrayList
    foreach ($p in $Paths) {
      foreach ($l in $live) {
        if ($l.Session -eq $Session) { continue }
        if (Test-ScopeOverlap -A $l.Scope -B $p) { [void]$conflicts.Add($p + "  正被 " + $l.Session + " 声明") }
      }
    }
    if ($conflicts.Count -gt 0 -and -not $Force) {
      Write-Host 'X 待提交路径与其它会话的租约重叠，拒绝提交：' -ForegroundColor Red
      foreach ($c in $conflicts) { Write-Host ('   ' + $c) -ForegroundColor Red }
      Write-Log 'COMMIT-REJECT scope-conflict'
      exit 3
    }

    # 自动追加认领：否则 pre-commit hook 会以「未认领」为由拦下这次提交，
    # 协调器与 hook 的口径必须一致。
    Add-MyLeases -NewPaths $Paths -Minutes $LeaseMinutes

    $addArgs = @('add', '--') + $Paths
    $r = Invoke-GitText $addArgs
    if ($r.Code -ne 0) { throw ('git add 失败：' + ($r.Out -join "`n")) }

    $staged = @(Get-GitLines @('diff', '--cached', '--name-only'))
    if ($staged.Count -eq 0) {
      Write-Host 'X 这些路径没有任何改动，无需提交。' -ForegroundColor Yellow
      Write-Log 'COMMIT-NOCHANGE'
      exit 5
    }
    $extra = New-Object System.Collections.ArrayList
    foreach ($s in $staged) {
      $okPath = $false
      foreach ($p in $Paths) { if (Test-ScopeMatch -Scope $p -Path $s) { $okPath = $true; break } }
      if (-not $okPath) { [void]$extra.Add($s) }
    }
    if ($extra.Count -gt 0) {
      Write-Host 'X 暂存区出现了未列出的路径，中止（未做任何提交）：' -ForegroundColor Red
      foreach ($e in $extra) { Write-Host ('   ' + $e) -ForegroundColor Red }
      Write-Log 'COMMIT-REJECT unexpected-staged'
      exit 4
    }

    if ($DryRun) {
      Write-Host '（DryRun）将提交以下路径：' -ForegroundColor Yellow
      foreach ($s in $staged) { Write-Host ('   ' + $s) }
      Invoke-GitText (@('restore', '--staged', '--') + $Paths) | Out-Null
      return
    }

    $cr = Invoke-GitText (@('commit', '-m', $Message))
    if ($cr.Code -ne 0) {
      Write-Host 'X git commit 失败：' -ForegroundColor Red
      foreach ($o in $cr.Out) { Write-Host ('   ' + $o) -ForegroundColor Red }
      Write-Log 'COMMIT-FAIL'
      exit 6
    }
    foreach ($o in $cr.Out) { Write-Host $o }
    Write-Log ("COMMIT ok paths=" + ($Paths -join ','))
    Write-Host ("OK 提交完成：" + $staged.Count + " 个路径") -ForegroundColor Green
    Write-Host '  下一步：push' -ForegroundColor Gray
  } finally { Exit-CoordLock }
}

function Invoke-Push {
  $branch = Get-CurrentBranch
  Enter-CoordLock ("push by " + $Session)
  try {
    Write-Host '-> 先 fetch，确认远端没有别人的新提交…' -ForegroundColor Gray
    $f = Invoke-GitText @('fetch', 'origin', '--prune')
    if ($f.Code -ne 0) {
      Write-Host 'X fetch 失败（网络或凭据问题），未推送任何东西：' -ForegroundColor Red
      foreach ($o in $f.Out) { Write-Host ('   ' + $o) -ForegroundColor Red }
      Write-Log 'PUSH-REJECT fetch-failed'
      exit 7
    }
    $div = Get-Divergence
    if ($div.Behind -gt 0) {
      Write-Host ("X 本地落后 " + $div.Behind + " 个提交，直接推送会被拒或造成历史分叉。") -ForegroundColor Red
      Write-Host '  请先 rebase：git rebase origin/main  然后重跑 push。' -ForegroundColor Yellow
      Write-Host '  绝不要用 git push --force 绕过。' -ForegroundColor Yellow
      Write-Log ("PUSH-REJECT behind=" + $div.Behind)
      exit 8
    }
    if ($div.Ahead -eq 0) {
      Write-Host 'OK 本地与远端一致，无需推送。' -ForegroundColor Green
      return
    }
    if ($DryRun) {
      Write-Host ("（DryRun）将推送 " + $div.Ahead + " 个提交到 origin/" + $branch) -ForegroundColor Yellow
      return
    }
    $r = Invoke-GitText @('push', 'origin', $branch)
    if ($r.Code -ne 0) {
      Write-Host 'X push 失败：' -ForegroundColor Red
      foreach ($o in $r.Out) { Write-Host ('   ' + $o) -ForegroundColor Red }
      Write-Log 'PUSH-FAIL'
      exit 9
    }
    foreach ($o in $r.Out) { Write-Host $o }
    Write-Log ("PUSH ok ahead=" + $div.Ahead)
    Write-Host ("OK 已推送 " + $div.Ahead + " 个提交到 origin/" + $branch) -ForegroundColor Green
  } finally { Exit-CoordLock }
}

function Invoke-Watch {
  $head = ((Get-GitLines @('rev-parse', 'HEAD')) | Select-Object -First 1)
  $dirty = Get-DirtyFiles
  $files = @()
  foreach ($d in $dirty) {
    $it = Get-Item -LiteralPath (Join-Path $Repo $d.Path) -ErrorAction SilentlyContinue
    $m = $null
    if ($it) { $m = $it.LastWriteTime.ToString('o') }
    $files += [pscustomobject]@{ Path = $d.Path; Code = $d.Code; MTime = $m }
  }
  $snap = [pscustomobject]@{ Session = $Session; Time = (Get-Date).ToString('o'); Head = $head; Files = $files }

  $prev = $null
  if (Test-Path -LiteralPath $SnapFile) {
    try { $prev = [System.IO.File]::ReadAllText($SnapFile, [Text.Encoding]::UTF8) | ConvertFrom-Json } catch { $prev = $null }
  }
  [System.IO.File]::WriteAllText($SnapFile, ($snap | ConvertTo-Json -Depth 6), $Utf8NoBom)

  if (-not $prev) {
    Write-Host 'OK 已记录基线快照（再次运行 watch 即可看到变化）。' -ForegroundColor Green
    return
  }
  Write-Host ("基线：" + $prev.Time + "   HEAD " + $prev.Head.Substring(0, 8)) -ForegroundColor Gray
  $changes = New-Object System.Collections.ArrayList
  if ($prev.Head -ne $head) {
    $by = ''
    if ($prev.Session -and $prev.Session -ne $Session) { $by = "（快照由 " + $prev.Session + " 记录）" }
    [void]$changes.Add("HEAD 变化：" + $prev.Head.Substring(0, 8) + " -> " + $head.Substring(0, 8) + " " + $by)
  }
  $prevMap = @{}
  foreach ($f in $prev.Files) { $prevMap[$f.Path] = $f }
  $curMap = @{}
  foreach ($f in $files) {
    $curMap[$f.Path] = $f
    if (-not $prevMap.ContainsKey($f.Path)) {
      [void]$changes.Add("新增改动：" + $f.Code + " " + $f.Path)
    } elseif ($prevMap[$f.Path].MTime -ne $f.MTime) {
      [void]$changes.Add("被再次改写：" + $f.Path)
    }
  }
  foreach ($k in $prevMap.Keys) { if (-not $curMap.ContainsKey($k)) { [void]$changes.Add("改动已被提交或撤销：" + $k) } }

  if ($changes.Count -eq 0) {
    Write-Host 'OK 自上次快照以来没有变化。' -ForegroundColor Green
  } else {
    Write-Host ("自上次快照以来 " + $changes.Count + " 处变化：") -ForegroundColor Cyan
    foreach ($c in $changes) { Write-Host ('   ' + $c) }
  }
}

function Invoke-Selftest {
  Write-Host '--- 自检 ---' -ForegroundColor Cyan
  Write-Host ("仓库可读   : " + (Test-Path -LiteralPath (Join-Path $Repo 'index.html')))
  $g = Invoke-GitText @('--version')
  Write-Host ("git 版本   : " + ($g.Out -join ' '))
  Write-Host ("状态目录   : " + $StateDir)
  Write-Host ("活跃租约   : " + @(Get-LiveLeases).Count)
  if (Test-Path -LiteralPath $LockFile) { Write-Host '锁状态     : 占用' -ForegroundColor Yellow } else { Write-Host '锁状态     : 空闲' }
  $hooks = Join-Path $Repo '.git\hooks'
  foreach ($h in @('pre-push', 'pre-commit')) {
    $p = Join-Path $hooks $h
    if (Test-Path -LiteralPath $p) { Write-Host ("hook " + $h.PadRight(11) + ": 已安装") -ForegroundColor Green }
    else { Write-Host ("hook " + $h.PadRight(11) + ": 缺失") -ForegroundColor Yellow }
  }
  Write-Host '--- 自检结束 ---' -ForegroundColor Cyan
}

switch ($Action.ToLower()) {
  'status'   { Show-Status }
  'claim'    { Invoke-Claim }
  'release'  { Invoke-Release }
  'commit'   { Invoke-Commit }
  'push'     { Invoke-Push }
  'watch'    { Invoke-Watch }
  'selftest' { Invoke-Selftest }
  default {
    Write-Host ("未知动作：" + $Action) -ForegroundColor Red
    Write-Host '可用：status | claim | release | commit | push | watch | selftest' -ForegroundColor Yellow
    exit 2
  }
}