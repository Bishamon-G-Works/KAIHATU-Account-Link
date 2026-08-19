# -*- coding: utf-8 -*-
"""
部署リポジトリ監視ダッシュボード - データ取得スクリプト

GitHub APIを使って各監視対象リポジトリの最新コミット情報を取得し、
JSON形式で repo_status.json に保存する。

使用方法:
    GITHUB_TOKEN=<token> python scripts/fetch_updates.py
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

# requestsライブラリのインポート
try:
    import requests
except ImportError:
    print("エラー: requestsライブラリが必要です。pip install requests を実行してください。")
    sys.exit(1)

# 同ディレクトリのconfig.pyをインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    GITHUB_API_BASE,
    REQUEST_TIMEOUT,
    STATUS_FILE,
    COMMIT_MESSAGE_MAX_LENGTH,
    get_monitored_repos,
)

# 日本標準時（UTC+9）
JST = timezone(timedelta(hours=9))


def get_github_token():
    """
    環境変数からGitHubトークンを取得する。

    Returns:
        str or None: トークン文字列、未設定の場合はNone
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("警告: GITHUB_TOKEN が未設定です。API制限が厳しくなります（60回/時）。")
    return token


def build_headers(token):
    """
    GitHub API用のHTTPヘッダーを構築する。

    Args:
        token: GitHubトークン（Noneの場合は認証なし）

    Returns:
        dict: HTTPヘッダー辞書
    """
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "RepoStatusDashboard/1.0",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers


def truncate_message(message, max_length=COMMIT_MESSAGE_MAX_LENGTH):
    """
    コミットメッセージを1行目のみ、指定文字数で切り詰める。

    Args:
        message: コミットメッセージ全文
        max_length: 最大文字数

    Returns:
        str: 切り詰められたメッセージ
    """
    if not message:
        return "（メッセージなし）"
    # 1行目のみ取得
    first_line = message.split("\n")[0].strip()
    if len(first_line) > max_length:
        return first_line[:max_length - 1] + "…"
    return first_line


def parse_datetime(date_str):
    """
    ISO 8601形式の日時文字列をJSTに変換してフォーマットする。

    Args:
        date_str: ISO 8601形式の日時文字列（例: "2026-06-25T05:43:40Z"）

    Returns:
        str: "YYYY-MM-DD HH:MM" 形式の日時文字列（JST）
    """
    if not date_str:
        return "—"
    try:
        # ISO 8601 パース（末尾の "Z" を UTC として処理）
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        # JSTに変換
        dt_jst = dt.astimezone(JST)
        return dt_jst.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return "—"


def fetch_latest_commit(repo_full_name, headers):
    """
    指定リポジトリの最新コミット情報を取得する。

    Args:
        repo_full_name: "owner/repo" 形式の文字列
        headers: HTTPヘッダー辞書

    Returns:
        dict: コミット情報辞書
    """
    url = f"{GITHUB_API_BASE}/repos/{repo_full_name}/commits"
    params = {"per_page": 1}

    try:
        response = requests.get(
            url, headers=headers, params=params, timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        commits = response.json()

        if not commits:
            return {
                "repo": repo_full_name,
                "status": "✅",
                "message": "（コミットなし）",
                "author": "—",
                "date": "—",
                "sha_short": "—",
                "commit_url": "#",
            }

        commit = commits[0]
        commit_data = commit.get("commit", {})
        author_info = commit_data.get("author", {})

        return {
            "repo": repo_full_name,
            "status": "✅",
            "message": truncate_message(commit_data.get("message", "")),
            "author": author_info.get("name", "不明"),
            "date": parse_datetime(author_info.get("date")),
            "sha_short": commit.get("sha", "")[:7],
            "commit_url": commit.get("html_url", "#"),
        }

    except requests.exceptions.Timeout:
        print(f"  ⏰ タイムアウト: {repo_full_name}")
        return _error_result(repo_full_name, "タイムアウト")

    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else "不明"
        print(f"  ❌ HTTPエラー ({status_code}): {repo_full_name}")
        return _error_result(repo_full_name, f"HTTPエラー ({status_code})")

    except requests.exceptions.RequestException as e:
        print(f"  ❌ 通信エラー: {repo_full_name} - {e}")
        return _error_result(repo_full_name, "通信エラー")

    except (KeyError, IndexError, TypeError) as e:
        print(f"  ❌ データ解析エラー: {repo_full_name} - {e}")
        return _error_result(repo_full_name, "データ解析エラー")


def _error_result(repo_full_name, error_message):
    """
    エラー時の統一レスポンスを生成する。

    Args:
        repo_full_name: "owner/repo" 形式の文字列
        error_message: エラーメッセージ

    Returns:
        dict: エラー情報辞書
    """
    return {
        "repo": repo_full_name,
        "status": "❌",
        "message": error_message,
        "author": "—",
        "date": "—",
        "sha_short": "—",
        "commit_url": "#",
    }


def main():
    """メイン処理: 全監視対象リポジトリの最新コミットを取得してJSONに保存"""
    print("=" * 60)
    print("📊 リポジトリ状態取得を開始します")
    print("=" * 60)

    # トークン取得
    token = get_github_token()
    headers = build_headers(token)

    # 監視対象リポジトリを取得
    repos = get_monitored_repos()
    print(f"\n監視対象: {len(repos)} リポジトリ")

    # 各リポジトリの最新コミットを取得
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

    # タイムスタンプ付きで保存
    now_jst = datetime.now(JST)
    output = {
        "timestamp": now_jst.strftime("%Y-%m-%d %H:%M"),
        "timestamp_iso": now_jst.isoformat(),
        "total_repos": len(repos),
        "success_count": success_count,
        "error_count": error_count,
        "repos": results,
    }

    # JSONファイルに保存
    status_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.path.basename(STATUS_FILE),
    )
    with open(status_file_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"✅ 完了: 成功 {success_count} / エラー {error_count} / 合計 {len(repos)}")
    print(f"📄 保存先: {status_file_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
