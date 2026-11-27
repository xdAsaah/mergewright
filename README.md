# pr-merged

让开源 PR 被合并的跨会话工作台。

不是「怎么写 PR」的教程，而是解决一个具体问题：**下次打开会话，怎么在几分钟内知道这个项目还剩什么没做、什么已经排除、下一个该做哪条。**

## 为什么需要它

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
python scripts/prtool.py onboard --path <本地仓库>
python scripts/prtool.py append  --file state/prs.jsonl --json '{...}'
python scripts/prtool.py check
python scripts/prtool.py whoami
```

| 子命令 | 做什么 |
| --- | --- |
| `status` | 现算合并率、open 积压、通道活性，支持 GitHub / GitLab |
| `onboard` | 读本地仓库，推导出 commit 规范、测试命令、PR 模板等 |
| `append` | 往 JSONL 台账追加一条事件 |
| `check` | 自检档案：死链、目录缺失、坏 JSON、必备节、手写数字 |
| `whoami` | 检查提交身份，覆盖未装 git / 未登录 / 真实邮箱等场景 |

只依赖 Python 3.8+ 标准库，无第三方包。凭据从 `git credential` 取，不落盘、不回显。

`scripts/*.ps1` 是 Windows PowerShell 的等价实现，但只覆盖 `status` / `onboard` / `append` 三个子命令。

## 硬规则

这个 skill 内置了几条不可绕过的约束：

1. **未获用户明确同意，不改代码、不 fork、不提 PR、不开 issue、不评论**
2. **修 bug 必须先写能变红的失败测试**，并用变异验证证明它真的守护
3. **证据分级**：注入故障算 L1，默认不能提；真实运行算 L2；平台硬限制或仓库文档矛盾算 L3
4. **数字不要手写**：合并率一律由 `status` 现算
5. **每次会话结束必须回填**档案，不写等于白做
6. **每次会话先定 PR 类型再挖候选**，不要挖完再问。类型只有五类：`fix` / `test` / `feat` / `perf` / `docs`

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
│   ├── hunt-candidate.md 找候选：6 种扫描手法
│   ├── verify.md         验证：三级证据 + 变异验证
│   ├── write-pr.md       写 PR：标题、正文、commit
│   ├── follow-up.md      跟进：review 风格 + 止损
│   ├── severe-scan.md    严重 bug：不变量 + 攻击面矩阵
│   └── first-pr.md       首 PR 与阶段策略
├── conventions/
│   └── _TEMPLATE.md      规则文件模板
├── projects/
│   ├── _index.md         项目一览（空表头）
│   └── _template/        项目档案模板
├── state/
│   ├── prs.jsonl         PR 事件流水
│   └── scans.jsonl       扫描流水
└── scripts/              5 个 Python 子命令 + 3 个 PowerShell 等价实现
```

## 关于仓库里的空文件

`preferences.md`、`lessons.md`、`projects/_index.md`、`state/*.jsonl` 在仓库里都是**空模板**。
它们是给你 clone 下来之后填的，不会包含作者的个人数据。

如果你直接在这个目录里使用 skill，建议取消 `.gitignore` 末尾那些注释掉的规则，避免把自己的私人数据提交上去。

## License

MIT
