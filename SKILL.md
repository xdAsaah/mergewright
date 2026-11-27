---
name: mergewright
description: 开源贡献的跨会话工作台：为某个仓库找可提的 PR 候选、验证证据、写失败测试、开 PR、跟进 review、回填台账。当用户提到提开源 PR、找候选 bug、挖有价值的 PR、写失败测试提 PR、跟进已提 PR 的结果、查看某项目还能提什么、开源贡献台账、避免重复调研某个仓库、给新仓库建立贡献规则时触发。也用于首次进入一个新仓库做评分与首 PR 选择。
---

# mergewright · 开源 PR 工作台

跨会话、跨项目地推进开源贡献。**核心目标不是"多提 PR"，而是下次开会话能在几分钟内回答三个问题**：

1. 这个项目还剩什么没做？
2. 什么已经被排除（以及为什么）？
3. 下一个该做哪一条？

## 第一次用：先做初始化

**先建数据目录**（只需一次）：

```bash
python scripts/prtool.py init
```

默认建在 `~/.mergewright/`。已存在的文件不会覆盖，重复跑是安全的。

**然后**：`preferences.md` 还是空表 → 读 `references/init.md`，问 3 个只有用户知道的问题，一次问完。

不要跳过这一步直接找项目——目的、时间投入、技术栈这三项决定了后面所有判断。

**提交身份不用问**，跑 `python scripts/prtool.py whoami` 自动检测，缺什么它会给出可直接执行的设置命令。

## 数据在哪

**skill 包和数据是两个目录，这一点很重要。**

| | 位置 | 说明 |
| --- | --- | --- |
| **skill 包** | 你 clone 的地方（如 `~/.trae-cn/skills/mergewright/`） | 只读。升级用 `git pull`，各 agent 各一份 |
| **数据目录** | 默认 `~/.mergewright/` | 唯一。所有执行记录都在这里，**多个 agent 共用同一份** |

本文档和 `references/` 里提到的 `conventions/`、`projects/`、`state/`、`preferences.md`、`lessons.md`，**一律指数据目录下的路径**，不在 skill 包里。

数据目录的确定顺序：

1. 命令行 `--data <路径>`
2. 环境变量 `MERGEWRIGHT_HOME`
3. 默认 `~/.mergewright/`

**为什么这样分**：同一台机器上可能装了 Trae、Claude Code、Codex 各一份 skill。如果数据跟着包走，切到另一个 agent 就是一份空档案，前面做过什么全不知道。分开之后，不管用哪个 agent，打开的都是同一份执行记录。

skill 包里的 `_seed/` 是空模板，`init` 时拷到数据目录。**不要直接改 `_seed/` 里的文件**——那是模板，改了会影响下次初始化。

### 本地工作副本在哪

数据共用解决了「记录在哪」，但没解决「**代码在哪**」。同一个项目在不同 agent 里可能 clone 在不同盘、不同目录，甚至不同机器上。

所以每个项目第一次进场时，把工作副本路径记下来：

```bash
python scripts/prtool.py where --project <项目> --path <本地仓库路径>
```

`onboard --path` 会自动写这一条，不用额外跑。记录落在 `state/workspaces.jsonl`：

```json
{"ts":"...","project":"agent-autoloop","repo":"owner/repo","path":"d:\\github\\agent-autoloop","host":"DESKTOP-XXXX","os":"Windows"}
```

**进项目前先查，别问用户要路径**：

```bash
python scripts/prtool.py where --project <项目>
```

输出会标出本机可用 / 路径缺失 / remote 不符 / 别的机器，并直接给出「本机可用：<路径>」。本机没有可用副本时，它按记录里的 repo 给出 clone 命令。`repo` 从 `git remote get-url origin` 推导，所以 remote 换过的旧路径能被认出来。

## 四层结构

