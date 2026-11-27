# pr-merged

**Land your first merged PR. Then keep landing them.**

Most contribution attempts die quietly. Not because the code was wrong, but because nobody told you the maintainer doesn't accept injected faults as evidence, that three other places have the same gap, or that someone already has a PR open for the exact issue you just spent two hours on.

`pr-merged` is a cross-session workbench that fixes that. It hunts real candidates, forces you to prove the bug before writing code, keeps you out of PR pileups, and remembers every project's rules, every excluded direction, and every post-mortem between sessions — so the next one starts in minutes instead of from scratch.

English | [中文](README.zh.md)

## What changes

| Without it | With it |
| --- | --- |
| Re-research the same repo every session | Open `_index.md`, see exactly what is left and what is ruled out |
| Submit a fix the maintainer rejects as "not real evidence" | Evidence tiers force you to reach L2 before writing a line |
| Spend two hours on a bug someone already fixed | `issues` flags open PRs, merged-but-unclosed issues, and PR graveyards |
| Guess which PR type this project actually accepts | Acceptance is observed from the last 20 merged PRs |
| Forget what the maintainer changed in your branch | Every PR gets a post-mortem in `ledger.md` |

## Why PRs fail

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

`pr-merged` is a plain directory following the agent skill convention: `SKILL.md` with YAML frontmatter (`name` + `description`), plus files referenced from the same directory. No build step, no dependencies to install.

**Step 1** — clone it into your agent's skills directory:

```bash
git clone https://github.com/xdAsaah/pr-merged.git <your-agent-skills-dir>/pr-merged
```

Common skills directories:

| Agent | Directory |
| --- | --- |
| Trae / Trae CN | `~/.trae-cn/skills` |
| Claude Code | `~/.claude/skills` |
| Codex | `~/.codex/skills` |
| DSH | `~/.dsh/skills` |

If your agent is not listed, check its docs for the skills directory — the layout is the same everywhere.

**Step 2** — create the data directory:

```bash
python <your-agent-skills-dir>/pr-merged/scripts/prtool.py init
```

This creates `~/.pr-merged/` with the archive skeleton. Existing files are never overwritten, so re-running is safe.

**Only need the method, not the memory?** Copy `SKILL.md` and `references/` alone. They have no dependency on the state files.

### Claude Code plugin

The repo also ships `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, so Claude Code can install it as a plugin instead of a loose skill:

```bash
/plugin marketplace add xdAsaah/pr-merged
/plugin install pr-merged@pr-merged
```

Both manifests pass `claude plugin validate`. The plugin entry only points back at this directory, so the skill files stay exactly where they are — nothing is duplicated.

## Where your work lives

**The skill package and your data are two separate directories.** This is deliberate.

| | Location | Notes |
| --- | --- | --- |
| **Skill package** | Wherever you cloned it | Read-only. Upgrade with `git pull`. One copy per agent |
| **Data directory** | `~/.pr-merged/` by default | Single. All execution records live here, **shared across every agent** |

Why it matters: you may have the skill installed under Trae, Claude Code, and Codex at the same time. If your records lived inside the package, switching agents would show you an empty archive — no memory of what you already investigated, excluded, or submitted. With the data directory split out, every agent opens the same history.

Override the location with `--data <path>` or the `PR_MERGED_HOME` environment variable:

```bash
PR_MERGED_HOME=/path/to/archive python scripts/prtool.py check
```

The package's `_seed/` holds the blank templates. Do not edit files there — they are what `init` copies from.

### Where the code is

Shared records answer "what did I do". They do not answer "**where is the checkout**". The same project can live at different paths in different agents, on different drives, or on different machines.

Every project records its working copy on first entry:

```bash
python scripts/prtool.py where --project <project> --path <local-repo>
```

`onboard --path` writes this automatically. The record lands in `state/workspaces.jsonl` and carries the repo, path, hostname, and OS. Before entering a project, look it up instead of asking the user:

```bash
python scripts/prtool.py where --project <project>
```

It reports each copy as usable / path missing / remote mismatch / other machine, and prints the path to use. If nothing is usable on this machine, it prints the clone command based on the recorded repo.

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
python scripts/prtool.py init
python scripts/prtool.py status  --repo owner/repo --author your-username
python scripts/prtool.py issues  --repo owner/repo
python scripts/prtool.py onboard --path <local-repo>
python scripts/prtool.py where   --project <project> [--path <local-repo>]
python scripts/prtool.py append  --file state/prs.jsonl --json '{...}'
python scripts/prtool.py check
python scripts/prtool.py whoami
```

