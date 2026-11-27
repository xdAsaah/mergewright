---
name: open-source-pr
description: 开源贡献的跨会话工作台：为某个仓库找可提的 PR 候选、验证证据、写失败测试、开 PR、跟进 review、回填台账。当用户提到提开源 PR、找候选 bug、挖有价值的 PR、写失败测试提 PR、跟进已提 PR 的结果、查看某项目还能提什么、开源贡献台账、避免重复调研某个仓库、给新仓库建立贡献规则时触发。也用于首次进入一个新仓库做评分与首 PR 选择。
---

# 开源 PR 工作台

跨会话、跨项目地推进开源贡献。**核心目标不是"多提 PR"，而是下次开会话能在几分钟内回答三个问题**：

1. 这个项目还剩什么没做？
2. 什么已经被排除（以及为什么）？
3. 下一个该做哪一条？

## 第一次用：先做初始化

**没有 `preferences.md` 或它还是空表** → 读 `references/init.md`，问 3 个只有用户知道的问题，一次问完。

不要跳过这一步直接找项目——目的、时间投入、技术栈这三项决定了后面所有判断。

**提交身份不用问**，跑 `python scripts/prtool.py whoami` 自动检测，缺什么它会给出可直接执行的设置命令。

## 四层结构

| 层 | 位置 | 内容 | 变不变 |
| --- | --- | --- | --- |
| **方法层** | `references/` | 怎么找、怎么验证、怎么写、怎么止损 | 跨项目通用 |
| **规则层** | `conventions/<项目>.md` | 这个仓库的 commit 规范、PR 模板、测试要求、维护者政策 | 每项目一份 |
| **状态层** | `projects/` + `state/` | 台账、排除项、候选池、事件流水 | 每项目一份 |
| **经验层** | `lessons.md` | 你自己踩过的坑，跨项目复用，还没成熟到进方法层 | 跨项目 |

**规则层的值不要写进方法层。** 方法层只说「查 `conventions` 的 X」，具体值去规则文件看。

**经验怎么流动**：`ledger.md` 的单项目教训 →（换个项目也成立）→ `lessons.md` →（能写成可执行步骤）→ `references/`。同一类教训出现 2 次或导致过 PR 被关，必须升级。详见 `lessons.md` 第二节。

`preferences.md` 存「用户要什么」，`lessons.md` 存「你学到了什么」，不要混。

## 硬规则（任何情况下都适用）

1. **未获用户明确同意，不改代码、不 fork、不提 PR、不开 issue、不评论。** 挖到候选先汇报，等指令。
2. **修 bug 先写能复现的失败测试**，并且用变异验证证明它会红：改坏实现 → 确认只有对应那条用例失败 → 恢复。恒真的断言不算守护。
3. **证据要够。** 兜底类修复的门槛查 `conventions/<项目>.md` 的「维护者政策」；该字段为空时默认按 `references/verify.md` 的 L2/L3 标准。
4. **标题写「场景：旧行为 → 新行为」**，正文格式按 `conventions/<项目>.md` 的「PR 正文模板」。
5. **每次会话结束必须回填**：`projects/_index.md` 的下一个动作、对应项目的 `ledger.md` / `candidates.md`、`state/*.jsonl` 追加事件。不写等于白做。
6. **踩到的坑当场归类**：只对这个项目成立 → 写该项目 `ledger.md` 的教训；换个项目也成立 → 写 `lessons.md`。别只留在对话里。

## 路由表

| 用户要什么 / 你正要做什么 | 先读 |
| --- | --- |
| **第一次用、还没设置偏好** | `references/init.md` |
| **检查 git 提交身份、noreply 邮箱** | `scripts/prtool.py whoami` |
| **接手一个已有项目**（默认入口） | `projects/_index.md` → `conventions/<项目>.md` → 该项目 `candidates.md` |
| **新项目进场**（还没有 conventions） | `references/onboard-project.md` |
| 选新项目、评估值不值得去 | `references/choose-project.md` |
| 在某项目里找可提的 PR 候选 | `references/hunt-candidate.md` |
| 候选怎么验证、怎么算证据够 | `references/verify.md` |
| 写 PR 标题 / 正文 / commit | `references/write-pr.md` + `conventions/<项目>.md` |
| 维护者回复了、要不要改、怎么止损 | `references/follow-up.md` |
| 找严重 bug（S1/S2 线） | `references/severe-scan.md` |
| 查某项目当前 PR 状态与合并率 | `scripts/prtool.py status`（或 `scripts/pr-status.ps1`） |
| **踩到一个坑，判断该记在哪** | `lessons.md` 第一节（判据）+ 第三节（贡献教训）/ 第四节（工具障碍） |
| **检查档案有没有坏（死链、手写数字、坏 JSON）** | `scripts/prtool.py check` |

