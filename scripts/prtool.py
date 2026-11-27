#!/usr/bin/env python3
"""开源 PR 工作台脚本（跨平台，只用标准库，Python 3.8+）。

与同目录的 .ps1 等价，Windows / macOS / Linux 都能跑：

  python prtool.py status  --repo owner/repo [--author 你] [--platform github|gitlab] [--site host]
  python prtool.py onboard --path <本地仓库>
  python prtool.py append  --file state/prs.jsonl --json '{"ts":"...","project":"..."}'

凭据从 git credential 取（不落盘、不回显），和 .ps1 走同一个凭据库。
"""

import argparse
import json
import os
import platform
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------- 通用

def run(cmd, cwd=None):
    """跑一个命令，失败返回空串。"""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except (FileNotFoundError, OSError):
        return ""
    return p.stdout or ""


def get_token(host):
    """从 git 凭据库取 token。Python 能正确写 stdin，不需要 .ps1 那套临时文件。"""
    env = dict(os.environ, GCM_INTERACTIVE="Never")
    try:
        p = subprocess.run(["git", "credential", "fill"],
                           input=f"protocol=https\nhost={host}\n\n",
                           capture_output=True, text=True, env=env, timeout=30)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    for line in (p.stdout or "").splitlines():
        if line.startswith("password="):
            return line[len("password="):].strip()
    return None


def get_credential_username(host):
    """从 git 凭据库取用户名（不含密码）。拿不到返回 None。"""
    env = dict(os.environ, GCM_INTERACTIVE="Never")
    try:
        p = subprocess.run(["git", "credential", "fill"],
                           input=f"protocol=https\nhost={host}\n\n",
                           capture_output=True, text=True, env=env, timeout=30)
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None
    for line in (p.stdout or "").splitlines():
        if line.startswith("username="):
            return line[len("username="):].strip() or None
    return None


