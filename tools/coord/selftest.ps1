# Asterweave 协调器自检：在隔离的临时仓库里验证 claim / commit / push / hook 行为。
# 不会触碰 D:\Asterweave 的任何 git 状态。
$ErrorActionPreference = 'Continue'
$src     = 'D:\Asterweave'
$root    = 'D:\Asterweave-coord-selftest'
$pass = 0; $fail = 0
$results = New-Object System.Collections.ArrayList

function Check {
  param([string]$Name, [bool]$Ok, [string]$Detail = '')
  if ($Ok) { $script:pass++; Write-Host ("  PASS  {0}" -f $Name) -ForegroundColor Green }
  else     { $script:fail++; Write-Host ("  FAIL  {0}   {1}" -f $Name, $Detail) -ForegroundColor Red }
  [void]$script:results.Add([pscustomobject]@{ Name = $Name; Ok = $Ok; Detail = $Detail })
}

if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
New-Item -ItemType Directory -Force -Path $root | Out-Null

$bare  = Join-Path $root 'origin.git'
$work  = Join-Path $root 'work'
$work2 = Join-Path $root 'work2'

& git init --bare -q $bare | Out-Null
& git -C $bare symbolic-ref HEAD refs/heads/main | Out-Null
& git clone -q $bare $work 2>&1 | Out-Null
& git -C $work config user.email 'selftest@local'
& git -C $work config user.name  'selftest'
& git -C $work config commit.gpgsign false
& git -C $work checkout -q -b main 2>&1 | Out-Null

# 复刻真实仓库的 .gitignore 约定
Set-Content -LiteralPath (Join-Path $work '.gitignore') -Value "tools/coord/`n.scratch/`n" -Encoding utf8
New-Item -ItemType Directory -Force -Path (Join-Path $work 'game') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $work 'docs') | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $work 'dist') | Out-Null
Set-Content -LiteralPath (Join-Path $work 'game\index.html') -Value 'v1' -Encoding utf8
Set-Content -LiteralPath (Join-Path $work 'docs\SPEC.md')    -Value 'v1' -Encoding utf8
Set-Content -LiteralPath (Join-Path $work 'dist\app.js')     -Value 'v1' -Encoding utf8
& git -C $work add -A | Out-Null
& git -C $work commit -q -m 'init' | Out-Null
& git -C $work push -q -u origin main 2>&1 | Out-Null

# 安装协调器与 hook
$cd = Join-Path $work 'tools\coord'
New-Item -ItemType Directory -Force -Path $cd | Out-Null
Copy-Item -LiteralPath (Join-Path $src 'tools\coord\coord.ps1') -Destination (Join-Path $cd 'coord.ps1') -Force
# hook 的权威源在 tools\coord\hooks（受版本控制），不是 .git\hooks 里的那份副本。
# 测试仓库不设 core.hooksPath，所以放进它的 .git\hooks 即可生效。
Copy-Item -LiteralPath (Join-Path $src 'tools\coord\hooks\pre-push')   -Destination (Join-Path $work '.git\hooks\pre-push')   -Force
Copy-Item -LiteralPath (Join-Path $src 'tools\coord\hooks\pre-commit') -Destination (Join-Path $work '.git\hooks\pre-commit') -Force

$script:Coord = Join-Path $cd 'coord.ps1'

function RunCoord {
  param([string[]]$A, [string]$Sess, [string]$Repo = $work)
  if ($Sess) { $env:COORD_SESSION = $Sess } else { Remove-Item Env:COORD_SESSION -ErrorAction SilentlyContinue }
  $all = @($A) + @('-RepoRoot', $Repo)
  $out = & powershell -NoProfile -File $script:Coord @all 2>&1
  $code = $LASTEXITCODE
  Remove-Item Env:COORD_SESSION -ErrorAction SilentlyContinue
  return [pscustomobject]@{ Code = $code; Text = ($out -join "`n") }
}

