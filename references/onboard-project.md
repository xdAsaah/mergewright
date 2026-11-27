# 进场：把项目规则采集出来

> 触发：第一次在某个仓库工作，或用户说「加一个新项目」。
> **目标：自动填出 `conventions/<项目>.md` 里 70% 的项，只把剩下 2–3 个问题问用户。**

## 一、先读全局偏好，别重复问

**止损线、低价值 PR 策略、目标方向这些是全局偏好，存在 `preferences.md`。**

| 情况 | 动作 |
| --- | --- |
| `preferences.md` 已有值 | 直接用，**不要在这个项目里再问一遍** |
| `preferences.md` 缺失或空 | 先跑 `references/init.md` 的全局初始化，一次问完 |
| 这个项目要破例（比如这里愿意更宽松） | 记进 `conventions/<项目>.md` 的备注，并在 `preferences.md` 标「项目例外」 |

**只有项目级的问题才在这里问**（见第四节）。

## 二、代码在哪：先查，别问

进任何仓库之前先查一遍，**不要直接问用户「仓库在哪个目录」**：

```bash
python scripts/prtool.py where --project <项目>
```

| 输出 | 做什么 |
| --- | --- |
| 有「本机可用：<路径>」 | 直接用这个路径，跳到第三节 |
| 标「路径缺失」/「remote 不符」 | 代码搬过家或换了 remote，重新 clone 后用 `where --path` 记一条 |
| 标「别的机器」 | 这台机器没有副本，按记录里的 repo clone 一份再记 |
| 完全没有记录 | 问用户要路径，`onboard --path` 会自动记下来 |

记录落在数据目录的 `state/workspaces.jsonl`，所有 agent 共用同一份。**同一个项目在不同 agent 里 clone 到不同目录、甚至不同机器，都能查到。**

## 三、推导（读文件）

按顺序跑，每项记进 `conventions/<项目>.md` 并标 `[推导]`。

### 1. 平台与仓库

```powershell
git remote -v                      # 平台 + owner/repo
git symbolic-ref refs/remotes/origin/HEAD   # 默认分支
```

### 2. commit 规范

```powershell
# 最近 50 个提交的前缀分布
git log --format='%s' -50 | ForEach-Object {
  if ($_ -match '^([a-z]+)(\([^)]+\))?!?:') { $matches[1] } else { '(无前缀)' }
} | Group-Object | Sort-Object Count -Descending | Select-Object Name, Count
```

- 有 `fix`/`feat`/`docs` 等集中分布 → conventional commits
- 大部分是 `(无前缀)` → 无规范，照维护者最近的习惯写

**语言**：看最近 20 条标题里有没有 CJK 字符。

```powershell
git log --format='%s' -20 | ForEach-Object { if ($_ -match '[\u4e00-\u9fff]') { '中文' } else { '英文' } } | Group-Object | Select-Object Name, Count
```

### 3. PR 正文模板

```powershell
Get-ChildItem .github -Filter '*pull_request_template*' -Recurse -ErrorAction SilentlyContinue
Get-ChildItem .github/PULL_REQUEST_TEMPLATE* -ErrorAction SilentlyContinue
Get-ChildItem .gitlab/merge_request_templates -ErrorAction SilentlyContinue
```

有模板 → 照抄小标题进 `conventions`；没有 → 用 `references/write-pr.md` 的默认三段。

### 4. 贡献指南里的硬要求

```powershell
Get-ChildItem CONTRIBUTING*,AGENTS*,CODE_OF_CONDUCT* -ErrorAction SilentlyContinue
```

重点找：
- 分支名前缀限制
- 是否要求 `Allow edits by maintainers`
- 是否要求 CLA
- 是否要求先开 issue

### 5. 测试命令

按项目类型找入口：

| 项目类型 | 看哪里 |
| --- | --- |
| Node | `package.json` 的 `scripts` |
| Python | `pyproject.toml`、`tox.ini`、`Makefile`、`pytest.ini` |
| Go | `Makefile`、`.golangci.yml` |
| Rust | `Cargo.toml`、`Makefile` |
| 其他 | `Makefile`、`justfile`、`Taskfile.yml` |

再读 CI 配置（`.github/workflows/`、`.gitlab-ci.yml`），确认**CI 实际跑的命令**——它比本地脚本更能说明「什么算通过」。

