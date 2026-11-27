# 查某仓库的 PR/MR 状态与通道活性
#
#   .\pr-status.ps1 -Repo owner/repo -Author 你的用户名
#   .\pr-status.ps1 -Repo group/project -Platform gitlab -Site gitlab.example.com -Author you
#
# 现算，不依赖台账里手写的数字：外部合并率、open 积压、最近一次合并。
# 凭据从 Windows 凭据管理器取（git credential fill），不落盘、不回显。
# 注意：本文件必须保存为 UTF-8 带 BOM，否则 PowerShell 5.1 会把中文读成乱码。

param(
  [Parameter(Mandatory = $true)][string]$Repo,
  [string]$Author = "",
  [ValidateSet('github', 'gitlab')][string]$Platform = 'github',
  [string]$Site = ''
)

$ErrorActionPreference = 'Stop'
$env:GCM_INTERACTIVE = 'Never'
$utf8 = New-Object Text.UTF8Encoding($false)

# PowerShell 5.1 把字符串管道给原生程序会丢内容（git 报 missing protocol field），
# 所以写临时文件 + cmd 重定向。
function Get-Token([string]$hostName) {
  $q = Join-Path $env:TEMP ("cred-" + [guid]::NewGuid().ToString('N') + ".txt")
  [IO.File]::WriteAllText($q, "protocol=https`nhost=$hostName`n", $utf8)
  try { cmd /c "git credential fill < `"$q`"" 2>&1 } finally { Remove-Item $q -Force -ErrorAction SilentlyContinue }
}

# 注意：$Host 是 PowerShell 保留变量，参数名必须用别的（这里用 -Site）
if (-not $Site) { $Site = if ($Platform -eq 'github') { 'github.com' } else { 'gitlab.com' } }
$cred = Get-Token $Site
$token = (($cred | Select-String '^password=') -replace '^password=', '')
if (-not $token) { Write-Error "拿不到 $Site 的 token：先 git credential 登录一次"; exit 1 }

# PS 5.1 的 Invoke-RestMethod 把 ISO 时间戳返回成字符串，统一转成 DateTime
function As-Time($value) {
  if ($value -is [datetime]) { return $value }
  if (-not $value) { return $null }
  try { return [datetime]::Parse($value, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AdjustToUniversal) } catch { return $null }
}

function Days-Since($value) {
  $t = As-Time $value
  if (-not $t) { return $null }
  return [math]::Round(((Get-Date).ToUniversalTime() - $t).TotalDays, 1)
}

# ---------- 平台适配 ----------
$script:Api = if ($Platform -eq 'github') { 'https://api.github.com' } else { "https://$Site/api/v4" }
$script:H = if ($Platform -eq 'github') {
  @{ Authorization = "Bearer $token"; Accept = 'application/vnd.github+json'; 'User-Agent' = 'trae' }
} else {
  @{ 'PRIVATE-TOKEN' = $token; 'User-Agent' = 'trae' }
}

function Get-Json([string]$uri) {
  try { Invoke-RestMethod -Uri $uri -Headers $script:H }
  catch { Write-Warning "请求失败 $uri : $($_.Exception.Message)"; $null }
}

function Convert-Pull($raw) {
  if ($Platform -eq 'github') {
    [pscustomobject]@{
      Number = $raw.number; Title = $raw.title; Author = $raw.user.login
      Created = $raw.created_at; Merged = $raw.merged_at; State = $raw.state
      Assoc = $raw.author_association; IsBot = ($raw.user.type -eq 'Bot')
    }
  } else {
    [pscustomobject]@{
      Number = $raw.iid; Title = $raw.title; Author = $raw.author.username
      Created = $raw.created_at; Merged = $(if ($raw.state -eq 'merged') { $raw.merged_at } else { $null })
      State = $(if ($raw.state -eq 'merged') { 'closed' } else { $raw.state })
      Assoc = $(if ($raw.author.username -eq $Author) { 'SELF' } else { 'OTHER' })
      IsBot = ($raw.author.username -match '^(dependabot|renovate|bot)')
    }
  }
}

Write-Output "=== $Platform : $Repo ==="

# 仓库活跃度
if ($Platform -eq 'github') {
  $info = Get-Json "$script:Api/repos/$Repo"
  if ($info) { "stars=$($info.stargazers_count)  pushed=$($info.pushed_at)  open_issues(incl PR)=$($info.open_issues_count)" }
} else {
  $info = Get-Json "$script:Api/projects/$([uri]::EscapeDataString($Repo))"
  if ($info) { "stars=$($info.star_count)  last_activity=$($info.last_activity_at)" }
}

# open PR
$openRaw = if ($Platform -eq 'github') { Get-Json "$script:Api/repos/$Repo/pulls?state=open&per_page=100" }
           else { Get-Json "$script:Api/projects/$([uri]::EscapeDataString($Repo))/merge_requests?state=opened&per_page=100" }
$open = @($openRaw | Where-Object { $_ } | ForEach-Object { Convert-Pull $_ })
"open: $($open.Count)"
if ($open.Count -gt 0) {
  $oldest = ($open | Sort-Object { As-Time $_.Created } | Select-Object -First 1)
  "  oldest: #$($oldest.Number) 等了 $(Days-Since $oldest.Created) 天 ($($oldest.Title))"
  foreach ($p in ($open | Sort-Object { As-Time $_.Created })) {
    $cm = if ($Platform -eq 'github') { Get-Json "$script:Api/repos/$Repo/issues/$($p.Number)/comments" }
          else { Get-Json "$script:Api/projects/$([uri]::EscapeDataString($Repo))/merge_requests/$($p.Number)/notes" }
    $others = @($cm | Where-Object { $_ -and $_.user.login -ne $p.Author })
    "  #$($p.Number) [$($p.Author)] 他人评论 $($others.Count) 条  $($p.Title)"
  }
}

# 最近 20 个已关闭
$closedRaw = if ($Platform -eq 'github') { Get-Json "$script:Api/repos/$Repo/pulls?state=closed&per_page=20&sort=updated&direction=desc" }
             else { Get-Json "$script:Api/projects/$([uri]::EscapeDataString($Repo))/merge_requests?state=closed&per_page=20&order_by=updated_at" }
$closed = @($closedRaw | Where-Object { $_ } | ForEach-Object { Convert-Pull $_ })
if ($closed.Count -gt 0) {
  $human = @($closed | Where-Object { -not $_.IsBot })
  $merged = @($human | Where-Object { $_.Merged })
  $external = if ($Platform -eq 'github') {
    @($merged | Where-Object { $_.Assoc -notin @('MEMBER', 'OWNER', 'COLLABORATOR') })
  } else {
    @($merged | Where-Object { $_.Assoc -eq 'OTHER' })
  }
  "近 20 个已关闭（剔 bot）: $($human.Count)  合并 $($merged.Count)  外部作者合并 $($external.Count)"
  if ($merged.Count -gt 0) {
    $last = ($merged | Sort-Object { As-Time $_.Merged } -Descending | Select-Object -First 1)
    "  最近合并: #$($last.Number) at $($last.Merged)"
  }
  $authors = @($external | ForEach-Object { $_.Author } | Sort-Object -Unique)
  "  外部合并作者: $($authors.Count) 人 -> $($authors -join ', ')"
}

# 指定作者的全部 PR
if ($Author) {
  if ($Platform -eq 'github') {
    $q = Get-Json "$script:Api/search/issues?q=repo:$Repo+author:$Author+type:pr&per_page=100"
    $items = @($q.items | ForEach-Object {
      [pscustomobject]@{ Number = $_.number; Title = $_.title; Merged = $_.pull_request.merged_at; State = $_.state }
    })
    $total = $q.total_count
  } else {
    $raw = Get-Json "$script:Api/projects/$([uri]::EscapeDataString($Repo))/merge_requests?author_username=$Author&per_page=100"
    $items = @($raw | Where-Object { $_ } | ForEach-Object {
      [pscustomobject]@{ Number = $_.iid; Title = $_.title; Merged = $(if ($_.state -eq 'merged') { $_.merged_at } else { $null }); State = $_.state }
    })
    $total = $items.Count
  }
  $m = @($items | Where-Object { $_.Merged })
  $c = @($items | Where-Object { -not $_.Merged -and $_.State -eq 'closed' })
  $o = @($items | Where-Object { $_.State -eq 'open' -or $_.State -eq 'opened' })
  ""
  "=== $Author 的 PR ==="
  "总数 $total  合并 $($m.Count)  关闭未合并 $($c.Count)  在审 $($o.Count)"
  $items | Sort-Object Number | ForEach-Object {
    $state = if ($_.Merged) { "merged $($_.Merged)" } else { $_.State }
    "  #$($_.Number) [$state] $($_.Title)"
  }
}