def as_time(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        d = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def days_since(value):
    t = as_time(value)
    if not t:
        return None
    return round((datetime.now(timezone.utc) - t).total_seconds() / 86400, 1)


def api_get(url, headers):
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"警告：请求失败 {url} : HTTP {e.code}", file=sys.stderr)
    except Exception as e:
        print(f"警告：请求失败 {url} : {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------- 目录约定

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录里应该有什么；init 时从包内的 _seed/ 拷
DATA_ITEMS = ("preferences.md", "lessons.md", "conventions", "projects", "state")


def data_root(explicit=""):
    """数据目录：--data > $PR_MERGED_HOME > ~/.pr-merged。

    所有 projects/ conventions/ state/ preferences.md lessons.md 都在这里，
    不在 skill 包里——这样多个 agent 可以共用同一份执行记录。
    """
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env = os.environ.get("PR_MERGED_HOME", "").strip()
    if env:
        return os.path.abspath(os.path.expanduser(env))
    return os.path.join(os.path.expanduser("~"), ".pr-merged")


def data_file(rel, explicit=""):
    return os.path.join(data_root(explicit), rel)


def seed_dir():
    return os.path.join(PACKAGE_ROOT, "_seed")


# ---------------------------------------------------------------- 工作副本

def host_tag():
    try:
        return socket.gethostname() or "unknown"
    except OSError:
        return "unknown"


def os_tag():
    return platform.system() or "unknown"


def norm_repo(value):
    """把 remote url 或 owner/repo 归一成小写的 owner/repo。"""
    s = (value or "").strip()
    if not s:
        return ""
    has_host = False
    m = re.match(r"^(https?://|ssh://|git://|git@)", s)
    if m:
        s = s[m.end():]
        has_host = True
        s = s.replace(":", "/", 1)      # git@host:owner/repo 的冒号
    s = re.sub(r"\.git$", "", s)
    parts = [p for p in s.strip("/").split("/") if p]
    if has_host:
        parts = parts[1:]               # 去掉 host（含 ssh 的端口段）
    return "/".join(parts[-2:]).lower()


def git_remote_repo(path):
    return norm_repo(run(["git", "-C", path, "remote", "get-url", "origin"]).strip())


def git_branch(path):
    """当前分支；detached 时返回短 SHA。"""
    b = run(["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"]).strip()
    if b and b != "HEAD":
        return b
    return run(["git", "-C", path, "rev-parse", "--short", "HEAD"]).strip()


def git_dirty(path):
    """未提交改动：返回 (文件数, 是否有未推送提交)。"""
    st = run(["git", "-C", path, "status", "--porcelain"]).strip()
    changed = len([ln for ln in st.splitlines() if ln.strip()])
    ahead = 0
    ab = run(["git", "-C", path, "rev-list", "--count", "@{u}..HEAD"]).strip()
    if ab.isdigit():
        ahead = int(ab)
    return changed, ahead


def read_workspaces(data):
    """读 state/workspaces.jsonl，同 (project, host, path) 只保留最后一条。"""
    path = os.path.join(data, "state", "workspaces.jsonl")
    latest = {}
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            key = (obj.get("project", ""), obj.get("host", ""), obj.get("path", ""))
            latest[key] = obj
    rows = list(latest.values())
    rows.sort(key=lambda r: (r.get("project", ""), r.get("host", ""), r.get("path", "")))
    return rows


def record_workspace(project, path, data, repo=""):
    """把本地工作副本路径写进 state/workspaces.jsonl，同 (项目, 机器, 路径) 覆盖旧记录。"""
    full = os.path.abspath(os.path.expanduser(path))
    rec = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "project": project,
        "repo": repo or git_remote_repo(full),
        "path": full,
        "host": host_tag(),
        "os": os_tag(),
    }
    target = os.path.join(data, "state", "workspaces.jsonl")
    os.makedirs(os.path.dirname(target), exist_ok=True)

    kept = []
    if os.path.isfile(target):
        with open(target, encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(obj, dict):
                    continue
                same = (obj.get("project"), obj.get("host"), obj.get("path"))
                if same != (rec["project"], rec["host"], rec["path"]):
                    kept.append(obj)
    kept.append(rec)
    kept.sort(key=lambda r: (r.get("project", ""), r.get("host", ""), r.get("path", "")))

    with open(target, "w", encoding="utf-8", newline="\n") as f:
        for obj in kept:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return rec


def cmd_where(args):
    """查/记某个项目在哪些机器上、哪个目录做过。"""
    data = data_root(args.data)
    this_host = host_tag()

    if args.path:
        path = os.path.abspath(os.path.expanduser(args.path))
        if not os.path.isdir(path):
            print(f"路径不存在：{path}", file=sys.stderr)
            return 1
        project = args.project or os.path.basename(path.rstrip("\\/"))
        rec = record_workspace(project, path, data, args.repo)
        print(f"已记录工作副本 -> {os.path.join(data, 'state', 'workspaces.jsonl')}")
        print(f"  {rec['project']}  {rec['path']}  ({rec['host']} / {rec['os']})")
        return 0

    rows = read_workspaces(data)
    if args.project:
        rows = [r for r in rows if r.get("project", "").lower() == args.project.lower()]
    if args.repo:
        want = norm_repo(args.repo)
        rows = [r for r in rows if norm_repo(r.get("repo", "")) == want]
    if not rows:
        if args.project or args.repo:
            print("没有记录。这个项目还没在任何一个 agent 里跑过 onboard，")
            print("或者记录是在旧版本写的。跑一次：")
            print("  python scripts/prtool.py onboard --path <本地仓库>")
        else:
            print("还没有任何工作副本记录。")
            print("进项目时跑 onboard --path，会自动记下路径。")
        return 0

    print(f"{'项目':<18} {'本机':<8} {'分支':<26} {'状态':<12} 路径")
    for r in rows:
        p = r.get("path", "")
        exists = os.path.isdir(p)
        branch, dirty = "-", "-"
        if not exists:
            mark = "别的机器" if r.get("host") != this_host else "缺失"
        else:
            cur = git_remote_repo(p)
            want = norm_repo(r.get("repo", ""))
            mark = "remote不符" if cur and want and cur != want else "可用"
            branch = git_branch(p) or "-"
            if branch == "-":
                dirty = "非 git 目录"
            else:
                n, ahead = git_dirty(p)
                bits = []
                if n:
                    bits.append(f"{n} 处未提交")
                if ahead:
                    bits.append(f"{ahead} 个未推送")
                dirty = "，".join(bits) if bits else "干净"
        print(f"{r.get('project',''):<18} {mark:<8} {branch:<26} {dirty:<12} {p}")

    print()
    usable = [r for r in rows if os.path.isdir(r.get("path", ""))]
    if args.project and usable:
        r = usable[0]
        p = r["path"]
        print(f"本机可用：{p}")
        branch = git_branch(p)
        if branch:
            print(f"当前分支：{branch}")
        n, ahead = git_dirty(p)
        if n or ahead:
            print(f"有未完成状态：{n} 处未提交改动" + (f"，{ahead} 个提交未推送" if ahead else ""))
            print("动手前先看 git diff / git log，可能是上一个 agent 的半成品，别重做。")
        else:
            print("工作区干净，可以直接开工。")
        print("不要问用户要仓库位置。")
    elif not usable:
        print("本机没有可用的工作副本。先 clone 一份，再跑：")
        repo = rows[0].get("repo", "") or "<owner/repo>"
        print(f"  git clone https://github.com/{repo}.git <你要放的目录>")
        print(f"  python scripts/prtool.py where --project {rows[0].get('project', '<项目>')} --path <你要放的目录>")
    else:
        print("加 --project <项目> 只看一个，直接给出该用的路径和分支状态。")
    return 0


# ---------------------------------------------------------------- init

def cmd_init(args):
    """建数据目录骨架：从包内 _seed/ 拷模板，已存在的文件不覆盖。"""
    root = data_root(args.data)
    seed = seed_dir()
    print(f"数据目录：{root}")

    if not os.path.isdir(seed):
        print(f"包内缺少 _seed/：{seed}", file=sys.stderr)
        print("这个 skill 包装不完整，重新 clone 一次。", file=sys.stderr)
        return 1

    os.makedirs(root, exist_ok=True)
    created, skipped = [], []

    for name in DATA_ITEMS:
        src = os.path.join(seed, name)
        dst = os.path.join(root, name)
        if not os.path.exists(src):
            continue
        if os.path.isdir(src):
            for dirpath, _, files in os.walk(src):
                rel = os.path.relpath(dirpath, src)
                target_dir = dst if rel == "." else os.path.join(dst, rel)
                os.makedirs(target_dir, exist_ok=True)
                for fn in files:
                    s = os.path.join(dirpath, fn)
                    d = os.path.join(target_dir, fn)
                    if os.path.exists(d):
                        skipped.append(os.path.relpath(d, root))
                        continue
                    with open(s, "rb") as f:
                        data = f.read()
                    with open(d, "wb") as f:
                        f.write(data)
                    created.append(os.path.relpath(d, root))
        else:
            if os.path.exists(dst):
                skipped.append(name)
                continue
            with open(src, "rb") as f:
                data = f.read()
            with open(dst, "wb") as f:
                f.write(data)
            created.append(name)

    if created:
        print(f"\n新建 {len(created)} 个：")
        for c in created:
            print(f"  + {c}")
    if skipped:
        print(f"\n已存在，跳过 {len(skipped)} 个（不会覆盖你的数据）：")
        for s in skipped:
            print(f"  = {s}")
    if not created and not skipped:
        print("\n没有可拷贝的模板。")

    print()
    print("下一步：")
    print(f"  1. 填 {os.path.join(root, 'preferences.md')}（首次使用问 3 个问题）")
    print(f"  2. python {os.path.join(PACKAGE_ROOT, 'scripts', 'prtool.py')} check")
    return 0


# ---------------------------------------------------------------- status

def convert_pull(raw, platform, author):
    if platform == "github":
        return {
            "number": raw.get("number"),
            "title": raw.get("title"),
            "author": (raw.get("user") or {}).get("login"),
            "created": raw.get("created_at"),
            "merged": raw.get("merged_at"),
            "state": raw.get("state"),
            "assoc": raw.get("author_association"),
            "is_bot": (raw.get("user") or {}).get("type") == "Bot",
        }
    login = (raw.get("author") or {}).get("username")
    return {
        "number": raw.get("iid"),
        "title": raw.get("title"),
        "author": login,
        "created": raw.get("created_at"),
        "merged": raw.get("merged_at") if raw.get("state") == "merged" else None,
        "state": "closed" if raw.get("state") == "merged" else raw.get("state"),
        "assoc": "SELF" if login == author else "OTHER",
        "is_bot": bool(re.match(r"^(dependabot|renovate|bot)", login or "")),
    }


def cmd_status(args):
    platform = args.platform
    site = args.site or ("github.com" if platform == "github" else "gitlab.com")
    token = get_token(site)
    if not token:
        print(f"拿不到 {site} 的 token：先 git credential 登录一次", file=sys.stderr)
        return 1

    api = "https://api.github.com" if platform == "github" else f"https://{site}/api/v4"
    if platform == "github":
        headers = {"Authorization": f"Bearer {token}",
                   "Accept": "application/vnd.github+json",
                   "User-Agent": "pr-merged"}
    else:
        headers = {"PRIVATE-TOKEN": token, "User-Agent": "pr-merged"}

    proj = urllib.parse.quote(args.repo, safe="")
    repo = args.repo
    author = args.author

    print(f"=== {platform} : {repo} ===")

    if platform == "github":
        info = api_get(f"{api}/repos/{repo}", headers)
        if info:
            print(f"stars={info.get('stargazers_count')}  pushed={info.get('pushed_at')}"
                  f"  open_issues(incl PR)={info.get('open_issues_count')}")
    else:
        info = api_get(f"{api}/projects/{proj}", headers)
        if info:
            print(f"stars={info.get('star_count')}  last_activity={info.get('last_activity_at')}")

    # open PR
    if platform == "github":
        raw = api_get(f"{api}/repos/{repo}/pulls?state=open&per_page=100", headers)
    else:
        raw = api_get(f"{api}/projects/{proj}/merge_requests?state=opened&per_page=100", headers)
    open_pulls = [convert_pull(p, platform, author) for p in (raw or [])]
    print(f"open: {len(open_pulls)}")
    if open_pulls:
        ordered = sorted(open_pulls, key=lambda p: as_time(p["created"]) or datetime.max.replace(tzinfo=timezone.utc))
        oldest = ordered[0]
        print(f"  oldest: #{oldest['number']} 等了 {days_since(oldest['created'])} 天 ({oldest['title']})")
        for p in ordered:
            if platform == "github":
                cm = api_get(f"{api}/repos/{repo}/issues/{p['number']}/comments", headers)
            else:
                cm = api_get(f"{api}/projects/{proj}/merge_requests/{p['number']}/notes", headers)
            others = [c for c in (cm or []) if (c.get("user") or {}).get("login") != p["author"]]
            print(f"  #{p['number']} [{p['author']}] 他人评论 {len(others)} 条  {p['title']}")

    # 最近 20 个已关闭
    if platform == "github":
        raw = api_get(f"{api}/repos/{repo}/pulls?state=closed&per_page=20&sort=updated&direction=desc", headers)
    else:
        raw = api_get(f"{api}/projects/{proj}/merge_requests?state=closed&per_page=20&order_by=updated_at", headers)
    closed = [convert_pull(p, platform, author) for p in (raw or [])]
    if closed:
        human = [p for p in closed if not p["is_bot"]]
        merged = [p for p in human if p["merged"]]
        if platform == "github":
            external = [p for p in merged if p["assoc"] not in ("MEMBER", "OWNER", "COLLABORATOR")]
        else:
            external = [p for p in merged if p["assoc"] == "OTHER"]
        print(f"近 20 个已关闭（剔 bot）: {len(human)}  合并 {len(merged)}  外部作者合并 {len(external)}")
        if merged:
            last = max(merged, key=lambda p: as_time(p["merged"]) or datetime.min.replace(tzinfo=timezone.utc))
            print(f"  最近合并: #{last['number']} at {last['merged']}")
        authors = sorted({p["author"] for p in external})
        print(f"  外部合并作者: {len(authors)} 人 -> {', '.join(authors)}")

    # 指定作者的全部 PR
    if author:
        if platform == "github":
            q = api_get(f"{api}/search/issues?q=repo:{repo}+author:{author}+type:pr&per_page=100", headers)
            items = [{"number": it.get("number"), "title": it.get("title"),
                      "merged": (it.get("pull_request") or {}).get("merged_at"),
                      "state": it.get("state")} for it in ((q or {}).get("items") or [])]
            total = (q or {}).get("total_count", len(items))
        else:
            raw = api_get(f"{api}/projects/{proj}/merge_requests?author_username={author}&per_page=100", headers)
            items = [{"number": it.get("iid"), "title": it.get("title"),
                      "merged": it.get("merged_at") if it.get("state") == "merged" else None,
                      "state": it.get("state")} for it in (raw or [])]
            total = len(items)
        m = [i for i in items if i["merged"]]
        c = [i for i in items if not i["merged"] and i["state"] == "closed"]
        o = [i for i in items if i["state"] in ("open", "opened")]
        print()
        print(f"=== {author} 的 PR ===")
        print(f"总数 {total}  合并 {len(m)}  关闭未合并 {len(c)}  在审 {len(o)}")
        for i in sorted(items, key=lambda x: x["number"] or 0):
            state = f"merged {i['merged']}" if i["merged"] else i["state"]
            print(f"  #{i['number']} [{state}] {i['title']}")

        # 按类型统计：从 conventional commit 前缀解析，解析不出的归到「无前缀」
        def pr_type(title):
            mm = re.match(r"^([a-z]+)(\([^)]+\))?!?:", title or "")
            t = mm.group(1) if mm else ""
            return t if t in ("fix", "test", "feat", "perf", "docs") else "(其他)"

        stats = {}
        for i in items:
            t = pr_type(i["title"])
            s = stats.setdefault(t, {"total": 0, "merged": 0, "closed": 0, "open": 0})
            s["total"] += 1
            if i["merged"]:
                s["merged"] += 1
            elif i["state"] in ("open", "opened"):
                s["open"] += 1
            elif i["state"] == "closed":
                s["closed"] += 1
        if stats:
            print()
            print(f"=== {author} 的 PR 按类型 ===")
            order = ["fix", "test", "feat", "perf", "docs", "(其他)"]
            for t in order + [k for k in stats if k not in order]:
                s = stats.get(t)
                if not s:
                    continue
                done = s["merged"] + s["closed"]
                rate = f"{s['merged'] * 100 // done}%" if done else "—"
                print(f"  {t:<7} 提交 {s['total']:>2}  合并 {s['merged']:>2}  "
                      f"关闭 {s['closed']:>2}  在审 {s['open']:>2}  合并率 {rate}")
    return 0


# ---------------------------------------------------------------- issues

def linked_prs_github(api, repo, num, headers):
    """查某个 issue 的关联 PR（cross-referenced 事件）。"""
    events = api_get(f"{api}/repos/{repo}/issues/{num}/timeline?per_page=100", headers)
    out, seen = [], set()
    for e in events or []:
        if e.get("event") != "cross-referenced":
            continue
        src = (e.get("source") or {}).get("issue") or {}
        if not src.get("pull_request"):
            continue
        pn = src.get("number")
        if pn in seen:
            continue
        seen.add(pn)
        out.append({
            "number": pn,
            "title": (src.get("title") or "")[:60],
            "state": src.get("state"),
            "merged": (src.get("pull_request") or {}).get("merged_at"),
            "author": (src.get("user") or {}).get("login"),
        })
    return out


def linked_prs_gitlab(api, proj, iid, headers):
    """查某个 issue 的关联 MR。"""
    mrs = api_get(f"{api}/projects/{proj}/issues/{iid}/related_merge_requests", headers)
    return [{
        "number": m.get("iid"),
        "title": (m.get("title") or "")[:60],
        "state": m.get("state"),
        "merged": m.get("merged_at"),
        "author": (m.get("author") or {}).get("username"),
    } for m in (mrs or [])]


def cmd_issues(args):
    """扫 open issue，标出 good first issue / 长期未修 / 维护者说 PR welcome 的。"""
    platform = args.platform
    site = args.site or ("github.com" if platform == "github" else "gitlab.com")
    token = get_token(site)
    if not token:
        print(f"拿不到 {site} 的 token：先 git credential 登录一次", file=sys.stderr)
        return 1

    api = "https://api.github.com" if platform == "github" else f"https://{site}/api/v4"
    if platform == "github":
        headers = {"Authorization": f"Bearer {token}",
                   "Accept": "application/vnd.github+json",
                   "User-Agent": "pr-merged"}
    else:
        headers = {"PRIVATE-TOKEN": token, "User-Agent": "pr-merged"}

    repo = args.repo
    proj = urllib.parse.quote(repo, safe="")

    print(f"=== {platform} : {repo} 的 open issue ===")

    if platform == "github":
        # issues 接口会混入 PR，用 type:issue 排除
        q = api_get(f"{api}/search/issues?q=repo:{repo}+type:issue+state:open"
                    f"&per_page={args.limit}&sort=updated&order=desc", headers)
        raw = (q or {}).get("items") or []
    else:
        raw = api_get(f"{api}/projects/{proj}/issues?state=opened&per_page={args.limit}"
                      f"&order_by=updated_at", headers) or []

    if not raw:
        print("没有 open issue。")
        return 0

    now = datetime.now(timezone.utc)
    rows = []
    for it in raw:
        num = it.get("number") or it.get("iid")
        title = (it.get("title") or "").strip()
        created = it.get("created_at")
        updated = it.get("updated_at")
        labels = [l.get("name", "") if isinstance(l, dict) else str(l)
                  for l in (it.get("labels") or [])]
        comments = it.get("comments", 0)
        assignees = it.get("assignees") or []
        if platform == "gitlab" and it.get("assignee"):
            assignees = [it["assignee"]]

        # 判定标签
        tags = []
        low = " ".join(labels).lower()
        if re.search(r"good first issue|good-first-issue|beginner|easy|starter", low):
            tags.append("新手友好")
        if re.search(r"help wanted|pr welcome|contributions welcome", low):
            tags.append("欢迎 PR")
        if re.search(r"bug|confirmed", low):
            tags.append("bug")
        if assignees:
            tags.append("已认领")

        age = None
        if created:
            t = as_time(created)
            if t:
                age = round((now - t).total_seconds() / 86400)
        idle = None
        if updated:
            t = as_time(updated)
            if t:
                idle = round((now - t).total_seconds() / 86400)

        if age is not None and age >= 90 and not assignees:
            tags.append("长期未修")
        if idle is not None and idle >= 60 and comments == 0 and not assignees:
            tags.append("无人回应")

        rows.append({"num": num, "title": title, "age": age, "idle": idle,
                     "comments": comments, "labels": labels, "tags": tags,
                     "prs": [], "pr_checked": False})

    # 查关联 PR：只查前 N 个（默认 15），避免打满 rate limit
    if not args.no_linked and rows:
        # 先按初排顺序，只查最可能做的那些；已认领的不查
        rows.sort(key=lambda r: (1 if "已认领" in r["tags"] else 0, -(r["age"] or 0)))
        budget = args.linked_limit
        checked = 0
        for r in rows:
            if checked >= budget:
                break
            if "已认领" in r["tags"]:
                continue
            if platform == "github":
                prs = linked_prs_github(api, repo, r["num"], headers)
            else:
                prs = linked_prs_gitlab(api, proj, r["num"], headers)
            r["prs"] = prs
            r["pr_checked"] = True
            checked += 1
            if prs:
                open_pr = [p for p in prs if p["state"] in ("open", "opened")]
                merged_pr = [p for p in prs if p["merged"]]
                failed_pr = [p for p in prs if p["state"] == "closed" and not p["merged"]]
                if open_pr:
                    r["tags"].append("已有 PR 在审")
                elif merged_pr:
                    r["tags"].append("已修待确认")
                else:
                    r["tags"].append("有相关 PR")
                # PR 坟场：多次尝试都没合进去，说明问题难做或要求不明确
                if len(failed_pr) >= args.min_failed_prs:
                    r["tags"].append(f"多 PR 未合×{len(failed_pr)}")
                    r["failed_prs"] = failed_pr

    # 排序：新手友好/欢迎 PR 优先；已有 PR 的压到最后
    def rank(r):
        score = 0
        if "新手友好" in r["tags"]:
            score -= 20
        if "欢迎 PR" in r["tags"]:
            score -= 15
        if "已认领" in r["tags"]:
            score += 30
        if "已有 PR 在审" in r["tags"]:
            score += 40
        if "已修待确认" in r["tags"]:
            score += 25
        if r.get("failed_prs"):
            score += 35
        return (score, -(r["age"] or 0))

    rows.sort(key=rank)

    print(f"共 {len(rows)} 个\n")
    for r in rows:
        tagstr = f"  [{', '.join(r['tags'])}]" if r["tags"] else ""
        print(f"  #{r['num']} {r['title'][:70]}{tagstr}")
        meta = []
        if r["age"] is not None:
            meta.append(f"开了 {r['age']} 天")
        if r["idle"] is not None:
            meta.append(f"静默 {r['idle']} 天")
        meta.append(f"评论 {r['comments']}")
        if r["labels"]:
            meta.append(", ".join(r["labels"][:4]))
        print(f"      {' · '.join(meta)}")
        # 坟场 issue 只显示最近 3 个失败 PR，避免刷屏
        shown = r["prs"]
        if r.get("failed_prs") and len(shown) > 3:
            keep = [p for p in shown if p not in r["failed_prs"]][:1]
            keep += r["failed_prs"][:3]
            shown = keep
            print(f"      （另有 {len(r['prs']) - len(shown)} 个关联 PR 未显示）")
        for p in shown:
            state = "merged" if p["merged"] else p["state"]
            print(f"      ↳ PR #{p['number']} [{state}] {p['title']}  @{p['author']}")

    # 汇总提示
    print()
    good = [r for r in rows if "新手友好" in r["tags"] or "欢迎 PR" in r["tags"]]
    stale = [r for r in rows if "长期未修" in r["tags"]]
    claimed = [r for r in rows if "已认领" in r["tags"]]
    has_pr = [r for r in rows if "已有 PR 在审" in r["tags"]]
    done = [r for r in rows if "已修待确认" in r["tags"]]
    grave = [r for r in rows if r.get("failed_prs")]
    print(f"可优先看：{len(good)} 个（新手友好 / 欢迎 PR）")
    print(f"长期未修：{len(stale)} 个（≥90 天且未认领）")
    print(f"已认领：{len(claimed)} 个（不要碰）")
    if not args.no_linked:
        print(f"已有 PR 在审：{len(has_pr)} 个（别重复做）")
        print(f"已修待确认：{len(done)} 个（PR 已合，issue 可能忘关）")
        print(f"多 PR 未合：{len(grave)} 个（≥{args.min_failed_prs} 次尝试失败，先问维护者）")
    return 0


# ---------------------------------------------------------------- onboard

def cmd_onboard(args):
    path = args.path
    if not os.path.isdir(path):
        print(f"路径不存在：{path}", file=sys.stderr)
        return 1
    root = os.path.abspath(path)

    def g(*a):
        return run(["git", *a], cwd=root).strip()

    print(f"# 采集结果：{os.path.basename(root)}")
    print()
    print(f"> 采集时间 {datetime.now().strftime('%Y-%m-%d %H:%M')}，路径 {root}")
    print("> 全部标 [推导]。观察项和维护者政策需要跑 prtool.py status 后再填。")

    print()
    print("## 1. 托管与提交")
    print()
    print("| 项 | 值 | 来源 |")
    print("| --- | --- | --- |")

    remote = g("remote", "get-url", "origin")
    if not remote:
        # origin 不一定是 upstream 的别名（fork 工作流里常叫 upstream），退到任意一个
        remotes = [ln for ln in g("remote", "-v").splitlines() if ln.strip()]
        if remotes:
            remote = remotes[0].split()[1]
    if "github.com" in remote:
        platform = "GitHub"
    elif "gitlab" in remote:
        platform = "GitLab"
    else:
        platform = "未知"
    m = re.search(r"[:/]([^/:]+/[^/]+?)(\.git)?$", remote)
    repo_name = m.group(1) if m else "未知"
    default_branch = ""
    for r in ("origin", "upstream"):
        default_branch = re.sub(r"^refs/remotes/%s/" % r, "",
                                g("symbolic-ref", f"refs/remotes/{r}/HEAD")).strip()
        if default_branch:
            break
    if not default_branch:
        default_branch = g("config", "--get", "init.defaultBranch") or "main"

    print(f"| 平台 | {platform} | [推导] remote url |")
    print(f"| 仓库 | {repo_name} | [推导] |")
    print(f"| 默认分支 | {default_branch} | [推导] |")

    contrib = None
    for name in sorted(os.listdir(root)):
        if name.upper().startswith("CONTRIBUTING"):
            contrib = os.path.join(root, name)
            break
    if contrib:
        try:
            with open(contrib, encoding="utf-8", errors="replace") as f:
                c = f.read()
        except OSError:
            c = ""
        if re.search(r"claude/|codex/|dependabot/", c):
            print(f"| 允许的分支名前缀 | 见 CONTRIBUTING（有前缀限制） | [推导] {os.path.basename(contrib)} |")
        if "Allow edits by maintainers" in c:
            print(f"| 必须勾 Allow edits by maintainers | 是 | [推导] {os.path.basename(contrib)} |")
        if re.search(r"CLA|Contributor License", c):
            print(f"| 需要签署 CLA | 是 | [推导] {os.path.basename(contrib)} |")

    subjects = [s for s in g("log", "--format=%s", "-50").splitlines() if s.strip()]
    counts = {}
    for s in subjects:
        mm = re.match(r"^([a-z]+)(\([^)]+\))?!?:", s)
        counts[mm.group(1) if mm else "(无前缀)"] = counts.get(mm.group(1) if mm else "(无前缀)", 0) + 1
    top = " / ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda x: -x[1])[:3])
    if re.search(r"fix|feat|docs", top):
        print(f"| commit 规范 | conventional commits | [推导] 近 50 提交：{top} |")
    else:
        print(f"| commit 规范 | 无固定前缀 | [推导] 近 50 提交：{top} |")

    langs = {}
    for s in [x for x in g("log", "--format=%s", "-20").splitlines() if x.strip()]:
        key = "中文" if re.search(r"[\u4e00-\u9fff]", s) else "英文"
        langs[key] = langs.get(key, 0) + 1
    if langs:
        print(f"| commit 语言 | {max(langs, key=langs.get)} | [推导] 近 20 提交 |")

    tpl = []
    gh = os.path.join(root, ".github")
    if os.path.isdir(gh):
        for dirpath, _, files in os.walk(gh):
            for f in files:
                if "pull_request_template" in f.lower():
                    tpl.append(os.path.join(dirpath, f))
    gl = os.path.join(root, ".gitlab", "merge_request_templates")
    if os.path.isdir(gl):
        tpl += [os.path.join(gl, f) for f in os.listdir(gl)]
    if tpl:
        print(f"| PR 正文模板 | {os.path.relpath(tpl[0], root).replace(os.sep, '/')} | [推导] |")
    else:
        print("| PR 正文模板 | 无模板，用默认三段 | [推导] |")

    print()
    print("## 2. 测试要求")
    print()
    print("| 项 | 值 | 来源 |")
    print("| --- | --- | --- |")

    pkg_path = os.path.join(root, "package.json")
    if os.path.isfile(pkg_path):
        try:
            with open(pkg_path, encoding="utf-8", errors="replace") as f:
                scripts = (json.load(f).get("scripts") or {})
        except (OSError, ValueError):
            scripts = {}
        cmds = [k for k in scripts if re.search(r"test|lint|check|format|typecheck", k)]
        if cmds:
            print(f"| 可用检查命令 | {'、'.join('npm run ' + c for c in cmds)} | [推导] package.json |")
    elif any(os.path.isfile(os.path.join(root, f)) for f in ("pyproject.toml", "tox.ini", "pytest.ini")):
        print("| 可用检查命令 | pytest / ruff / mypy（按配置） | [推导] Python 项目 |")
    elif os.path.isfile(os.path.join(root, "Cargo.toml")):
        print("| 可用检查命令 | cargo test / cargo clippy | [推导] Cargo.toml |")
    elif os.path.isfile(os.path.join(root, "go.mod")):
        print("| 可用检查命令 | go test ./... / go vet | [推导] go.mod |")
    elif os.path.isfile(os.path.join(root, "Makefile")):
        print("| 可用检查命令 | make test（见 Makefile） | [推导] |")

    wf_dir = os.path.join(root, ".github", "workflows")
    if os.path.isdir(wf_dir):
        runs = []
        for f in sorted(os.listdir(wf_dir)):
            if not f.endswith((".yml", ".yaml")):
                continue
            try:
                with open(os.path.join(wf_dir, f), encoding="utf-8", errors="replace") as fh:
                    runs += [mm.group(1).strip() for mm in re.finditer(r"run:\s*(.+)", fh.read())]
            except OSError:
                pass
        if runs:
            uniq = list(dict.fromkeys(runs))[:6]
            print(f"| CI 实际命令 | {' ; '.join(uniq)} | [推导] .github/workflows |")

    skip_hits = []
    scanned = 0
    pruned = {".git", "node_modules", "dist", "build", "target", "__pycache__",
              "site-packages", "venv", ".venv", "vendor", ".next", "out", "coverage"}
    for dirpath, dirnames, files in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in pruned]
        for f in files:
            if not f.endswith((".ts", ".js", ".py")):
                continue
            if scanned >= 200:
                break
            scanned += 1
            try:
                with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if re.search(r"process\.platform|platform ===|sys\.platform|skip:", line):
                            skip_hits.append(f"{f}:{i}")
                            break
            except OSError:
                pass
        if scanned >= 200:
            break
    if skip_hits:
        print(f"| 有平台条件跳过 | 是，{'、'.join(skip_hits[:3])} | [推导] |")

    print()
    print("## 3. 目录地图")
    print()
    print("| 目录 | 文件数 | 说明 |")
    print("| --- | --- | --- |")
    for name in sorted(os.listdir(root)):
        full = os.path.join(root, name)
        if not os.path.isdir(full) or re.match(r"^\.|node_modules|dist|build|target|__pycache__", name):
            continue
        n = sum(len(files) for _, _, files in os.walk(full))
        print(f"| {name} | {n} | |")

    print()
    print("## 4. 还需要人工补")
    print()
    print(f"- **观察项**：维护者是否直接改分支、review 风格、首响中位、合并节奏 → 跑 `prtool.py status --repo {repo_name} --author <你>` 后填")
    print("- **维护者政策**：兜底门槛、明确拒绝过的方向 → 读最近 20 个关闭未合并 PR 的维护者留言")
    print("- **领域约定**：写代码前必读的几条 → 读 README / AGENTS / 核心模块注释")
    print("- **不变量**：只有做严重线才需要 → 见 `references/severe-scan.md` 第一节")
    print("- **用户偏好**：止损线、低价值 PR 提不提 → 问用户")

    if not getattr(args, "no_record", False):
        project = getattr(args, "project", "") or os.path.basename(root.rstrip("\\/"))
        rec = record_workspace(project, root, data_root(getattr(args, "data", "")),
                               git_remote_repo(root))
        print()
        print("## 5. 工作副本已记录")
        print()
        print(f"| 项目 | 路径 | 机器 |")
        print("| --- | --- | --- |")
        print(f"| {rec['project']} | `{rec['path']}` | {rec['host']} / {rec['os']} |")
        print()
        print("写进了数据目录的 `state/workspaces.jsonl`。别的 agent 进来时跑")
        print("`prtool.py where --project <项目>` 就能直接拿到这个路径，不用再问用户。")
    return 0


