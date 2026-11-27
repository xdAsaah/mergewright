# 写 PR：标题、正文、commit

> 触发：候选已验证通过，准备开 PR。
> **格式一律以 `conventions/<项目>.md` 的「托管与提交」为准。** 下面给的是没有规则文件时的默认值，以及跨项目通用的判断标准。

## 零、语言：默认英文

**PR 标题、正文、commit message、给维护者的回复，默认一律英文。** 这是默认值，不需要从仓库推导，也不因为模板文件是中文就改：

| 情况 | 写什么 |
| --- | --- |
| 默认（用户没提过语言） | **英文** |
| 用户对本次 / 本项目明确说「用中文」 | 中文；同时把 `conventions/<项目>.md` 的「PR 正文语言 / 提交语言」改成 `[用户定] 中文` |
| `.github/pull_request_template.md` 是中文 | 仍然英文——**文件语言不是写作语言** |
| 历史 commit 全是中文 | 仍然英文，除非用户就此说过中文 |
| 维护者直接要求换语言 | 按维护者要求改，并记进 `conventions` 的对应行（来源写 `[观察]` 或 `[用户定]`） |

**判断顺序**：用户的明确指示 → `conventions` 里 `[用户定]` 的语言 → 英文。中间那一层只有 用户定过 才有值，**不要自己从仓库习惯反推**。

## 一、标题

**通用标准**：标题要写清「场景 + 旧行为 → 新行为」，写不出来说明边界没想清，回去继续验证。

默认格式（多数项目适用）：`<type>(<scope>): <描述>`

| type | 什么时候用 |
| --- | --- |
| `fix` | 修一个可复现的错误行为 |
| `test` | 只增改测试 |
| `feat` | 新增能力（门槛最高） |
| `perf` | 只改性能，行为不变 |
| `docs` | 只改文档 |

`scope` 取改动的目录名。

**好的标题**（结构对，不看具体项目）：
- `fix(windows): a child of a console-less process no longer opens a window`
- `fix(cron): a zone that skips midnight still starts its day at the first hour`
- `fix(cli): an early-exiting reader no longer aborts the whole run`

**坏的标题**：
- `Fix bug` （没有场景）
- `Improve error handling` （没有新旧行为对比）
- `Add tests for X` （说的是动作，不是验收标准）

**默认英文标题**（见第零节）。**只有用户要求过中文，才用中文标题**；`conventions` 里 `[用户定]` 写了中文也照它来——别把自己的习惯强加给项目。

## 二、正文

**先读 `conventions/<项目>.md` 的「PR 正文模板」**：
- 填了模板路径 → 严格按模板的小标题写
- 写了「无模板」→ 用下面的默认三段
- 字段为空 → 先跑 `references/onboard-project.md` 采集

默认三段（无模板时）：

```markdown
## What this fixes

现象 + 原因 + 改后行为。

## How it was verified

- 新测试的红→绿实测（写具体数字，如 `3 !== 2`）
- 真机环境（OS 版本、运行时版本）
- 跑了哪些检查命令、结果
- 没跑的检查及原因

## Compatibility and impact

无影响就写 None 并说明为什么。
```

**通用要点**：
- **语言默认英文**（见第零节）；只有用户明确指定过中文的项目才写中文
- 红→绿要写**具体数字**，不要写「测试通过」
- 没跑的检查要主动说明原因，不要装作全跑了
- 维护者改过你分支的项目，正文要把边角情况写全（他会替你想，你想不到会显得没做功课）

## 三、发 PR 时的编码

**通用规则**：PR 正文按 UTF-8 发送，发完读回来校验有没有乱码。用 `prtool.py` 或平台的网页界面发就不会有问题。

**用 PowerShell 调 REST API 发 JSON 时中文会变 `?`**——这是 PowerShell 专有的坑，处理办法见 `lessons.md` 第四节「工具与环境障碍」。

## 四、commit