function RunGit {
  param([string[]]$A, [string]$Repo = $work, [string]$Sess)
  if ($Sess) { $env:COORD_SESSION = $Sess } else { Remove-Item Env:COORD_SESSION -ErrorAction SilentlyContinue }
  $out = & git -C $Repo @A 2>&1
  $code = $LASTEXITCODE
  Remove-Item Env:COORD_SESSION -ErrorAction SilentlyContinue
  return [pscustomobject]@{ Code = $code; Text = ($out -join "`n") }
}

Write-Host ''
Write-Host '=== 1. status / selftest 基本可用 ===' -ForegroundColor Cyan
$r = RunCoord @('status') 'selftest'
Check 'status 退出码 0' ($r.Code -eq 0) $r.Text
Check 'status 报告仓库路径' ($r.Text -match 'Asterweave-coord-selftest')

$r = RunCoord @('selftest') 'selftest'
Check 'selftest 识别两个 hook 已安装' (($r.Text -match 'pre-push\s*:\s*已安装') -and ($r.Text -match 'pre-commit\s*:\s*已安装')) $r.Text

Write-Host ''
Write-Host '=== 2. 作用域租约：重叠必须被拒 ===' -ForegroundColor Cyan
$r = RunCoord @('claim', '-Session', 'A', '-Paths', 'game/index.html') 'A'
Check 'A 认领 game/index.html 成功' ($r.Code -eq 0) $r.Text

$r = RunCoord @('claim', '-Session', 'B', '-Paths', 'game/index.html') 'B'
Check 'B 认领同一文件被拒（退出码 3）' ($r.Code -eq 3) ("code=$($r.Code) $($r.Text)")

$r = RunCoord @('claim', '-Session', 'B', '-Paths', 'game/') 'B'
Check 'B 认领同目录被拒（前缀匹配生效）' ($r.Code -eq 3) ("code=$($r.Code) $($r.Text)")

$r = RunCoord @('claim', '-Session', 'B', '-Paths', 'docs/') 'B'
Check 'B 认领不相交路径成功' ($r.Code -eq 0) $r.Text

$r = RunCoord @('status') 'selftest'
Check 'status 同时显示 A 与 B 的租约' (($r.Text -match '\bA\b') -and ($r.Text -match '\bB\b') -and ($r.Text -match '剩余'))

Write-Host ''
Write-Host '=== 3. commit：只提交显式路径 ===' -ForegroundColor Cyan
Set-Content -LiteralPath (Join-Path $work 'game\index.html') -Value 'v2-A' -Encoding utf8
Set-Content -LiteralPath (Join-Path $work 'docs\SPEC.md')    -Value 'v2-B' -Encoding utf8