# ---------------------------------------------------------------- append

def cmd_append(args):
    raw = args.json if args.json else sys.stdin.read()
    raw = (raw or "").lstrip("\ufeff").strip()
    if not raw:
        print("没有内容可追加", file=sys.stderr)
        return 1
    try:
        obj = json.loads(raw)
    except ValueError as e:
        print(f"不是合法 JSON: {e}", file=sys.stderr)
        return 1
    if not isinstance(obj, dict):
        print("需要一个 JSON 对象，不是数组或标量", file=sys.stderr)
        return 1
    if "ts" not in obj:
        print("警告：缺少 ts 字段，建议补上 ISO 时间戳", file=sys.stderr)

    one_line = re.sub(r"\r?\n", " ", raw)
    # 相对路径按数据目录解析；绝对路径原样使用
    p = args.file
    full = p if os.path.isabs(p) else data_file(p, args.data)
    full = os.path.abspath(os.path.expanduser(full))
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)

    prefix = ""
    if os.path.exists(full) and os.path.getsize(full) > 0:
        with open(full, "rb") as f:
            f.seek(-1, os.SEEK_END)
            if f.read(1) != b"\n":
                prefix = "\n"
    with open(full, "a", encoding="utf-8", newline="\n") as f:
        f.write(prefix + one_line + "\n")

    with open(full, encoding="utf-8") as f:
        lines = [ln for ln in f.read().splitlines() if ln.strip()]
    if not lines:
        print(f"写入后文件是空的，请检查 {args.file}", file=sys.stderr)
        return 1
    try:
        json.loads(lines[-1])
    except ValueError:
        print(f"写入后最后一行不是合法 JSON，请检查 {args.file}", file=sys.stderr)
        return 1

    print(f"appended -> {full}")
    print(lines[-1])
    return 0


