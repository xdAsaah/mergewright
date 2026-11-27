# pr-merged

A cross-session workbench for getting open-source PRs merged.

This is not another "how to write a PR" tutorial. It solves one concrete problem: **when you open a new session, how do you find out in a few minutes what is still left in this project, what has already been ruled out, and which candidate to do next?**

English | [中文](README.md)

## Why it exists

Open-source PRs rarely fail because the code is wrong. They fail for reasons like these:

- You reproduce a bug with an injected fault, and the maintainer does not accept it as evidence
- You fix the one place you hit, but three more places have the same gap
- You re-investigate a direction you already ruled out last month
- The maintainer edits your branch directly, and you never figure out what he changed

Memory does not scale to these. This skill turns them into **persistent records**: per-project rules, excluded directions, a post-mortem for every PR, and cross-project lessons, all written to files.

## What it is

A multi-file directory that follows the agent skill convention:

| Layer | Location | Purpose |
| --- | --- | --- |
| Method | `references/` | How to hunt candidates, verify evidence, write PRs, and cut losses |
| Rules | `conventions/<project>.md` | Per-repo commit convention, test requirements, maintainer policy |
| State | `projects/` + `state/` | Ledger, exclusions, candidate pool, event stream |
| Lessons | `lessons.md` | Your own pitfalls, with an escalation path |

## Install

### Trae / Trae CN

```bash
git clone https://github.com/xdAsaah/pr-merged.git ~/.trae-cn/skills/pr-merged
```

### Claude Code

```bash
git clone https://github.com/xdAsaah/pr-merged.git ~/.claude/skills/pr-merged
```

### Other agents

The skill format is portable: `SKILL.md` with YAML frontmatter (`name` + `description`), plus files referenced from the same directory. Drop it into your agent's skills directory.

## First run

After installing, just say "I want to contribute a PR to an open-source project" or "what can I contribute to this repo", and the skill triggers automatically.

It asks three questions on first use:

1. **Goal**: job hunting / learning / joining a community / fixing something you actually use
2. **Time**: how many hours per week you can spend
3. **Stack and domain**: multi-select, each with an "unrestricted" option

Stop-loss limits, response deadlines, and low-value PR policy are **not asked**. They are derived from the first two answers and shown to you for confirmation.

Commit identity is also **not asked**. One command detects it:

```bash
python scripts/prtool.py whoami
```

It checks whether git is installed, whether you are logged in, and whether your email is a noreply address. Whatever is missing, it prints a command you can run directly.

## Commands

```bash
python scripts/prtool.py status  --repo owner/repo --author your-username
python scripts/prtool.py issues  --repo owner/repo
python scripts/prtool.py onboard --path <local-repo>
python scripts/prtool.py append  --file state/prs.jsonl --json '{...}'
python scripts/prtool.py check
python scripts/prtool.py whoami
```

| Subcommand | What it does |
| --- | --- |
| `status` | Computes merge rate, open backlog, and channel activity live; groups your PRs by type; supports GitHub and GitLab |
| `issues` | Scans open issues and flags: beginner-friendly / PR welcome / long unfixed / assigned / open PR exists / merged but unclosed / related PR / multiple failed PRs |
| `onboard` | Reads a local repo and derives commit convention, test commands, PR template, and more |
| `append` | Appends one event to a JSONL ledger |
| `check` | Self-checks the archive: dead links, missing dirs, broken JSON, required sections, hand-written numbers |
| `whoami` | Checks commit identity, covering missing git / not logged in / real email |

Only the Python 3.8+ standard library, no third-party packages. Credentials come from `git credential`; never written to disk, never echoed.

`scripts/*.ps1` are Windows PowerShell equivalents, but they cover only `status` / `onboard` / `append`. **They do not include `issues`, `check`, or `whoami`.**

## Hard rules

A few constraints cannot be bypassed:

1. **Without explicit user approval: do not change code, do not fork, do not open a PR, do not open an issue, do not comment**
2. **A bug fix starts with a failing test that can go red**, proven by mutation testing that it actually guards
3. **Evidence tiers**: injected faults are L1 and cannot be submitted by default; real runs are L2; platform hard limits or contradictions in repo docs are L3
4. **Never hand-write numbers**: merge rates always come from `status`
5. **Every session ends by writing back** to the archive; unwritten work is wasted work
6. **Every session decides the PR type before hunting candidates**, not after. Only five types: `fix` / `test` / `feat` / `perf` / `docs`