### 6. 平台边界（本机跑不了的测试）

```powershell
# 找「按平台跳过」的逻辑
Select-String -Path tests\*,scripts\* -Pattern 'platform ===|process.platform|skip:|unix|win32' -ErrorAction SilentlyContinue
```

### 7. 目录地图

```powershell
Get-ChildItem -Directory | Where-Object { $_.Name -notmatch '^\.|node_modules' } | Select-Object Name
```

结合 README 判断每个目录的职责和改动风险。

## 四、观察（读最近的 PR）

用 `scripts/prtool.py status --repo <owner/repo>` 取数，然后：

| 看什么 | 怎么判断 | 记成 |
| --- | --- | --- |
| 维护者是否直接改贡献者分支 | 已合并 PR 的 commit 数 > 作者提交数，或 `commits` 里有维护者作者 | `[观察]` |
| review 风格 | 有 line review 评论 → 写意见；只有 issue 评论 → 留言型；都没有但 commit 变了 → 直接改 | `[观察]` |
| 人类首响中位 | 一次性外部作者的 PR，从 created 到第一条他人评论的小时数 | `[观察]` |
| 合并节奏 | 合并时间戳的分布：集中在几分钟内 → 批量；分散 → 逐条 | `[观察]` |
| 明确拒绝过的方向 | 读关闭未合并的 PR，看维护者留言 | `[观察]` → 写进 `excluded.md` |
| **PR 类型接受度** | 数近 20 个已合并 PR 的类型分布（`fix`/`test`/`feat`/`perf`/`docs`） | `[观察]` → 写进 conventions 3.1 |

**只看最近 20 个已关闭 PR，且剔除 bot 和自合并。**

### PR 类型接受度怎么判

`status` 输出里没有现成的类型分布（它只统计指定作者的），所以手工数一遍，或者跑：

```bash
# 列出近 20 个已合并 PR 的标题，按前缀人工归类
python scripts/prtool.py status --repo <owner/repo> --author <维护者>
```

更简单的办法：直接看最近 20 个已合并 PR 的标题前缀。

| 观察结果 | 判成 |
| --- | --- |
| 某类型有 ≥3 个合并，且合并间隔短 | **欢迎** |
| 有 1–2 个合并，或有条件（要求补测试/附数据） | **中性** |
| 有合并但都拖很久，或维护者留言提过门槛 | **谨慎** |
| 有明确关闭的同类 PR，且理由是否定该类 | **不接受** |
| 样本 < 2 个 | **未知**，不要假设 |

把结果填进 `conventions/<项目>.md` 的 3.1 表，每条带证据和日期。

## 五、只问项目级的这几个（最多 3 个）

推导和观察做完后，只问这些——**都是这个项目特有的，`preferences.md` 里没有**：

1. 这个项目你打算投入多久？一次做到底还是试试看？（决定要不要跑完整评分卡）
2. 有没有你知道但我读不出来的偏好？例如「这个维护者讨厌 XX」「他上次拒过某类改动」
3. 确认推导结果：把自动读出来的平台、commit 规范、测试命令、PR 模板列一遍，问他有没有错

**不要问**：
- 止损线、低价值 PR 提不提、目标方向 → 已在 `preferences.md`，直接读
- commit 规范、测试命令、平台、PR 模板 → 都能从仓库读出来，列给他确认即可

## 六、产出

1. `conventions/<项目>.md`（按 `_TEMPLATE.md` 填，每条带来源和日期）
2. `projects/<项目>/profile.md`（仓库地图、领域约定、维护者画像）
3. `projects/_index.md` 加一行
4. `state/workspaces.jsonl` 追加一条工作副本记录（`onboard --path` 自动写，除非加了 `--no-record`）
5. 告诉用户：**哪些是推导的、哪些是观察的、哪些是他定的**，让他能一眼看出哪些可能不准

## 七、规则过期怎么办

- 每条带日期；超过 90 天的 `[观察]` 项，下次用之前先重新看一眼
- 用户说「维护者变了」/「项目改规矩了」→ 立刻更新，并在变更记录里写明依据
- `prtool.py status` 输出里带 `pushed_at`，如果比 `conventions` 的最后更新还新，提示可能过期
- **类型接受度每 90 天重看一次**：项目的方向会变，半年前不接受 `feat`，现在可能在收
