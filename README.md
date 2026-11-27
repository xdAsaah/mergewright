# pr-merged

**拿到第一个被合并的 PR。然后是第二个、第三个。**

大部分贡献不是失败在代码上，是死在没人告诉你的地方：维护者不认注入的故障当证据，修了一处还有三处同样的坑，或者你花两小时做完的修复，早就有人开了 PR。

`pr-merged` 是一个跨会话工作台，专门解决这些。它帮你找真实候选、逼你在写代码前先证明 bug、让你避开撞车，并把每个项目的规则、排除过的方向、每个 PR 的复盘都记住——下次开局几分钟，不是从零开始。

[English](README.en.md) | 中文

## 用它之前和之后

| 之前 | 之后 |
| --- | --- |
| 每次会话重新调研同一个仓库 | 打开 `_index.md`，一眼看到还剩什么、什么已排除 |
| 提了个修复，维护者说「这不算证据」 | 证据分级逼你先到 L2 再动笔 |
| 花两小时做的 bug，别人早修了 | `issues` 标出已有 PR 在审、已修待确认、PR 坟场 |
| 猜这个项目收不收 test 类 PR | 从近 20 个已合并 PR 自动观察接受度 |
| 忘了维护者在你分支上改了什么 | 每个 PR 都有复盘，写进 `ledger.md` |

## 为什么 PR 会失败

给开源项目提 PR，失败通常不是代码写错，而是这几种：

- 用注入的故障当证据，维护者不认
- 修了撞到的一处，同类漏项还有三处
- 上个月查过的方向，这次又从头查一遍
- 维护者直接改了你的分支，你没读懂他改了什么

这些问题靠记性解决不了。这个 skill 把它们变成**可持久化的档案**：项目规则、已排除方向、每个 PR 的复盘、跨项目的教训，都落在文件里。

## 它是什么

一个符合 agent skill 规范的多文件目录，包含：

| 层 | 位置 | 作用 |
| --- | --- | --- |
| 方法层 | `references/` | 怎么找候选、怎么验证证据、怎么写 PR、怎么止损 |
| 规则层 | `conventions/<项目>.md` | 每个仓库的 commit 规范、测试要求、维护者政策 |
| 状态层 | `projects/` + `state/` | 台账、排除项、候选池、事件流水 |
| 经验层 | `lessons.md` | 你自己踩过的坑，带升级路径 |

## 安装

### Trae / Trae CN

```bash
git clone https://github.com/<你的用户名>/pr-merged.git ~/.trae-cn/skills/pr-merged
```

### Claude Code

```bash
git clone https://github.com/<你的用户名>/pr-merged.git ~/.claude/skills/pr-merged
```

### 其他 agent

skill 格式是通用的：`SKILL.md` + YAML frontmatter（`name` + `description`）+ 同目录引用文件。
放到你的 agent 的 skills 目录下即可。

## 首次使用

装好后直接说「我要提开源 PR」或「看看这个仓库能提什么」，skill 会自动触发。

第一次会问你 3 个问题：

1. **目的**：求职 / 学技术 / 进社区 / 修自己用的问题
2. **时间**：每周能投入多少
3. **技术栈和领域**：多选，各含「不限」

止损线、响应时限、低价值 PR 策略**不问**，由前两题推导后给你确认。

提交身份也**不问**，跑一条命令自动检测：

```bash
python scripts/prtool.py whoami
```

它会检查 git 是否安装、有没有登录、邮箱是不是 noreply。缺什么就给你可直接执行的命令。

## 命令

```bash
python scripts/prtool.py status  --repo owner/repo --author 你的用户名
python scripts/prtool.py issues  --repo owner/repo
python scripts/prtool.py onboard --path <本地仓库>
python scripts/prtool.py append  --file state/prs.jsonl --json '{...}'
python scripts/prtool.py check
python scripts/prtool.py whoami
```

| 子命令 | 做什么 |
| --- | --- |
| `status` | 现算合并率、open 积压、通道活性，按 PR 类型分组统计；支持 GitHub / GitLab |
| `issues` | 扫 open issue，标新手友好 / 欢迎 PR / 长期未修 / 已认领 / 已有 PR 在审 / 已修待确认 / 有相关 PR / 多 PR 未合 |
| `onboard` | 读本地仓库，推导出 commit 规范、测试命令、PR 模板等 |
| `append` | 往 JSONL 台账追加一条事件 |
| `check` | 自检档案：死链、目录缺失、坏 JSON、必备节、手写数字 |
| `whoami` | 检查提交身份，覆盖未装 git / 未登录 / 真实邮箱等场景 |

只依赖 Python 3.8+ 标准库，无第三方包。凭据从 `git credential` 取，不落盘、不回显。

`scripts/*.ps1` 是 Windows PowerShell 的等价实现，但只覆盖 `status` / `onboard` / `append` 三个子命令，**没有 `issues`、`check`、`whoami`**。

## 硬规则

这个 skill 内置了几条不可绕过的约束：

