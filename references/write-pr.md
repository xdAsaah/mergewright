# 写 PR：标题、正文、commit

> 触发：候选已验证通过，准备开 PR。
> **格式一律以 `conventions/<项目>.md` 的「托管与提交」为准。** 下面给的是没有规则文件时的默认值，以及跨项目通用的判断标准。

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

**如果 `conventions` 说该项目用中文标题或不加前缀，就照它来**——别把自己的习惯强加给项目。

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
- **语言跟项目**：`conventions` 的「commit 语言」写英文就用英文
- 红→绿要写**具体数字**，不要写「测试通过」
- 没跑的检查要主动说明原因，不要装作全跑了
- 维护者改过你分支的项目，正文要把边角情况写全（他会替你想，你想不到会显得没做功课）

## 三、发 PR 时的编码

**通用规则**：PR 正文按 UTF-8 发送，发完读回来校验有没有乱码。用 `prtool.py` 或平台的网页界面发就不会有问题。

**用 PowerShell 调 REST API 发 JSON 时中文会变 `?`**——这是 PowerShell 专有的坑，处理办法见 `lessons.md` 第四节「工具与环境障碍」。

## 四、commit

- 语言和格式按 `conventions` 的「commit 规范」
- 正文写「旧行为 → 新行为 → 验证」
- 一个 PR 一个 commit 或少量相关 commit，不要夹带无关改动
- 作者身份：用 noreply 邮箱不影响贡献归属统计

```powershell
git -c user.name=<你的用户名> -c user.email=<noreply 邮箱> commit -m "<标题>" -m "<正文>"
```

## 五、开 PR 的必选项

- **Allow edits by maintainers**：`conventions` 说是要求就必勾（`maintainer_can_modify: true`）
- 分支从最新默认分支起（先 fetch）
- 外部贡献走 Fork，不要往上游推分支
- 只含本次改动的 commit（用新分支，别把上个 PR 的 commit 带进来）

## 六、开完立刻做

1. 等 CI 全绿
2. 记录到 `projects/<项目>/ledger.md` 和 `state/prs.jsonl`
3. 更新 `projects/_index.md` 的下一个动作
4. 按 `preferences.md` 的响应时限盯 review（默认 24 小时）

## 七、贡献类踩坑（与工具无关）

| 坑 | 表现 | 处理 |
| --- | --- | --- |
| 上个 PR 的 commit 混进来 | PR 显示多余文件 | 从默认分支新建分支再 cherry-pick |
| 只修撞到的那一处 | 维护者合并时补了同类漏项 | 全库搜一遍同类再提 |
| 注释/正文里的类比没验证 | 维护者只改了你这句注释 | 写进 PR 的文字也要能站住 |
| 文档 PR 里贴了不可见字符 | 引用报错信息时把 BOM 也贴进去 | 贴之前检查字符是否可见 |
| Windows 上 git diff 有 mode 变化 | 可执行位丢失 | 提交前检查 `git diff` 的 mode 行 |

**工具与环境障碍**（PowerShell 编码、`cmd /c`、沙箱拦截等）在 `lessons.md` 第四节，不混在这里。
