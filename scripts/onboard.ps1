# 进场采集：读本地仓库，推导出 conventions 里能自动填的项
#
#   .\onboard.ps1 -Path D:\code\some-repo
#
# 只做推导（[推导]），不做观察（那需要调 API），也不问用户。
# 输出是可以直接粘进 conventions/<项目>.md 的 markdown 片段。
# 注意：本文件必须保存为 UTF-8 带 BOM，否则 PowerShell 5.1 会把中文读成乱码。

param(
  [Parameter(Mandatory = $true)][string]$Path
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $Path)) { Write-Error "路径不存在：$Path"; exit 1 }
$root = (Resolve-Path $Path).Path
Push-Location $root
try {

# EAP=Stop 下原生程序的 stderr 会变成终止错误（比如没有 origin 时 git 报错），
# 所以所有 git 调用都走这个包装，失败返回空。
# 注意：函数名不能叫 Git —— PowerShell 函数名大小写不敏感，会和 git.exe 撞名导致无限递归。
function Invoke-Git([string[]]$GitArgs) {
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & git @GitArgs 2>$null } finally { $ErrorActionPreference = $prev }
}

"# 采集结果：$(Split-Path $root -Leaf)"
""
"> 采集时间 $(Get-Date -Format 'yyyy-MM-dd HH:mm')，路径 $root"
"> 全部标 `[推导]`。观察项和维护者政策需要跑 pr-status.ps1 后再填。"

# ---------- 1. 平台与仓库 ----------
""
"## 1. 托管与提交"
""
"| 项 | 值 | 来源 |"
"| --- | --- | --- |"

$remote = (Invoke-Git @('remote','get-url','origin'))
if (-not $remote) {
  # origin 不一定是 upstream 的别名（fork 工作流里常叫 upstream），退到任意一个
  $remotes = @(Invoke-Git @('remote','-v') | Where-Object { $_.Trim() })
  if ($remotes.Count -gt 0) { $remote = ($remotes[0] -split '\s+')[1] }
}
$platform = if ($remote -match 'github\.com') { 'GitHub' } elseif ($remote -match 'gitlab') { 'GitLab' } else { '未知' }
$repoName = if ($remote -match '[:/]([^/:]+/[^/]+?)(\.git)?$') { $matches[1] } else { '未知' }
$defaultBranch = ''
foreach ($r in @('origin', 'upstream')) {
  $defaultBranch = (Invoke-Git @('symbolic-ref', "refs/remotes/$r/HEAD")) -replace "^refs/remotes/$r/", ''
  if ($defaultBranch) { break }
}
if (-not $defaultBranch) { $defaultBranch = (Invoke-Git @('config','--get','init.defaultBranch')) }
if (-not $defaultBranch) { $defaultBranch = 'main' }

"| 平台 | $platform | `[推导]` remote url |"
"| 仓库 | $repoName | `[推导]` |"
"| 默认分支 | $defaultBranch | `[推导]` |"

# 分支前缀限制
$contrib = Get-ChildItem -Filter 'CONTRIBUTING*' -ErrorAction SilentlyContinue | Select-Object -First 1
if ($contrib) {
  $c = [IO.File]::ReadAllText($contrib.FullName)
  if ($c -match 'claude/|codex/|dependabot/') { "| 允许的分支名前缀 | 见 CONTRIBUTING（有前缀限制） | `[推导]` $($contrib.Name) |" }
  if ($c -match 'Allow edits by maintainers') { "| 必须勾 Allow edits by maintainers | 是 | `[推导]` $($contrib.Name) |" }
  if ($c -match 'CLA|Contributor License') { "| 需要签署 CLA | 是 | `[推导]` $($contrib.Name) |" }
}

# commit 规范
$prefixes = Invoke-Git @('log','--format=%s','-50') | ForEach-Object {
  if ($_ -match '^([a-z]+)(\([^)]+\))?!?:') { $matches[1] } else { '(无前缀)' }
} | Group-Object | Sort-Object Count -Descending
$top = ($prefixes | Select-Object -First 3 | ForEach-Object { "$($_.Name) $($_.Count)" }) -join ' / '
if ($top -match 'fix|feat|docs') { "| commit 规范 | conventional commits | `[推导]` 近 50 提交：$top |" }
else { "| commit 规范 | 无固定前缀 | `[推导]` 近 50 提交：$top |" }

# commit 语言
$langs = Invoke-Git @('log','--format=%s','-20') | ForEach-Object { if ($_ -match '[\u4e00-\u9fff]') { '中文' } else { '英文' } } | Group-Object | Sort-Object Count -Descending
if ($langs) { "| commit 语言 | $($langs[0].Name) | `[推导]` 近 20 提交 |" }