| 层 | 位置 | 内容 | 变不变 |
| --- | --- | --- | --- |
| **方法层** | `references/` | 怎么找、怎么验证、怎么写、怎么止损 | 跨项目通用 |
| **规则层** | `conventions/<项目>.md` | 这个仓库的 commit 规范、PR 模板、测试要求、维护者政策 | 每项目一份 |
| **状态层** | `projects/` + `state/` | 台账、排除项、候选池、事件流水 | 每项目一份 |
| **经验层** | `lessons.md` | 你自己踩过的坑，跨项目复用，还没成熟到进方法层 | 跨项目 |

除方法层在 skill 包里，其余三层都在**数据目录**下。

**规则层的值不要写进方法层。** 方法层只说「查 `conventions` 的 X」，具体值去规则文件看。

**经验怎么流动**：`ledger.md` 的单项目教训 →（换个项目也成立）→ `lessons.md` →（能写成可执行步骤）→ `references/`。同一类教训出现 2 次或导致过 PR 被关，必须升级。详见 `lessons.md` 第二节。

`preferences.md` 存「用户要什么」，`lessons.md` 存「你学到了什么」，不要混。

## 硬规则（任何情况下都适用）

1. **未获用户明确同意，不改代码、不 fork、不提 PR、不开 issue、不评论。** 挖到候选先汇报，等指令。
2. **修 bug 先写能复现的失败测试**，并且用变异验证证明它会红：改坏实现 → 确认只有对应那条用例失败 → 恢复。恒真的断言不算守护。
3. **证据要够。** 兜底类修复的门槛查 `conventions/<项目>.md` 的「维护者政策」；该字段为空时默认按 `references/verify.md` 的 L2/L3 标准。
4. **标题写「场景：旧行为 → 新行为」**，正文格式按 `conventions/<项目>.md` 的「PR 正文模板」。
5. **每次会话结束必须回填**：`projects/_index.md` 的下一个动作、对应项目的 `ledger.md` / `candidates.md`、`state/*.jsonl` 追加事件。不写等于白做。
6. **开分支改代码之前，先在 `candidates.md` 的「进行中」档写一行**（分支名、已改文件、卡在哪）。这是唯一一处会因会话中断而直接导致重复劳动的地方。
7. **踩到的坑当场归类**：只对这个项目成立 → 写该项目 `ledger.md` 的教训；换个项目也成立 → 写 `lessons.md`。别只留在对话里。
8. **每次会话都要先定 PR 类型再挖候选**，不要挖完一堆再问用户要不要。类型只用五类：`fix` / `test` / `feat` / `perf` / `docs`。**例外**：`candidates.md` 的进行中/待提/待验证档已有内容时，直接接手或汇报，不重新问类型。
9. **先看已有候选，再挖新的。** 已经动手或挖出来、证据齐的候选，优先级高于任何新方向。
10. **用户基于你的结论批准动作时，动手前先复核那个结论。** 结论在你自己手里时是判断，错了代价为零；用户一旦据此批准，它就是行动依据，错了烧的是他的信誉和一个 PR 号。**凡「没有守护 / 没有测试 / 不存在」这类否定判断，复核时必须按文件名定位、整段读过对应测试文件**——搜索没命中不等于不存在，被截断的检索结果更不能当证据。细则见 `references/verify.md` 第八节。
11. **取数只走带 token 的通道。** `api.github.com` 的匿名额度只有 **60 次/小时/IP**，认证是 5000 次/小时；而 `web_fetch` 这类抓取工具加不了 `Authorization` 头，用它拉 API 等于匿名，一轮"按仓取数 + 逐个 PR 深读"就能把额度吃光。取数只准用三种：`scripts/prtool.py`（自带 token）、`gh api` / `gh pr view`、本地 `git`。**额度耗尽时 `prtool.py` 直接报错退出（退出码 2），此时数据是缺的，绝不能据此判断「仓库没有 PR」「项目停收了」。** 各命令的请求成本见「脚本」一节的表。
12. **PR 的语言默认英文，这是默认值，不是从仓库推导出来的。** 标题、正文、commit message、给维护者的回复，一律英文。只有当用户对本次或本项目**明确说过「用中文」**时才改：写中文，同时把 `conventions/<项目>.md` 的「PR 正文语言 / 提交语言」改标成 `[用户定] 中文`。**仓库模板文件本身是中文、历史 commit 是中文，都不构成理由**——文件语言不是写作语言。详见 `references/write-pr.md` 第零节。
13. **同一个项目同时最多 3 条 open PR，不分类型。** 到第 3 条就只跟进：按维护者要求改现有 PR、等评审结果，**不再挖新候选、不提新 PR**。只有用户明确要求才能破例，并在 `candidates.md` 记一行理由。开 PR 前先看 `status --author` 输出的「在审 N/3」。
14. **推送前跑该仓 CI 的门禁命令，不是只跑 `pytest` + `ruff`。** 清单来自 `conventions/<项目>.md` §2（由 `onboard` 从 `.github/workflows` 逐 job 抽出），重点是 `scripts/check_*.py`、`dev/*-check-local`、`make type-check*` 这类仓库自建脚本；带 `--base-rev` 的用 PR 基线。**PR 正文里「已验证」必须分级**：单测只能证明请求/参数形状，真实语义（尤其跨后端行为）没跑过就写「未验证，等 e2e」，见 `references/verify.md` 第九节。