# ---------------------------------------------------------------- whoami

def cmd_whoami(args):
    """检测 git 提交身份，缺什么给出可直接执行的设置步骤。"""
    host = args.site or "github.com"
    name = run(["git", "config", "--global", "user.name"]).strip()
    email = run(["git", "config", "--global", "user.email"]).strip()
    cred_user = get_credential_username(host)
    has_gh = bool(run(["gh", "--version"]).strip())
    has_git = bool(run(["git", "--version"]).strip())

    print(f"=== 提交身份检查（host: {host}）===\n")

    # ---- 环境层：git 有没有装
    if not has_git:
        print("  git      (未安装)")
        print("           ✗ 没有 git 无法提交任何代码\n")
        print("先安装 git：")
        print("  Windows   https://git-scm.com/download/win")
        print("  macOS     brew install git   （或 xcode-select --install）")
        print("  Linux     sudo apt install git   （或 dnf/pacman 对应命令）")
        print("\n装完重跑：python scripts/prtool.py whoami")
        return 1
    print("  git      已安装")

    # ---- 账号层：登录状态决定后面能不能自动填
    if cred_user:
        print(f"  {host} 账号  {cred_user}")
    else:
        print(f"  {host} 账号  (未登录)")
        if has_gh:
            print("           ↳ 检测到 gh CLI，可用 gh auth login 登录")
        else:
            print("           ↳ 没有 gh CLI 也可以，首次 push 时 git 会弹登录")

    print()

    # ---- 完全空白：没有账号也没有身份，先登录再设置
    if not cred_user and not name and not email:
        print("这台机器还没有配置过 GitHub 身份。按顺序做三步：\n")
        print("第 1 步 · 登录")
        if has_gh:
            print("  gh auth login")
            print("  # 选 GitHub.com → HTTPS → 用浏览器登录")
        else:
            print("  装 gh：https://cli.github.com  然后 gh auth login")
            print("  或跳过这步，等第一次 git push 时按提示在浏览器里登录")
        print()
        print("第 2 步 · 重跑本命令，会自动读出用户名和 ID")
        print("  python scripts/prtool.py whoami")
        print("  # 这次它会直接给你两条已填好的 git config 命令，复制执行即可")
        print()
        print("第 3 步 · 再跑一次确认")
        print("  python scripts/prtool.py whoami")
        print()
        print("如果不想登录也能设置：去 GitHub → Settings → Emails")
        print("勾选「Keep my email addresses private」，页面会显示完整 noreply 地址，")
        print("把它和用户名手动填进 git config 即可。")
        print()
        print("提示：noreply 邮箱不影响贡献归属统计，但能避免真实邮箱永久留在 commit 历史里。")
        return 1

    # ---- 有账号或部分配置：逐项检查
    ok = True
    actions = []

    if name:
        print(f"  提交名   {name}")
    else:
        print("  提交名   (未设置)")
        ok = False
        actions.append("设置提交名")
        if cred_user:
            print(f"           ↳ 用凭据里的账号名：{cred_user}")

    if not email:
        print("  邮箱     (未设置)")
        ok = False
        actions.append("设置邮箱")
    elif "noreply" in email.lower():
        print(f"  邮箱     {email}")
        print("           ✓ noreply 邮箱，不泄露真实信息，也不影响贡献归属统计")
    else:
        print(f"  邮箱     {email}")
        print("           ⚠ 这看起来是真实邮箱，会公开出现在每个 commit 里")
        actions.append("换成 noreply 邮箱")

    print()

    if ok and not actions:
        print("身份已就绪，无需操作。")
        return 0

    # ---- 生成可执行命令
    guess_name = name or cred_user or "<你的用户名>"
    if email and "noreply" in email.lower():
        suggested = email
    elif cred_user:
        info = api_get(f"https://api.github.com/users/{cred_user}",
                       {"User-Agent": "pr-merged"})
        uid = str((info or {}).get("id") or "")
        if uid:
            suggested = f"{uid}+{cred_user}@users.noreply.github.com"
        else:
            suggested = f"<数字ID>+{cred_user}@users.noreply.github.com"
            print(f"提示：数字 ID 在 https://api.github.com/users/{cred_user} 的 id 字段。")
            print("      也可以用 GitHub 设置页「Keep my email addresses private」生成的地址。\n")
    else:
        suggested = "<数字ID>+<用户名>@users.noreply.github.com"

    print("执行以下命令完成设置：\n")
    if not name:
        print(f'  git config --global user.name "{guess_name}"')
    if not email or "noreply" not in email.lower():
        print(f'  git config --global user.email "{suggested}"')
    if not cred_user:
        print("  # 登录（二选一）")
        if has_gh:
            print("  gh auth login")
        else:
            print("  # 装 gh 后 gh auth login，或等首次 push 时按提示登录")
        print(f"  # 或首次 git push 时按提示登录 {host}")
    print()
    print("设置后重跑：python scripts/prtool.py whoami")
    return 1