## What to do next (four tiers)

Each session checks top-down and stops at the first hit:

| Tier | Condition | Action |
| --- | --- | --- |
| 1 | `candidates.md` has ready-to-submit candidates | Report them and ask whether to submit |
| 2 | Has candidates awaiting verification | Gather evidence first; promote when ready |
| 3 | Both empty, and the project has **0 PRs** | Recommend low-value directions as a door-opener |
| 4 | Both empty, and PRs already submitted | Ask the user which type to do |

The first two tiers skip the type question: the candidate is already in hand, so just ask "shall we do it". Tier 3's "0 PRs" is not "0 merged"; a submitted-but-closed PR counts as having a record.

## How issues are used

Issues are both a candidate source and a record that prevents duplicate work:

```bash
python scripts/prtool.py issues --repo owner/repo
```

Eight flags:

| Flag | What to do |
| --- | --- |
| **Beginner-friendly** (`good first issue`) | Look first |
| **PR welcome** (`help wanted`) | Look first |
| **Long unfixed** (≥90 days unassigned) | See why nobody fixed it |
| **Assigned** | Do not touch |
| **Open PR exists** | Do not touch, you will collide |
| **Merged but unclosed** (PR merged, issue still open) | Verify first, do not redo |
| **Related PR** (PR closed unmerged) | Read the close reason before deciding |
| **Multiple failed PRs ×N** (≥3 attempts) | PR graveyard: real demand, hard to land. Read the failures to find the common blocker |

Linked-PR lookup covers the first 15 issues by default, one extra API request each. Tune with `--linked-limit`, or disable with `--no-linked`. The graveyard threshold is `--min-failed-prs`, default 3.

| Scenario | Rule |
| --- | --- |
| Hunting candidates | Prioritize beginner-friendly / PR welcome |
| Open an issue first? | Check section 3.2 "issue policy" in `conventions/<project>.md`; new features and protocol changes must be discussed first |
| PR body | `Fixes #N` for a full fix, `Refs #N` for a partial one; one PR closes one issue |
| End of session | Update `projects/<project>/issues.md` |

## How the PR type is decided

It is not "do a low-value PR first, then anything goes". Every session decides the type first, from three inputs:

| Input | Where it comes from |
| --- | --- |
| Project stage | Merged count: 0–1 trust building / 1–3 low severity / ≥3 severe line |
| Project acceptance | The "PR type acceptance" table in `conventions/<project>.md`, observed from the last 20 merged PRs |
| Your own history | The "by type" section of `status --author <you>`, giving the merge rate per type |

Then it **asks you which type to do this time**. It does not decide for you. Candidates are archived by type, and the "type review" table in `ledger.md` is refreshed every 5 PRs.

## Layout

```
pr-merged/
├── SKILL.md              Entry point: routing table, hard rules, session flow
├── preferences.md        Your cross-project preferences (filled after first run)
├── lessons.md            Your own pitfalls, with an escalation path
├── references/           Method layer, 9 files
│   ├── init.md           First run: 3 questions + identity check
│   ├── onboard-project.md Entering a repo: derive rules + observe the maintainer
│   ├── choose-project.md Choosing a project: scorecard + statistical traps
│   ├── hunt-candidate.md Hunting candidates: 7 scanning techniques
│   ├── verify.md         Verification: three evidence tiers + mutation testing
│   ├── write-pr.md       Writing the PR: title, body, commit
│   ├── follow-up.md      Following up: review styles + stop-loss
│   ├── severe-scan.md    Severe bugs: invariants + attack-surface matrix
│   └── first-pr.md       First PR and stage strategy
├── conventions/
│   └── _TEMPLATE.md      Rules file template
├── projects/
│   ├── _index.md         Project overview (empty table)
│   └── _template/        Project archive templates (profile / ledger / candidates / excluded / issues)
├── state/
│   ├── prs.jsonl         PR event stream
│   └── scans.jsonl       Scan stream
└── scripts/              6 Python subcommands + 3 PowerShell equivalents
```

## About the empty files

`preferences.md`, `lessons.md`, `projects/_index.md`, and `state/*.jsonl` are **empty templates** in the repo.
They are meant to be filled in after you clone it; they never contain the author's personal data.

If you use the skill directly inside this directory, uncomment the rules at the bottom of `.gitignore` so you do not accidentally commit your own private data.

## License

MIT