## 路由表

| 用户要什么 / 你正要做什么 | 先读 |
| --- | --- |
| **第一次用、还没设置偏好** | `references/init.md` |
| **检查 git 提交身份、noreply 邮箱** | `scripts/prtool.py whoami` |
| **接手一个已有项目**（默认入口） | `projects/_index.md` → `conventions/<项目>.md` → 该项目 `candidates.md`（先看「进行中」档） |
| **代码在哪 / 工作副本路径** | `scripts/prtool.py where --project <项目>` |
| **新项目进场**（还没有 conventions） | `references/onboard-project.md` |
| 选新项目、评估值不值得去 | `references/choose-project.md` |
| 在某项目里找可提的 PR 候选 | `references/hunt-candidate.md` |
| 候选怎么验证、怎么算证据够 | `references/verify.md` |
| 写 PR 标题 / 正文 / commit | `references/write-pr.md` + `conventions/<项目>.md` |
| 维护者回复了、要不要改、怎么止损 | `references/follow-up.md` |
| 找严重 bug（S1/S2 线） | `references/severe-scan.md` |
| **做覆盖缺口清单 / 判断某条不变量有没有守护** | `projects/<项目>/coverage.md`，从 `_seed/projects/_template/coverage.md` 建；判定细则见 `references/verify.md` 第八节 |
| **这次该提哪类 PR、问用户选类型** | `references/first-pr.md` 第六节 + `conventions/<项目>.md` 的「PR 类型接受度」 |
| **从 issue 里找候选** | `references/hunt-candidate.md` 第 7 种手法 |
| **判断要不要先开 issue** | `conventions/<项目>.md` 的 3.2「issue 政策」 |
| **扫某项目 open issue** | `scripts/prtool.py issues --repo owner/repo` |
| **读某个 PR 的详情 / 评论 / review / 行内意见** | `scripts/prtool.py pr <PR 链接或 owner/repo#12>`（1 次请求拿全） |
| **查某仓库的关闭 / 合并明细（谁合的、为何被拒）** | `scripts/prtool.py closed --repo owner/repo`（基础 1 次请求） |
| **取表里没有的 GitHub API 数据** | `scripts/prtool.py api /repos/...`（带 token；禁止手搓匿名请求） |
| 查某项目当前 PR 状态与合并率 | `scripts/prtool.py status`（或 `scripts/pr-status.ps1`） |
| **踩到一个坑，判断该记在哪** | `lessons.md` 第一节（判据）+ 第三节（贡献教训）/ 第四节（工具障碍） |
| **检查档案有没有坏（死链、手写数字、坏 JSON）** | `scripts/prtool.py check` |
| **数据目录还没建 / 换了新机器** | `scripts/prtool.py init` |

## 记录在哪（写之前先看这里）

> 下表全部指**数据目录**下的路径（默认 `~/.mergewright/`），不是 skill 包里的。