# ---------------------------------------------------------------- check

def cmd_check(args):
    """自检分两段：skill 包是否完整、数据档案是否健康。"""
    pkg = os.path.abspath(args.root or PACKAGE_ROOT)
    data = data_root(args.data)
    problems = []
    notes = []

    def add(level, where, msg):
        (problems if level == "err" else notes).append(f"[{level}] {where}: {msg}")

    # ============================================================ 包
    print(f"=== 自检 · skill 包：{pkg} ===")

    for rel in ("SKILL.md", "README.md", "LICENSE", "_seed/conventions/_TEMPLATE.md"):
        if not os.path.isfile(os.path.join(pkg, rel)):
            add("err", rel, "包内文件不存在")

    if not os.path.isdir(seed_dir()):
        add("err", "_seed/", "缺失，init 无法建数据目录")
    else:
        for item in DATA_ITEMS:
            if not os.path.exists(os.path.join(seed_dir(), item)):
                add("warn", f"_seed/{item}", "模板缺失，init 时不会创建这一项")

    # ============================================================ 数据
    print(f"=== 自检 · 数据目录：{data} ===")
    if not os.path.isdir(data):
        print()
        print(f"  数据目录还没建。先跑：")
        print(f"    python scripts/prtool.py init")
        print(f"  或用 --data 指定，或设 PR_MERGED_HOME 环境变量。")
        print()
        if problems:
            print(f"包有 {len(problems)} 个问题：")
            for p in problems:
                print("  " + p)
        return 1 if problems else 0

    # 1. JSONL 合法性
    for name in ("prs.jsonl", "scans.jsonl"):
        path = os.path.join(data, "state", name)
        if not os.path.isfile(path):
            add("err", f"state/{name}", "文件不存在")
            continue
        with open(path, encoding="utf-8-sig") as f:
            for i, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except ValueError as e:
                    add("err", f"state/{name}:{i}", f"不是合法 JSON（{e}）")
                    continue
                if not isinstance(obj, dict):
                    add("err", f"state/{name}:{i}", "不是 JSON 对象")
                    continue
                for key in ("ts", "project"):
                    if key not in obj:
                        add("err", f"state/{name}:{i}", f"缺必填字段 {key}")

    # 1b. 工作副本记录：格式校验 + 本机路径是否还在
    ws_path = os.path.join(data, "state", "workspaces.jsonl")
    if not os.path.isfile(ws_path):
        add("warn", "state/workspaces.jsonl", "缺失，跑一次 init 补上（不影响已有记录）")
    else:
        this_host = host_tag()
        for i, line in enumerate(open(ws_path, encoding="utf-8-sig", errors="replace"), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except ValueError as e:
                add("err", f"state/workspaces.jsonl:{i}", f"不是合法 JSON（{e}）")
                continue
            if not isinstance(obj, dict):
                add("err", f"state/workspaces.jsonl:{i}", "不是 JSON 对象")
                continue
            for key in ("ts", "project", "path"):
                if key not in obj:
                    add("err", f"state/workspaces.jsonl:{i}", f"缺必填字段 {key}")
            p = obj.get("path", "")
            if obj.get("host") == this_host and p and not os.path.isdir(p):
                add("warn", f"state/workspaces.jsonl:{i}",
                    f"本机路径已不存在：{p}（换位置后跑 where --path 重记）")

    # 2. _index.md 里的项目：目录、规则文件、conventions 是否存在
    #    只解析第一张表（「项目 | 状态 | 规则文件 | 下一个动作 | 最后更新」），
    #    后面还有「保留什么 | 为什么」等说明性表格，不能一起当项目解析。
    index = os.path.join(data, "projects", "_index.md")
    if os.path.isfile(index):
        in_table = False
        header_cols = 0
        with open(index, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                s = line.strip()
                if not s.startswith("|"):
                    if in_table:
                        break
                    continue
                cells = [c.strip() for c in s.strip("|").split("|")]
                if not in_table:
                    if cells and cells[0] == "项目":
                        in_table = True
                        header_cols = len(cells)
                    continue
                if set("".join(cells)) <= set("-: "):
                    continue
                if len(cells) != header_cols:
                    continue
                name = cells[0].strip("`")
                if not name:
                    continue
                state = cells[1] if len(cells) > 1 else ""
                closed = any(k in state for k in ("已收尾", "已止损"))
                proj_dir = os.path.join(data, "projects", name)
                if not os.path.isdir(proj_dir):
                    # 已收尾 / 已止损的项目允许只有索引行，不强制建目录
                    add("warn" if closed else "err", f"projects/_index.md:{i}",
                        f"项目 {name} 没有 projects/{name}/ 目录" + ("（已收尾，可不建）" if closed else ""))
                for c in cells:
                    if c.startswith("`conventions/") and not os.path.isfile(os.path.join(data, c.strip("`"))):
                        add("err", f"projects/_index.md:{i}", f"项目 {name} 引用的 {c.strip('`')} 不存在")
        # 手写合并数检查
        with open(index, encoding="utf-8") as f:
            for i, line in enumerate(f, 1):
                if re.search(r"\|\s*\d+\s*/\s*\d+\s*\|", line):
                    add("err", f"projects/_index.md:{i}",
                        "出现了手写的「合并/总数」，按硬规则应改用 prtool.py status 现算")
    else:
        add("err", "projects/_index.md", "文件不存在")

    # 3. 所有 markdown 里的相对路径引用
    #    references/ scripts/ _seed/ → 包；conventions/ projects/ state/ → 数据
    link_re = re.compile(r"`((?:references|conventions|projects|scripts|state|_seed)/[^`\s]+?\.(?:md|py|ps1|jsonl))`")

    def resolve(target):
        top = target.split("/", 1)[0]
        base = data if top in ("conventions", "projects", "state") else pkg
        return os.path.join(base, target)

    for base_dir in (pkg, data):
        for dirpath, dirnames, files in os.walk(base_dir):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fn in files:
                if not fn.endswith(".md"):
                    continue
                full = os.path.join(dirpath, fn)
                rel_self = os.path.relpath(full, base_dir).replace(os.sep, "/")
                if rel_self.startswith("archive/"):
                    continue
                with open(full, encoding="utf-8", errors="replace") as f:
                    for i, line in enumerate(f, 1):
                        for m in link_re.finditer(line):
                            target = m.group(1)
                            if "<" in target or "*" in target:
                                continue
                            if not os.path.exists(resolve(target)):
                                add("err", f"{rel_self}:{i}", f"引用的 {target} 不存在")

    # 4. conventions 必备节
    conv_dir = os.path.join(data, "conventions")
    required = ["## 1. 托管与提交", "## 2. 测试要求", "## 3. 维护者政策",
                "### 3.1 PR 类型接受度", "### 3.2 issue 政策", "## 4. 领域约定",
                "## 6. 严重度口径", "## 7. 变更记录"]
    if os.path.isdir(conv_dir):
        for fn in sorted(os.listdir(conv_dir)):
            if not fn.endswith(".md") or fn.startswith("_"):
                continue
            full = os.path.join(conv_dir, fn)
            with open(full, encoding="utf-8", errors="replace") as f:
                text = f.read()
            for sec in required:
                if sec not in text:
                    add("warn", f"conventions/{fn}", f"缺必备节「{sec}」")
            if "[推导]" not in text and "[观察]" not in text and "[用户定]" not in text:
                add("warn", f"conventions/{fn}", "没有任何来源标记（[推导]/[观察]/[用户定]）")

    # 5. 数据顶层必备文件
    for rel in ("preferences.md", "lessons.md"):
        if not os.path.isfile(os.path.join(data, rel)):
            add("err", rel, "数据目录里缺少这个文件，跑一次 init")

    # 输出
    print()
    if problems:
        print(f"发现 {len(problems)} 个问题：")
        for p in problems:
            print("  " + p)
    if notes:
        print(f"\n{len(notes)} 条提示：")
        for n in notes:
            print("  " + n)
    if not problems and not notes:
        print("全部通过。")
    return 1 if problems else 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(prog="prtool.py", description="开源 PR 工作台脚本（跨平台）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="查某仓库的 PR/MR 状态与通道活性")
    s.add_argument("--repo", required=True, help="owner/repo 或 group/project")
    s.add_argument("--author", default="", help="可选，查这个作者的全部 PR")
    s.add_argument("--platform", default="github", choices=["github", "gitlab"])
    s.add_argument("--site", default="", help="自建实例的域名，默认 github.com / gitlab.com")
    s.set_defaults(func=cmd_status)

    o = sub.add_parser("onboard", help="读本地仓库，推导 conventions 能自动填的项")
    o.add_argument("--path", required=True)
    o.add_argument("--project", default="", help="项目名，默认取目录名")
    o.add_argument("--no-record", action="store_true", help="只采集，不写工作副本记录")
    o.add_argument("--data", default="", help="数据目录，默认 ~/.pr-merged 或 $PR_MERGED_HOME")
    o.set_defaults(func=cmd_onboard)

    w2 = sub.add_parser("where", help="查/记某个项目的本地工作副本路径（跨 agent 共享）")
    w2.add_argument("--project", default="", help="项目名，如 agent-autoloop")
    w2.add_argument("--repo", default="", help="owner/repo，按仓库过滤或补全")
    w2.add_argument("--path", default="", help="给了就记录这个路径，不给就只查询")
    w2.add_argument("--data", default="", help="数据目录，默认 ~/.pr-merged 或 $PR_MERGED_HOME")
    w2.set_defaults(func=cmd_where)

    a = sub.add_parser("append", help="往 JSONL 台账追加一条记录")
    a.add_argument("--file", required=True, help="相对路径按数据目录解析，绝对路径原样用")
    a.add_argument("--json", default="", help="省略则从 stdin 读")
    a.add_argument("--data", default="", help="数据目录，默认 ~/.pr-merged 或 $PR_MERGED_HOME")
    a.set_defaults(func=cmd_append)

    c = sub.add_parser("check", help="自检：skill 包完整性 + 数据档案健康度")
    c.add_argument("--root", default="", help="skill 包根目录，默认取本脚本的上一级")
    c.add_argument("--data", default="", help="数据目录，默认 ~/.pr-merged 或 $PR_MERGED_HOME")
    c.set_defaults(func=cmd_check)

    n = sub.add_parser("init", help="建数据目录骨架（已存在的文件不覆盖）")
    n.add_argument("--data", default="", help="数据目录，默认 ~/.pr-merged 或 $PR_MERGED_HOME")
    n.set_defaults(func=cmd_init)

    w = sub.add_parser("whoami", help="检查 git 提交身份，缺什么给设置步骤")
    w.add_argument("--site", default="", help="默认 github.com")
    w.set_defaults(func=cmd_whoami)

    i = sub.add_parser("issues", help="扫 open issue，标新手友好 / 长期未修 / 已认领")
    i.add_argument("--repo", required=True)
    i.add_argument("--platform", default="github", choices=["github", "gitlab"])
    i.add_argument("--site", default="", help="自建实例的域名，默认 github.com / gitlab.com")
    i.add_argument("--limit", type=int, default=50, help="最多拉多少个 issue，默认 50")
    i.add_argument("--linked-limit", type=int, default=15,
                   help="查关联 PR 的 issue 数上限，默认 15（每个多一次请求）")
    i.add_argument("--no-linked", action="store_true",
                   help="不查关联 PR，速度快但会漏掉「已有人在修」的 issue")
    i.add_argument("--min-failed-prs", type=int, default=3,
                   help="多少个已关闭未合并的 PR 算「多 PR 未合」，默认 3")
    i.set_defaults(func=cmd_issues)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
