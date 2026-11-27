# 项目台账

> 每个项目一行。**每次会话结束更新本表**：状态、下一个动作、最后更新时间。
> 详细档案在 `projects/<项目>/`，规则在 `conventions/<项目>.md`。
> **已合并数不要手写**——用 `scripts/prtool.py status --repo <owner/repo> --author <你>` 现算，本表只记「状态」和「下一个动作」这类机器算不出的东西。

| 项目 | 状态 | 规则文件 | 下一个动作 | 最后更新 |
| --- | --- | --- | --- | --- |

> 还没有项目。进第一个项目见下方「新项目怎么加」。

## 状态取值

- **探索中**：还没提过 PR，或首 PR 在审
- **信任建立中**：已有 1 个合并，正在做第二、三枪
- **主力**：信任已建立，可持续挖候选
- **已止损**：触发 `preferences.md` 的止损条件
- **已收尾**：达到目标 PR 数，除非有新线索不再投入

## 已收尾 / 已止损的项目档案怎么处理

**不删档案，但降级维护**：

| 保留什么 | 为什么 |
| --- | --- |
| `_index.md` 的这一行 | 证明去过、结果如何，避免重复评估 |
| 该项目 `ledger.md` | PR 号和结果要能查回来 |
| `excluded.md` 的「方向性排除」 | 防止下次重新踩同一条死路 |
| `profile.md` | 只有重新投入时才需要，可以停止更新 |

**可以不建**：`conventions/<项目>.md`（不再提 PR 就不需要规则）、`candidates.md`（不再挖候选）。

重新投入时再补跑 `onboard-project.md` 重建规则——不要指望旧规则还有效。

## 新项目怎么加

1. 跑 `scripts/prtool.py onboard --path <本地仓库>` 拿到推导结果
2. 按 `conventions/_TEMPLATE.md` 建 `conventions/<项目>.md`，把推导结果粘进去，再补观察项
3. 复制 `projects/_template/` 为 `projects/<项目>/`，填 `profile.md`
4. 在此表加一行，状态填「探索中」
5. 在 `state/prs.jsonl` 追加首条记录时带上 `"project":"<项目名>"`
6. 跑 `python scripts/prtool.py check` 确认没有死链和坏 JSON

**项目级的问题**（投入多久、有没有读不出的私有偏好）在 `references/onboard-project.md` 问，不要重复问 `preferences.md` 里已经答过的。