| Subcommand | What it does |
| --- | --- |
| `init` | Creates the data directory from `_seed/`; never overwrites existing files |
| `status` | Computes merge rate, open backlog, and channel activity live; groups your PRs by type; supports GitHub and GitLab |
| `issues` | Scans open issues and flags: beginner-friendly / PR welcome / long unfixed / assigned / open PR exists / merged but unclosed / related PR / multiple failed PRs |
| `onboard` | Reads a local repo and derives commit convention, test commands, PR template, and more; records the checkout path |
| `where` | Looks up or records where a project's checkout lives on each machine; flags missing paths and remote mismatches |
| `append` | Appends one event to a JSONL ledger (relative paths resolve against the data directory) |
| `check` | Self-checks both the package and the data archive |
| `whoami` | Checks commit identity, covering missing git / not logged in / real email |

`init`, `append`, `check`, `onboard`, and `where` accept `--data <path>` to point at a different archive.

Only the Python 3.8+ standard library, no third-party packages. Credentials come from `git credential`; never written to disk, never echoed.

`scripts/*.ps1` are Windows PowerShell equivalents, but they cover only `status` / `onboard` / `append`. **They do not include `issues`, `check`, `whoami`, or `where`.**

## Hard rules

A few constraints cannot be bypassed:

1. **Without explicit user approval: do not change code, do not fork, do not open a PR, do not open an issue, do not comment**
2. **A bug fix starts with a failing test that can go red**, proven by mutation testing that it actually guards
3. **Evidence tiers**: injected faults are L1 and cannot be submitted by default; real runs are L2; platform hard limits or contradictions in repo docs are L3
4. **Never hand-write numbers**: merge rates always come from `status`
5. **Every session ends by writing back** to the archive; unwritten work is wasted work
6. **Every session decides the PR type before hunting candidates**, not after. Only five types: `fix` / `test` / `feat` / `perf` / `docs`

## What to do next (five tiers)

Each session checks top-down and stops at the first hit:

| Tier | Condition | Action |
| --- | --- | --- |
| 0 | `candidates.md` has an in-progress entry | Take it over: read the recorded branch, inspect `git log` / `git diff`, finish it |
| 1 | Has ready-to-submit candidates | Report them and ask whether to submit |
| 2 | Has candidates awaiting verification | Gather evidence first; promote when ready |
| 3 | All empty, and the project has **0 PRs** | Recommend low-value directions as a door-opener |
| 4 | All empty, and PRs already submitted | Ask the user which type to do |

Tier 0 exists because a half-finished branch is the one thing a broken session can silently waste. The record is written **before** the branch is created, so the next agent knows to continue rather than restart.

Tiers 1 and 2 skip the type question: the candidate is already in hand, so just ask "shall we do it". Tier 3's "0 PRs" is not "0 merged"; a submitted-but-closed PR counts as having a record.

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
pr-merged/                ← skill package (read-only, one per agent)
├── SKILL.md              Entry point: routing table, hard rules, session flow
├── .claude-plugin/       Claude Code plugin + marketplace manifests
├── README.md / README.zh.md
├── references/           Method layer, 9 files
│   ├── init.md           First run: create data dir, 3 questions, identity check
│   ├── onboard-project.md Entering a repo: derive rules + observe the maintainer
│   ├── choose-project.md Choosing a project: scorecard + statistical traps
│   ├── hunt-candidate.md Hunting candidates: 7 scanning techniques
│   ├── verify.md         Verification: three evidence tiers + mutation testing
│   ├── write-pr.md       Writing the PR: title, body, commit
│   ├── follow-up.md      Following up: review styles + stop-loss
│   ├── severe-scan.md    Severe bugs: invariants + attack-surface matrix
│   └── first-pr.md       First PR and stage strategy
├── scripts/              7 Python subcommands + 3 PowerShell equivalents
└── _seed/                Blank templates, copied by `init`
    ├── preferences.md
    ├── lessons.md
    ├── conventions/_TEMPLATE.md
    ├── projects/_index.md + _template/ (profile/ledger/candidates/excluded/issues)
    └── state/prs.jsonl + scans.jsonl + workspaces.jsonl

~/.pr-merged/             ← your data (shared by every agent)
├── preferences.md
├── lessons.md
├── conventions/<project>.md
├── projects/_index.md + <project>/
└── state/*.jsonl         prs / scans / workspaces
```

## About `_seed/`

The templates in `_seed/` are copied to your data directory by `init`. They never contain the author's personal data.

Do not edit files inside `_seed/` — they are the source that future `init` runs copy from. Edit your own copies under `~/.pr-merged/` instead.

## License

MIT