## 记录在哪（写之前先看这里）

| 想知道 | 文件 |
| --- | --- |
| 所有项目一览、各自下一个动作 | `projects/_index.md` |
| 某项目的 commit/测试/维护者规则 | `conventions/<项目>.md` |
| 某项目的背景、仓库地图、领域约定 | `projects/<项目>/profile.md` |
| 某项目提过哪些 PR、结果如何、维护者改了什么 | `projects/<项目>/ledger.md` |
| 某项目哪些方向已排除（防重复调研） | `projects/<项目>/excluded.md` |
| 某项目待验证 / 待提 / 已筛掉的候选 | `projects/<项目>/candidates.md` |
| 严重线的覆盖缺口清单 | `projects/<项目>/coverage.md`（按需创建） |
| PR 事件流水（机器读，算合并率用） | `state/prs.jsonl` |
| 扫描流水（查过什么、结论如何） | `state/scans.jsonl` |
| 你自己踩过的坑、待验证的猜想 | `lessons.md` |
| 跨项目用户偏好（止损线、时限、目标方向） | `preferences.md` |

**数字不要手写。** 合并率、open 积压、最近合并时间一律由 `scripts/prtool.py status` 现算。

## 一次会话的标准流程

1. 读 `preferences.md`（没有就先做初始化）。
2. 读 `projects/_index.md`，确定本次做哪个项目、做什么。
3. **读该项目的 `conventions/<项目>.md`** —— 没有就先跑 `references/onboard-project.md`。
4. 读该项目的 `candidates.md` 与 `excluded.md`，**不要重走已排除的方向**。
5. 按 `references/hunt-candidate.md` 挖候选；每个候选按 `references/verify.md` 定性。
6. 汇报候选与证据，等用户决定。
7. 用户同意后按 `references/write-pr.md` + 该项目 conventions 开 PR。
8. 回填：`candidates.md` 状态、`state/scans.jsonl` 追加一条、`_index.md` 更新下一个动作；本轮踩到的坑按第 6 条硬规则归类。
9. PR 有结果时：更新 `ledger.md`、`state/prs.jsonl`、`profile.md` 的维护者画像。
10. 收尾跑一次 `python scripts/prtool.py check`，确认档案没写坏。

## 脚本

**两个版本等价，挑一个能跑的就行**：`scripts/prtool.py`（Python 3.8+，只用标准库，Windows / macOS / Linux 都能跑）；`scripts/*.ps1`（Windows PowerShell 5.1，无 Python 时用）。

```bash
# 查某项目状态（现算合并率与通道活性；支持 GitHub / GitLab）
python scripts/prtool.py status --repo owner/repo --author 你的用户名

# 追加一条事件到 JSONL 台账
python scripts/prtool.py append --file state/prs.jsonl --json '{"ts":"2026-11-27T02:10:00Z","project":"<项目>","pr":123,"status":"merged"}'

# 进场采集（只做推导部分，输出可直接粘进 conventions）
python scripts/prtool.py onboard --path <本地仓库路径>

# 自检：死链、目录缺失、JSONL 合法性、conventions 必备节、手写数字
python scripts/prtool.py check

# 检查提交身份，缺什么给出可直接执行的设置命令
python scripts/prtool.py whoami
```

Windows PowerShell 等价：

```powershell
.\scripts\pr-status.ps1 -Repo owner/repo -Author 你的用户名
.\scripts\append.ps1 -File state/prs.jsonl -Json '{"ts":"...","project":"<项目>","pr":123}'
.\scripts\onboard.ps1 -Path <本地仓库路径>
```

凭据都从 `git credential` 取（同一个凭据库，不落盘、不回显）。两个版本都支持 GitHub 和 GitLab，自建实例用 `--site` / `-Site` 指定域名。

**注意**：PowerShell 里用 `--json` 传带引号的 JSON 会被吞引号，改用 stdin 管道：
```powershell
'{"ts":"..."}' | python scripts/prtool.py append --file state/prs.jsonl
```

## 用户偏好与经验

- `preferences.md`：止损线、响应时限、低价值 PR 提不提、目标方向这类**跨项目偏好**。首次使用由 `references/init.md` 生成。
- `lessons.md`：你自己踩过的坑和待验证的猜想。每次会话结束按硬规则第 6 条归类。
