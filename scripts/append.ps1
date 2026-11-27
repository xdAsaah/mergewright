# 往 JSONL 台账追加一条记录
#
#   .\append.ps1 -File state/prs.jsonl -Json '{"ts":"...","project":"...","pr":419}'
#   '{"a":1}' | .\append.ps1 -File state/scans.jsonl
#
# 只追加，不改已有行。写完回读最后一行校验，防止写坏。
# 注意：本文件必须保存为 UTF-8 带 BOM，否则 PowerShell 5.1 会把中文读成乱码。

param(
  [Parameter(Mandatory = $true)][string]$File,
  [string]$Json
)

$ErrorActionPreference = 'Stop'
$utf8 = New-Object Text.UTF8Encoding($false)

if (-not $Json) { $Json = $input | Out-String }
$Json = $Json.Trim()
if (-not $Json) { Write-Error "没有内容可追加"; exit 1 }

try { $obj = $Json | ConvertFrom-Json } catch { Write-Error "不是合法 JSON: $($_.Exception.Message)"; exit 1 }
if ($obj -isnot [pscustomobject]) { Write-Error "需要一个 JSON 对象，不是数组或标量"; exit 1 }
if (-not $obj.ts) { Write-Warning "缺少 ts 字段，建议补上 ISO 时间戳" }

$oneLine = ($Json -replace '\r?\n', ' ')

# 绝对路径（Join-Path 遇到绝对路径会拼错，统一用 GetFullPath 解析）
$full = [IO.Path]::GetFullPath($File)
$dir = [IO.Path]::GetDirectoryName($full)
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

$existing = if (Test-Path $full) { [IO.File]::ReadAllText($full, $utf8) } else { "" }
$prefix = if ($existing.Length -gt 0 -and -not $existing.EndsWith("`n")) { "`n" } else { "" }
[IO.File]::AppendAllText($full, ($prefix + $oneLine + "`n"), $utf8)

# 回读校验：按 UTF-8 读最后一行。必须用 @() 包住——只有一行时管道返回的是字符串，
# 直接取 [-1] 会拿到最后一个字符。
$lines = @([IO.File]::ReadAllLines($full, $utf8) | Where-Object { $_.Trim() })
if ($lines.Count -eq 0) { Write-Error "写入后文件是空的，请检查 $File"; exit 1 }
$last = $lines[$lines.Count - 1]
try { $null = $last | ConvertFrom-Json } catch { Write-Error "写入后最后一行不是合法 JSON，请检查 $File"; exit 1 }

"appended -> $File"
$last