| 想知道 | 文件 |
| --- | --- |
| 所有项目一览、各自下一个动作 | `projects/_index.md` |
| 某项目的 commit/测试/维护者规则 | `conventions/<项目>.md` |
| 某项目的背景、仓库地图、领域约定 | `projects/<项目>/profile.md` |
| 某项目提过哪些 PR、结果如何、维护者改了什么 | `projects/<项目>/ledger.md` |
| 某项目哪些方向已排除（防重复调研） | `projects/<项目>/excluded.md` |
| 某项目进行中 / 待提 / 待验证 / 已筛掉的候选 | `projects/<项目>/candidates.md` |
| 某项目看过 / 认领 / 自己开的 issue | `projects/<项目>/issues.md` |
| 严重线的覆盖缺口清单 | `projects/<项目>/coverage.md`（按需创建） |
| PR 事件流水（机器读，算合并率用） | `state/prs.jsonl` |
| 扫描流水（查过什么、结论如何） | `state/scans.jsonl` |
| 各项目在本机的 clone 路径（跨 agent / 跨机器） | `state/workspaces.jsonl` |
| 你自己踩过的坑、待验证的猜想 | `lessons.md` |
| 跨项目用户偏好（止损线、时限、目标方向） | `preferences.md` |

**数字不要手写。** 合并率、open 积压、最近合并时间一律由 `scripts/prtool.py status` 现算。

## 一次会话的标准流程

1. 读 `preferences.md`（没有就先做初始化）。
2. 读 `projects/_index.md`，确定本次做哪个项目、做什么。
3. **确认代码在哪**：`python scripts/prtool.py where --project <项目>`。有「本机可用」就直接用那个路径，不要问用户；没有就先 clone，再 `where --path` 记一条。
4. **读该项目的 `conventions/<项目>.md`** —— 没有就先跑 `references/onboard-project.md`。
5. 读该项目的 `candidates.md`、`excluded.md`、`issues.md`，**不要重走已排除的方向**。
6. **按五档优先级决定这次做什么**（见下节，第 0 档是「进行中」）。
7. 挖候选时按 `references/hunt-candidate.md`；每个候选按 `references/verify.md` 定性。
8. 汇报候选与证据，等用户决定。
9. 用户同意后按 `references/write-pr.md` + 该项目 conventions 开 PR。**开分支前先在 `candidates.md` 的「进行中」档写一行。**
10. 回填：`candidates.md` 状态（进行中→待提→已完成，带类型）、`state/scans.jsonl` 追加一条、`_index.md` 更新下一个动作；本轮踩到的坑按第 7 条硬规则归类。
11. PR 有结果时：更新 `ledger.md`、`state/prs.jsonl`、`profile.md` 的维护者画像；每 5 个 PR 更新一次 `ledger.md` 的「类型复盘」表。
12. 收尾跑一次 `python scripts/prtool.py check`，确认档案没写坏。

## 第五步：这次做什么（五档优先级）

**从上往下查，命中就停，不要跳档。**

**先过在审闸门**：`status --author` 显示「在审 ≥ 3/3」时，第 3、4 档直接不成立——本轮只做第 0–2 档（跟进已有 PR、按 review 改、补证据），不挖新候选、不提新 PR。唯一的破例是用户明确要求。

| 档 | 条件 | 做什么 | 问不问用户 |
| --- | --- | --- | --- |
| **0** | `candidates.md` 的「进行中」档非空 | **先接手**：读那行记的分支和已改文件，`git log`/`git diff` 看做到哪一步，接着做完 | 问「继续这条，还是放弃」 |
| **1** | 「待提」档非空 | 直接汇报这几个候选，问要不要提 | 只问「提哪个」，不问类型 |
| **2** | 「待验证」档非空 | 先补证据，够格就升到待提 | 问「要不要继续验证这条」 |
| **3** | 前三档都空，且该项目**提过 0 个 PR** | 推荐低价值方向（docs / test / 平台兼容）作为敲门砖 | 给推荐 + 理由，等确认 |
| **4** | 前三档都空，且已提过 PR | **问用户这次做哪类**（见 `references/first-pr.md` 第六节） | 必须问 |