# PR 模板
$tpl = @()
$tpl += Get-ChildItem '.github' -Filter '*pull_request_template*' -Recurse -ErrorAction SilentlyContinue
$tpl += Get-ChildItem '.github\PULL_REQUEST_TEMPLATE*' -ErrorAction SilentlyContinue
$tpl += Get-ChildItem '.gitlab\merge_request_templates' -ErrorAction SilentlyContinue
if ($tpl.Count -gt 0) { "| PR 正文模板 | $($tpl[0].FullName.Replace($root + '\','')) | `[推导]` |" }
else { "| PR 正文模板 | 无模板，用默认三段 | `[推导]` |" }

# ---------- 2. 测试要求 ----------
""
"## 2. 测试要求"
""
"| 项 | 值 | 来源 |"
"| --- | --- | --- |"

$cmds = @()
if (Test-Path 'package.json') {
  $pkg = Get-Content 'package.json' -Raw | ConvertFrom-Json
  if ($pkg.scripts) {
    $cmds = $pkg.scripts.PSObject.Properties.Name | Where-Object { $_ -match 'test|lint|check|format|typecheck' }
    "| 可用检查命令 | $(($cmds | ForEach-Object { "npm run $_" }) -join '、') | `[推导]` package.json |"
  }
} elseif (Test-Path 'pyproject.toml' -or Test-Path 'tox.ini' -or Test-Path 'pytest.ini') {
  "| 可用检查命令 | pytest / ruff / mypy（按配置） | `[推导]` Python 项目 |"
} elseif (Test-Path 'Cargo.toml') {
  "| 可用检查命令 | cargo test / cargo clippy | `[推导]` Cargo.toml |"
} elseif (Test-Path 'go.mod') {
  "| 可用检查命令 | go test ./... / go vet | `[推导]` go.mod |"
} elseif (Test-Path 'Makefile') {
  "| 可用检查命令 | make test（见 Makefile） | `[推导]` |"
}

# CI 实际跑什么
$wf = Get-ChildItem '.github\workflows' -Filter '*.yml' -ErrorAction SilentlyContinue
if ($wf) {
  $runs = @()
  foreach ($f in $wf) { $runs += (Select-String -Path $f.FullName -Pattern 'run:\s*(.+)' | ForEach-Object { $_.Matches[0].Groups[1].Value.Trim() }) }
  if ($runs) { "| CI 实际命令 | $(($runs | Select-Object -Unique | Select-Object -First 6) -join ' ; ') | `[推导]` .github/workflows |" }
}

# 平台跳过
$skip = Select-String -Path (Get-ChildItem -Recurse -Include '*.ts','*.js','*.py' -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch 'node_modules' } | Select-Object -First 200).FullName -Pattern "process\.platform|platform ===|sys\.platform|skip:" -ErrorAction SilentlyContinue
if ($skip) { "| 有平台条件跳过 | 是，$(($skip | Select-Object -First 3 | ForEach-Object { "$($_.Filename):$($_.LineNumber)" }) -join '、') | `[推导]` |" }

# 守卫测试命名
$guard = Get-ChildItem -Recurse -Include 'guard-*' -File -ErrorAction SilentlyContinue | Select-Object -First 1
if ($guard) { "| 守卫测试命名 | $($guard.Name) | `[推导]` |" }

# ---------- 3. 目录地图 ----------
""
"## 3. 目录地图"
""
"| 目录 | 文件数 | 说明 |"
"| --- | --- | --- |"
Get-ChildItem -Directory | Where-Object { $_.Name -notmatch '^\.|node_modules|dist|build|target|__pycache__' } | ForEach-Object {
  $n = (Get-ChildItem $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
  "| $($_.Name) | $n | |"
}

# ---------- 4. 需要人工补的 ----------
""
"## 4. 还需要人工补"
""
"- **观察项**：维护者是否直接改分支、review 风格、首响中位、合并节奏 → 跑 ``scripts/pr-status.ps1 -Repo $repoName -Author <你>`` 后填"
"- **维护者政策**：兜底门槛、明确拒绝过的方向 → 读最近 20 个关闭未合并 PR 的维护者留言"
"- **领域约定**：写代码前必读的几条 → 读 README / AGENTS / 核心模块注释"
"- **不变量**：只有做严重线才需要 → 见 ``references/severe-scan.md`` 第一节"
"- **用户偏好**：止损线、低价值 PR 提不提 → 问用户"

} finally {
  Pop-Location
}

