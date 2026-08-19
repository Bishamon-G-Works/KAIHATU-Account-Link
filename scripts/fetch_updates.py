# -*- coding: utf-8 -*-
"""
GitHubアカウント監視ダッシュボード - データ取得スクリプト

README.md の LINK 列に記載された GitHub リポジトリの
最新コミット情報を取得し、repo_status.json に保存する。
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

try:
    import requests
except ImportError:
    print("エラー: pip install requests を実行してください。")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import GITHUB_API_BASE, REQUEST_TIMEOUT, STATUS_FILE, COMMIT_MESSAGE_MAX_LENGTH

JST = timezone(timedelta(hours=9))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(REPO_ROOT, "README.md")


def get_repos_from_readme(readme_path):
    """README.md の LINK 列から監視対象リポジトリを抽出する"""
    if not os.path.exists(readme_path):
        return []

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    repos = []
    seen = set()
    in_table = False
    skip_align = False

    for line in content.split("\n"):
        if "| リポジトリ |" in line and "| LINK |" in line:
            in_table = True
            skip_align = True
            continue
        if skip_align:
            skip_align = False
            continue
        if in_table:
            if line.startswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 2:
                    link_cell = cells[1]
                    url_m = re.search(r'\((.*?)\)', link_cell)
                    url = url_m.group(1) if url_m else "#"
                    m = re.search(r'github\.com/([^/#\s]+/[^/#\s]+)', url)
                    if m:
                        repo = m.group(1)
                        if repo not in seen:
                            repos.append(repo)
                            seen.add(repo)
            else:
                in_table = False

    return repos


def get_github_token():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("警告: GITHUB_TOKEN が未設定です（60回/時 制限）。")
    return token


def build_headers(token):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "RepoStatusDashboard/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def truncate_message(message):
    if not message:
        return "（メッセージなし）"
    first_line = message.split("\n")[0].strip()
    if len(first_line) > COMMIT_MESSAGE_MAX_LENGTH:
        return first_line[:COMMIT_MESSAGE_MAX_LENGTH - 1] + "…"
    return first_line


def parse_datetime(date_str):
    if not date_str:
        return "—"
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.astimezone(JST).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return "—"


def fetch_latest_commit(repo_full_name, headers):
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits"
    try:
        r = requests.get(url, headers=headers, params={"per_page": 1},
                         timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        commits = r.json()
        if not commits:
            return {"repo": repo_full_name, "status": "✅", "message": "（コミットなし）",
                    "date": "—", "sha_short": "—", "commit_url": "#"}
        c = commits[0]
        cd = c.get("commit", {})
        ai = cd.get("author", {})
        return {
            "repo": repo_full_name,
            "status": "✅",
            "message": truncate_message(cd.get("message", "")),
            "date": parse_datetime(ai.get("date")),
            "sha_short": c.get("sha", "")[:7],
            "commit_url": c.get("html_url", "#"),
        }
    except requests.exceptions.Timeout:
        return {"repo": repo_full_name, "status": "❌", "message": "タイムアウト",
                "date": "—", "sha_short": "—", "commit_url": "#"}
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response else "不明"
        return {"repo": repo_full_name, "status": "❌", "message": f"HTTPエラー ({code})",
                "date": "—", "sha_short": "—", "commit_url": "#"}
    except Exception as e:
        return {"repo": repo_full_name, "status": "❌", "message": "通信エラー",
                "date": "—", "sha_short": "—", "commit_url": "#"}


def main():
    print("=" * 60)
    print("📊 リポジトリ状態取得を開始します")
    print("=" * 60)

    token = get_github_token()
    headers = build_headers(token)

    repos = get_repos_from_readme(README_PATH)
    print(f"\n監視対象: {len(repos)} リポジトリ（README.mdのLINK列より）")

    results = {}
    success_count = 0
    error_count = 0

    for i, repo in enumerate(repos, 1):
        print(f"\n[{i}/{len(repos)}] {repo} を取得中...")
        result = fetch_latest_commit(repo, headers)
        results[repo] = result
        if result["status"] == "✅":
            success_count += 1
            print(f"  ✅ {result['message']}")
        else:
            error_count += 1
            print(f"  ❌ {result['message']}")

    now_jst = datetime.now(JST)
    output = {
        "timestamp": now_jst.strftime("%Y-%m-%d %H:%M"),
        "timestamp_iso": now_jst.isoformat(),
        "total_repos": len(repos),
        "success_count": success_count,
        "error_count": error_count,
        "repos": results,
    }

    status_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               os.path.basename(STATUS_FILE))
    with open(status_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"✅ 完了: 成功 {success_count} / エラー {error_count} / 合計 {len(repos)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
