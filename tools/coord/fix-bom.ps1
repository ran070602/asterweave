# fix-bom.ps1 -- Ensure UTF-8 BOM on PowerShell scripts that contain non-ASCII text.
#
# WHY: This machine runs Windows PowerShell 5.1 (Desktop). 5.1 decodes a .ps1 file
# WITHOUT a BOM using the system ANSI codepage (GBK here), so any Chinese string
# literal in the script becomes mojibake and the script fails to parse.
# Files WITH a UTF-8 BOM are decoded correctly.
#
# NOTE: This file is deliberately ASCII-only so that it works even if the BOM is lost.
#
# Usage:
#   powershell -NoProfile -File .workbuddy\coord\fix-bom.ps1
#   powershell -NoProfile -File .workbuddy\coord\fix-bom.ps1 -Check   # report only

[CmdletBinding()]
param(
  [string[]]$Files,
  [switch]$Check
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Files -or $Files.Count -eq 0) {
  # 自动发现本目录下所有 .ps1，避免新脚本被漏掉（曾经写死清单漏过一次）
  $Files = @(Get-ChildItem -LiteralPath $PSScriptRoot -Filter '*.ps1' -File -ErrorAction SilentlyContinue |
             ForEach-Object { $_.FullName })
}

$changed = 0
$ok = 0
foreach ($f in $Files) {
  if (-not (Test-Path -LiteralPath $f)) { Write-Host ("MISSING  " + $f); continue }
  $b = [System.IO.File]::ReadAllBytes($f)
  $hasBom = ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF)
  if ($hasBom) { Write-Host ("OK       " + $f); $ok++; continue }
  if ($Check) { Write-Host ("NO-BOM   " + $f); continue }
  $text = [System.Text.Encoding]::UTF8.GetString($b)
  $enc = New-Object System.Text.UTF8Encoding($true)
  [System.IO.File]::WriteAllBytes($f, $enc.GetPreamble() + $enc.GetBytes($text))
  Write-Host ("FIXED    " + $f)
  $changed++
}
Write-Host ("-- ok=" + $ok + " fixed=" + $changed)
if ($Check -and $changed -eq 0 -and $ok -lt $Files.Count) { exit 1 }
exit 0