1. **未获用户明确同意，不改代码、不 fork、不提 PR、不开 issue、不评论**
2. **修 bug 必须先写能变红的失败测试**，并用变异验证证明它真的守护
3. **证据分级**：注入故障算 L1，默认不能提；真实运行算 L2；平台硬限制或仓库文档矛盾算 L3
4. **数字不要手写**：合并率一律由 `status` 现算
5. **每次会话结束必须回填**档案，不写等于白做
6. **每次会话先定 PR 类型再挖候选**，不要挖完再问。类型只有五类：`fix` / `test` / `feat` / `perf` / `docs`

## 下一步做什么（四档优先级）

每次会话从上往下查，命中就停：

| 档 | 条件 | 动作 |
| --- | --- | --- |
| 1 | `candidates.md` 有待提候选 | 直接汇报，问要不要提 |
| 2 | 有待验证候选 | 先补证据，够格就升档 |
| 3 | 都空，且该项目 **0 个 PR** | 推荐低价值方向当敲门砖 |
| 4 | 都空，且已提过 PR | 问用户这次做哪类 |

前两档不问类型——候选已在手，直接问「要做吗」。第 3 档的「0 个 PR」不是「0 个 merged」，提过被关闭的算有记录。

## issue 怎么用

issue 既是候选来源，也是防重复的记录：

```bash
python scripts/prtool.py issues --repo owner/repo
```

自动标记八类：

| 标记 | 该怎么用 |
| --- | --- |
| **新手友好**（`good first issue`） | 优先看 |
| **欢迎 PR**（`help wanted`） | 优先看 |
| **长期未修**（≥90 天未认领） | 看为什么没修 |
| **已认领** | 不要碰 |
| **已有 PR 在审** | 不要碰，会撞车 |
| **已修待确认**（PR 已合但 issue 未关） | 先去验证，别重做 |
| **有相关 PR**（PR 被关闭） | 读关闭理由再决定 |
| **多 PR 未合×N**（≥3 次尝试失败） | PR 坟场：需求真实但难做，先读失败评论找共同卡点 |

关联 PR 查询默认查前 15 个 issue，每个多一次 API 请求。用 `--linked-limit` 调整，`--no-linked` 关掉。「多 PR 未合」的阈值用 `--min-failed-prs` 调整，默认 3。

| 场景 | 规则 |
| --- | --- |
| 找候选 | 优先看标了新手友好 / 欢迎 PR 的 |
| 要不要先开 issue | 查 `conventions/<项目>.md` 的 3.2「issue 政策」；新增功能、改协议必须先谈 |
| PR 正文 | 完整解决写 `Fixes #N`，部分解决写 `Refs #N`；一条 PR 只关一个 issue |
| 会话结束 | 更新 `projects/<项目>/issues.md` |

## PR 类型怎么定

不是「第一个 PR 做低价值，之后随便」。每一次会话都会先定类型，依据三个输入：

| 输入 | 从哪来 |
| --- | --- |
| 项目阶段 | 已合并数：0–1 信任建立 / 1–3 低严重度 / ≥3 可上严重线 |
| 项目接受度 | `conventions/<项目>.md` 的「PR 类型接受度」表，从近 20 个已合并 PR 自动观察 |
| 你自己的历史 | `status --author <你>` 输出里的「按类型」段，直接给各类型合并率 |

然后**问你这次做哪类**，不替你做决定。挖完的候选按类型归档，每 5 个 PR 更新一次 `ledger.md` 的「类型复盘」表。

## 目录

```
pr-merged/
├── SKILL.md              入口，路由表 + 硬规则 + 会话流程
├── preferences.md        你的跨项目偏好（首次使用后填写）
├── lessons.md            你踩过的坑，带升级路径
├── references/           方法层，9 个文件
│   ├── init.md           首次使用：3 个问题 + 身份检查
│   ├── onboard-project.md 进新仓库：推导规则 + 观察维护者
│   ├── choose-project.md 选项目：评分卡 + 统计陷阱
│   ├── hunt-candidate.md 找候选：7 种扫描手法
│   ├── verify.md         验证：三级证据 + 变异验证
│   ├── write-pr.md       写 PR：标题、正文、commit
│   ├── follow-up.md      跟进：review 风格 + 止损
│   ├── severe-scan.md    严重 bug：不变量 + 攻击面矩阵
│   └── first-pr.md       首 PR 与阶段策略
├── conventions/
│   └── _TEMPLATE.md      规则文件模板
├── projects/
│   ├── _index.md         项目一览（空表头）
│   └── _template/        项目档案模板（profile / ledger / candidates / excluded / issues）
├── state/
│   ├── prs.jsonl         PR 事件流水
│   └── scans.jsonl       扫描流水
└── scripts/              6 个 Python 子命令 + 3 个 PowerShell 等价实现
```

## 关于仓库里的空文件

`preferences.md`、`lessons.md`、`projects/_index.md`、`state/*.jsonl` 在仓库里都是**空模板**。
它们是给你 clone 下来之后填的，不会包含作者的个人数据。

如果你直接在这个目录里使用 skill，建议取消 `.gitignore` 末尾那些注释掉的规则，避免把自己的私人数据提交上去。

## License

MIT