**第 0 档为什么排最前**：已经开分支、改了代码的活，重做一遍的成本远高于任何新候选。上一个会话断在这里，说明当时判断过值得做。先看它，再谈新的。

**为什么第 1、2 档不问类型**：候选已经挖好、证据已经在手，再问「你想做哪类」是浪费一轮对话。直接说「有个 fix 候选等着，证据是 X，要做吗」。

**第 3 档的判定**：`ledger.md` 里 PR 记录为 0 条。**注意是 0 个 PR，不是 0 个 merged**——提过但被关闭的项目算「有记录」，走第 4 档，因为它已经暴露过维护者的态度。

**第 3 档推荐什么**（按合并难度从低到高）：

1. 文档勘误、示例修正（`docs`）
2. 补文档承诺但无测试守护的用例（`test`）
3. 平台兼容修复（Windows/macOS 上维护者跑不了的那类）
4. 纯测试基础设施（测试夹具、CI 小修）

推荐时要说清「为什么这个项目适合从低价值开始」——比如「这个项目近 20 个已合并里有 3 个纯测试 PR，说明维护者接受这类」。不要凭感觉推荐。

**第 4 档问完类型后**，才回到 `hunt-candidate.md` 按选定类型挖。

## issue 怎么参与

| 时机 | 做什么 | 详见 |
| --- | --- | --- |
| 找候选 | 扫 open issue：`good first issue`、长期未修 bug、维护者说 PR welcome 的；**自动标出已有 PR 在审 / 已修待确认的，避免撞车** | `references/hunt-candidate.md` 第 7 种手法 |
| 决定要不要先开 issue | 查 `conventions` 的「issue 政策」 | `conventions/_TEMPLATE.md` 3.2 |
| 开 PR 时 | 修 issue 就写 `Fixes #N`，只相关就写 `Refs #N` | `references/write-pr.md` 第六节 |
| 会话结束 | 更新 `projects/<项目>/issues.md` | 见该文件模板 |

**issue 是候选来源，也是防止重复工作的记录。** 别人已认领的 issue 不要碰；自己开的 issue 要追踪回复。

## 脚本

**优先用 `scripts/prtool.py`**（Python 3.8+，只用标准库，Windows / macOS / Linux 都能跑），十一个子命令齐全，全部从 `git credential` 取 token。

```bash
# 建数据目录（只需一次；已存在的文件不覆盖）
python scripts/prtool.py init

# 查某项目状态（现算合并率与通道活性；支持 GitHub / GitLab）
python scripts/prtool.py status --repo owner/repo --author 你的用户名

# 扫 open issue，标新手友好 / 已有 PR 在审 / PR 坟场等
python scripts/prtool.py issues --repo owner/repo

# 读一个 PR：详情 + 对话评论 + review + 行内线程 + 改动文件，一次 GraphQL
python scripts/prtool.py pr https://github.com/owner/repo/pull/12
python scripts/prtool.py pr owner/repo#12 --json      # 机器读

# 通用带 token 的 GET：所有 api.github.com 取数都走这里，别手搓匿名请求
python scripts/prtool.py api /rate_limit
python scripts/prtool.py api /repos/owner/repo/pulls/12/comments

# 已关闭 PR 明细：合并/未合并、时间；可选关闭理由与合并人
python scripts/prtool.py closed --repo owner/repo
python scripts/prtool.py closed --repo owner/repo --only unmerged --reasons
python scripts/prtool.py closed --repo owner/repo --only merged --with-merger --limit 20

# 追加一条事件到 JSONL 台账（相对路径按数据目录解析）
python scripts/prtool.py append --file state/prs.jsonl --json '{"ts":"2026-11-27T02:10:00Z","project":"<项目>","pr":123,"status":"merged"}'

# 进场采集（只做推导部分，输出可直接粘进 conventions；同时记下工作副本路径）
python scripts/prtool.py onboard --path <本地仓库路径>

# 查某个项目的代码在本机哪个目录（跨 agent / 跨机器）；给了 --path 就是记录
python scripts/prtool.py where --project <项目>
python scripts/prtool.py where --project <项目> --path <本地仓库路径>

# 自检：包完整性 + 数据档案健康度
python scripts/prtool.py check

# 检查提交身份，缺什么给出可直接执行的设置命令
python scripts/prtool.py whoami
```