$r = RunCoord @('commit', '-Session', 'A', '-Message', 'A: game only', '-Paths', 'game/index.html') 'A'
Check 'A 提交成功' ($r.Code -eq 0) $r.Text
# 必须用 @() 包住：只匹配到一项时 PowerShell 会退化成字符串，
# 而字符串的 [0] 取到的是首字符，断言会假失败。
$files = @((RunGit @('show', '--name-only', '--format=', 'HEAD')).Text -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
Check 'A 的提交只含 game/index.html' (($files.Count -eq 1) -and ($files[0] -eq 'game/index.html')) ($files -join ',')
$st = (RunGit @('status', '--porcelain')).Text
Check 'B 的 docs/SPEC.md 仍是未提交状态（没被卷走）' ($st -match 'docs/SPEC.md')

Write-Host ''
Write-Host '=== 4. commit：跨会话作用域冲突必须被拒 ===' -ForegroundColor Cyan
Set-Content -LiteralPath (Join-Path $work 'dist\app.js') -Value 'v2' -Encoding utf8
$r = RunCoord @('commit', '-Session', 'B', '-Message', 'B 抢 dist', '-Paths', 'dist/app.js') 'B'
Check 'B 提交未被任何人声明的 dist/ 成功' ($r.Code -eq 0) $r.Text

Set-Content -LiteralPath (Join-Path $work 'game\index.html') -Value 'v3' -Encoding utf8
$r = RunCoord @('commit', '-Session', 'B', '-Message', 'B 越界改 game', '-Paths', 'game/index.html') 'B'
Check 'B 提交 A 已声明的路径被拒（退出码 3）' ($r.Code -eq 3) ("code=$($r.Code) $($r.Text)")

Write-Host ''
Write-Host '=== 5. commit：索引不干净时必须拒绝 ===' -ForegroundColor Cyan
& git -C $work add -- docs/SPEC.md | Out-Null
Set-Content -LiteralPath (Join-Path $work 'docs\SPEC.md') -Value 'v3-B' -Encoding utf8
$r = RunCoord @('commit', '-Session', 'B', '-Message', 'B 带着脏索引提交', '-Paths', 'docs/SPEC.md') 'B'
Check '脏索引时拒绝提交（退出码 4）' ($r.Code -eq 4) ("code=$($r.Code) $($r.Text)")
& git -C $work reset -q | Out-Null

Write-Host ''
Write-Host '=== 6. pre-commit hook 拦截 git add -A ===' -ForegroundColor Cyan
Set-Content -LiteralPath (Join-Path $work 'docs\SPEC.md') -Value 'v4-B' -Encoding utf8
Set-Content -LiteralPath (Join-Path $work 'game\index.html') -Value 'v4-他人' -Encoding utf8
& git -C $work add -A | Out-Null
$r = RunGit @('commit', '-m', 'B 全量暂存') $work 'B'
Check 'pre-commit 拦住含他人路径的全量提交' ($r.Code -ne 0 -and $r.Text -match '拒绝提交') ("code=$($r.Code) $($r.Text)")
Check 'hook 指明冲突方是 A' ($r.Text -match '会话 A') $r.Text

$env:COORD_BYPASS = '1'
$r = RunGit @('commit', '-m', 'B 显式绕过') $work 'B'
Remove-Item Env:COORD_BYPASS -ErrorAction SilentlyContinue
Check 'COORD_BYPASS=1 可显式绕过' ($r.Code -eq 0) ("code=$($r.Code) $($r.Text)")
& git -C $work reset -q --soft HEAD~1 | Out-Null
& git -C $work reset -q | Out-Null

Write-Host ''
Write-Host '=== 6b. 回归：租约文件为 CRLF 时冲突检测仍必须生效 ===' -ForegroundColor Cyan
# 这条守的是一个真实踩过的坑：CRLF 会让 scope 尾部带 \r，路径匹配静默失败。
$leasePath = Join-Path $work '.git\asterweave-coord\leases.tsv'
$lf = [System.IO.File]::ReadAllText($leasePath, [System.Text.Encoding]::UTF8)
$normalized = ($lf -replace "`r`n", "`n")
$crlfText = ($normalized -replace "`n", "`r`n")
[System.IO.File]::WriteAllText($leasePath, $crlfText, (New-Object System.Text.UTF8Encoding($false)))
$crlf = [System.IO.File]::ReadAllText($leasePath, [System.Text.Encoding]::UTF8)
Check '测试前提：租约文件确为 CRLF' ($crlf -match "`r`n")
& git -C $work add -A | Out-Null
$r = RunGit @('commit', '-m', 'CRLF 回归') $work 'B'
Check 'CRLF 租约下仍能识别冲突方 A' ($r.Code -ne 0 -and $r.Text -match '会话 A') ("code=$($r.Code) $($r.Text)")
Check 'CRLF 下走的是「与他方冲突」分支而非「未认领」分支' ($r.Text -match '正被其它会话修改') $r.Text
& git -C $work reset -q | Out-Null
# 还原为 LF，继续后续用例
[System.IO.File]::WriteAllText($leasePath, ($crlf -replace "`r`n", "`n"), (New-Object System.Text.UTF8Encoding($false)))

Write-Host ''
Write-Host '=== 7. 未设置 COORD_SESSION 时 hook 完全不干预 ===' -ForegroundColor Cyan
Set-Content -LiteralPath (Join-Path $work 'docs\SPEC.md') -Value 'v5-B' -Encoding utf8
& git -C $work add -A | Out-Null
$r = RunGit @('commit', '-m', '未启用协调器的会话提交') $work
Check '无 COORD_SESSION 时提交放行' ($r.Code -eq 0) ("code=$($r.Code) $($r.Text)")

Write-Host ''
Write-Host '=== 8. push：落后时必须拒绝 ===' -ForegroundColor Cyan
$r = RunCoord @('push', '-Session', 'A') 'A'
Check 'A 正常推送成功' ($r.Code -eq 0) $r.Text

# 回归：rev-list --left-right --count 的左右列含义容易读反，
# 读反会让「领先」被当成「落后」，从而拦下每一次合法推送。
Set-Content -LiteralPath (Join-Path $work 'dist\app.js') -Value 'ahead-probe' -Encoding utf8
$rc = RunCoord @('commit', '-Session', 'B', '-Message', 'ahead probe', '-Paths', 'dist/app.js') 'B'
Check '探针提交成功（一并验证提交时自动追加认领）' ($rc.Code -eq 0) $rc.Text
$r = RunCoord @('status') 'B'
Check 'status 把领先 1 报成「领先 1 / 落后 0」' ($r.Text -match '领先 1 / 落后 0') ($r.Text -replace "`r?`n", ' | ')
& git -C $work reset -q --hard origin/main | Out-Null

# 模拟另一个会话（work2）先推了一个提交
& git clone -q $bare $work2 2>&1 | Out-Null
& git -C $work2 config user.email 'other@local'
& git -C $work2 config user.name 'other'
Set-Content -LiteralPath (Join-Path $work2 'docs\OTHER.md') -Value 'other' -Encoding utf8
& git -C $work2 add -A | Out-Null
& git -C $work2 commit -q -m 'other session commit' | Out-Null
& git -C $work2 push -q origin main 2>&1 | Out-Null

Set-Content -LiteralPath (Join-Path $work 'docs\SPEC.md') -Value 'v6-B' -Encoding utf8
$r = RunCoord @('commit', '-Session', 'B', '-Message', 'B 落后时提交', '-Paths', 'docs/SPEC.md') 'B'
Check '落后状态下仍可本地提交' ($r.Code -eq 0) $r.Text
$r = RunCoord @('push', '-Session', 'B') 'B'
Check '落后 1 个提交时拒绝推送（退出码 8）' ($r.Code -eq 8) ("code=$($r.Code) $($r.Text)")
Check '拒绝信息给出 rebase 指引' ($r.Text -match 'rebase origin/main') $r.Text

Write-Host ''
Write-Host '=== 9. pre-push hook 拦截非快进推送 ===' -ForegroundColor Cyan
& git -C $work fetch -q origin | Out-Null
$r = RunGit @('push', '--force', 'origin', 'main') $work
Check 'pre-push 拦住 force push' ($r.Code -ne 0 -and $r.Text -match '非快进推送') ("code=$($r.Code) $($r.Text)")

Write-Host ''
Write-Host '=== 10. rebase 后可以正常推送 ===' -ForegroundColor Cyan
& git -C $work rebase -q origin/main 2>&1 | Out-Null
$r = RunCoord @('push', '-Session', 'B') 'B'
Check 'rebase 后推送成功（历史未丢）' ($r.Code -eq 0) $r.Text
$log = (RunGit @('log', '--oneline', '-6')).Text
Check '远端历史里 other 的提交仍在' ($log -match 'other session commit') $log

Write-Host ''
Write-Host '=== 11. release 释放租约 ===' -ForegroundColor Cyan
$r = RunCoord @('release', '-Session', 'A') 'A'
Check 'release 成功' ($r.Code -eq 0) $r.Text
$r = RunCoord @('claim', '-Session', 'C', '-Paths', 'game/index.html') 'C'
Check 'A 释放后 C 可以认领该文件' ($r.Code -eq 0) $r.Text

Write-Host ''
Write-Host '=== 12. pre-push 护栏真值表（含 CR 回归） ===' -ForegroundColor Cyan
# 守两个真实踩过的坑：
#   a) 字段尾部混入 CR 会让 sha 无法解析，从而把每一次合法推送都误拦成「非快进」；
#   b) 退出码必须在管道不被截断的情况下读取，否则 PS 5.1 会记成 -1。
$sh = @('C:\Program Files\Git\bin\sh.exe', 'C:\Program Files\Git\bin\bash.exe') |
      Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $sh) { $sh = 'sh' }