- **commit message 默认英文**（同第零节）；格式按 `conventions` 的「commit 规范」
- 正文写「旧行为 → 新行为 → 验证」
- 一个 PR 一个 commit 或少量相关 commit，不要夹带无关改动
- 作者身份：用 noreply 邮箱不影响贡献归属统计

```powershell
git -c user.name=<你的用户名> -c user.email=<noreply 邮箱> commit -m "<标题>" -m "<正文>"
```

## 五、开 PR 的必选项

- **在审数没到上限**：`status --author` 的「在审 N/3」，N 必须 < 3（见硬规则 13）。到 3 条就别开，去 `follow-up.md` 跟进
- **Allow edits by maintainers**：`conventions` 说是要求就必勾（`maintainer_can_modify: true`）
- 分支从最新默认分支起（先 fetch）
- 外部贡献走 Fork，不要往上游推分支
- 只含本次改动的 commit（用新分支，别把上个 PR 的 commit 带进来）

## 六、关联 issue

**修了某个 issue，PR 正文必须写关键词**，否则 issue 不会自动关闭，维护者要手动关联。

### 三个关键词，别用错

| 写法 | 作用 | 什么时候用 |
| --- | --- | --- |
| `Fixes #123` | 合并后**自动关闭** issue | 这个 PR 完整解决了该 issue |
| `Closes #123` | 同上，语义等价 | 同上，习惯用哪个都行 |
| `Refs #123` | 只建立引用，**不关闭** | 只解决了 issue 的一部分 |

**放哪**：PR 正文任意位置都行，但放在第一段或专门的 `## Related` 段最清楚。有些项目模板里有固定位置，查 `conventions` 的「PR 正文模板」。

**一条 PR 只关一个 issue。** 写 `Fixes #1, #2` 会被维护者要求拆开——一个 PR 解决一个问题。

### 没有关联 issue 时

**不要为了写 `Fixes` 而硬编一个 issue 号。** 纯 bug 修复、文档改动通常不需要关联。

如果你觉得这个问题值得留档，可以在 PR 正文里说明「No related issue」，或者提完 PR 后自己开一个 issue 关联回去（少见，通常没必要）。

### 反过来：先开 issue 再提 PR

`conventions` 的 3.2「issue 政策」写了哪类改动必须先开 issue。开了 issue 之后：

1. 等维护者表态（同意方向 / 提出修改 / 说他自己改）
2. 得到正面回应后再提 PR
3. PR 正文写 `Fixes #<你开的 issue 号>`

**如果维护者在你开 issue 后说「我自己改」**，直接停手，不要提 PR。

## 七、开完立刻做

1. 等 CI 全绿
2. 记录到 `projects/<项目>/ledger.md` 和 `state/prs.jsonl`
3. 更新 `projects/_index.md` 的下一个动作
4. **如果关联了 issue**，更新 `projects/<项目>/issues.md` 的状态为「PR 已提」
5. 按 `preferences.md` 的响应时限盯 review（默认 24 小时）

## 八、贡献类踩坑（与工具无关）

| 坑 | 表现 | 处理 |
| --- | --- | --- |
| 上个 PR 的 commit 混进来 | PR 显示多余文件 | 从默认分支新建分支再 cherry-pick |
| 只修撞到的那一处 | 维护者合并时补了同类漏项 | 全库搜一遍同类再提 |
| 注释/正文里的类比没验证 | 维护者只改了你这句注释 | 写进 PR 的文字也要能站住 |
| 文档 PR 里贴了不可见字符 | 引用报错信息时把 BOM 也贴进去 | 贴之前检查字符是否可见 |
| Windows 上 git diff 有 mode 变化 | 可执行位丢失 | 提交前检查 `git diff` 的 mode 行 |

**工具与环境障碍**（PowerShell 编码、`cmd /c`、沙箱拦截等）在 `lessons.md` 第四节，不混在这里。