**每条命令花掉几次 API 额度**（认证 5000 次/小时；匿名只有 60，所以别手搓）：

| 命令 | 请求次数 |
| --- | --- |
| `status`（open PR 有 N 个） | 3 + N；加 `--no-comments` 就是 3 |
| `status --author` | 上面 + 1（search 走单独额度，30 次/分钟） |
| `issues`（默认 `--linked-limit 15`） | 1 + 15 = 16；`--no-linked` 是 1；`--linked-limit 6` 是 7 |
| `pr <PR>` | 1（GraphQL 一次拿详情/评论/review/行内/文件） |
| `closed --limit N` | 1；`--reasons` 每条未合并 +1（默认最多 20）；`--with-merger` 每条已合并 +1（默认最多 20） |
| `api <path>` | 1，`?per_page=100` 也只算 1 |
| `where` / `onboard` / `append` / `check` / `init` / `whoami`（配置齐全时） | 0 |

额度低于 50 时会先警告；真打满则**直接以退出码 2 中止**，不会返回半截空数据。

`append` / `check` / `init` / `onboard` / `where` 都接受 `--data <路径>`，用来临时指向别的数据目录。

**没有 Python 时**用 `scripts/*.ps1`（Windows PowerShell 5.1），但**只有三个子命令**，`init` / `issues` / `check` / `whoami` / `where` / `api` / `pr` 都没有对应实现：

```powershell
.\scripts\pr-status.ps1 -Repo owner/repo -Author 你的用户名
.\scripts\append.ps1 -File state/prs.jsonl -Json '{"ts":"...","project":"<项目>","pr":123}'
.\scripts\onboard.ps1 -Path <本地仓库路径>
```

`api` / `pr` 的替代是 `gh`（同一个 token、同样吃 5000 额度）：`gh api /repos/owner/repo/pulls/12/comments`、`gh pr view 12 --repo owner/repo --comments`。**别退回到网页/匿名抓取**，那样就是 60 次/小时。

这种情况下，`init` 需要手动建目录（从 skill 包的 `_seed/` 拷到 `~/.mergewright/`），`where` 要手动看 `state/workspaces.jsonl`，`check` 和 `whoami` 的检查项也要手动做：`check` 见下方清单，`whoami` 见 `references/init.md` 第三节的「手动设置」。

**`check` 手工核对清单**（没有 Python 时）：

- `state/*.jsonl` 每行是否都是合法 JSON，且带 `ts` 和 `project`
- `state/workspaces.jsonl` 里的 `path` 在本机是否还存在（不存在就重新记一条）
- `projects/_index.md` 里每个项目是否有对应目录和 `conventions/<项目>.md`
- 文档里 `` `references/` `` 开头的路径引用是否都存在
- `projects/_index.md` 里有没有手写的合并数（应该用 `status` 现算）

凭据都从 `git credential` 取（同一个凭据库，不落盘、不回显）。两个版本都支持 GitHub 和 GitLab，自建实例用 `--site` / `-Site` 指定域名。

**注意**：PowerShell 里用 `--json` 传带引号的 JSON 会被吞引号，改用 stdin 管道：
```powershell
'{"ts":"..."}' | python scripts/prtool.py append --file state/prs.jsonl
```

## 用户偏好与经验

- `preferences.md`：止损线、响应时限、低价值 PR 提不提、目标方向这类**跨项目偏好**。首次使用由 `references/init.md` 生成。
- `lessons.md`：你自己踩过的坑和待验证的猜想。每次会话结束按硬规则第 6 条归类。