$hookPath = Join-Path $work '.git\hooks\pre-push'
$headSha = (RunGit @('rev-parse', 'HEAD')).Text.Trim()
$ancSha  = (RunGit @('rev-parse', 'HEAD~1')).Text.Trim()
$tree    = (RunGit @('rev-parse', 'HEAD^{tree}')).Text.Trim()
$zeroSha = '0000000000000000000000000000000000000000'
# 造一个不在 HEAD 历史里的提交，模拟「远端有别人提交」
$dangling = ("probe`n" | & git -C $work commit-tree $tree 2>&1 | Select-Object -First 1)
$dangling = "$dangling".Trim()

function Test-PrePush {
  param([string]$Line, [int]$Expect)
  # hook 里的 git merge-base 是按「当前目录」解析 sha 的，
  # 所以必须在被隔离的测试仓库里执行，否则会拿测试仓库的 sha 去真实仓库里找。
  Push-Location $work
  try {
    $out = $Line | & $sh $hookPath origin 'https://example.invalid/x.git' 2>&1   # 先赋值，不截断管道
    $code = $LASTEXITCODE
  } finally { Pop-Location }
  return [pscustomobject]@{ Code = $code; Ok = ($code -eq $Expect); Text = ($out -join ' ') }
}

$c1 = Test-PrePush -Line "refs/heads/main $headSha refs/heads/main $ancSha" -Expect 0
Check '快进推送放行（exit 0）' $c1.Ok ("code=$($c1.Code) $($c1.Text)")
$c2 = Test-PrePush -Line "refs/heads/main $headSha refs/heads/main $dangling" -Expect 1
Check '非快进推送拦下（exit 1）' ($c2.Ok -and $c2.Text -match '非快进推送') ("code=$($c2.Code) $($c2.Text)")
# 同一行数据后面加 CR，模拟工具包装/跨平台管道带来的回车
$c3 = Test-PrePush -Line "refs/heads/main $headSha refs/heads/main $ancSha`r" -Expect 0
Check 'CR 回归：带 CR 的快进推送仍然放行' $c3.Ok ("code=$($c3.Code) $($c3.Text)")
$c4 = Test-PrePush -Line "refs/heads/main $zeroSha refs/heads/main $headSha" -Expect 1
Check '删除远端分支拦下（exit 1）' ($c4.Ok -and $c4.Text -match '拒绝删除远端分支') ("code=$($c4.Code) $($c4.Text)")
$c5 = Test-PrePush -Line "refs/heads/session/new $headSha refs/heads/session/new $zeroSha" -Expect 0
Check '新分支放行（exit 0）' $c5.Ok ("code=$($c5.Code) $($c5.Text)")

Write-Host ''
Write-Host '===============================' -ForegroundColor Cyan
Write-Host ("自检结果：PASS {0} / FAIL {1}" -f $pass, $fail) -ForegroundColor $(if ($fail -eq 0) { 'Green' } else { 'Red' })
Write-Host '===============================' -ForegroundColor Cyan
if ($fail -gt 0) {
  Write-Host ''
  Write-Host '失败项：' -ForegroundColor Red
  $results | Where-Object { -not $_.Ok } | ForEach-Object { Write-Host (" - {0}`n   {1}" -f $_.Name, $_.Detail) -ForegroundColor Red }
  exit 1
}
exit 0
