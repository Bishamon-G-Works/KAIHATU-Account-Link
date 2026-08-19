# -*- coding: utf-8 -*-
"""
GitHubアカウント監視ダッシュボード - 設定ファイル

このファイルが唯一の設定源（Single Source of Truth）です。
テーブル構造の定義と監視対象の判定を一元管理します。

【リポジトリ追加方法】
  該当セクションの rows に辞書を追加してください。
  - repo に "owner/repo" を指定 → 監視対象（APIで最新コミット取得）
  - repo に None を指定        → 監視対象外（テーブルには表示、ステータスは「—」）

【リポジトリ削除方法】
  該当の行辞書を rows から削除してください。
"""

# =============================================================================
# ダッシュボード テーブル定義
# =============================================================================
# 各セクションが独立したMarkdownテーブルとして生成されます。
# "header_cols" でそのセクションのヘッダー列名を定義します。

DASHBOARD_ENTRIES = [
    # === アカウント一覧 ===
    {
        "section": "アカウント一覧",
        "header_cols": ["リポジトリ", "LINK", "概要",
                        "ステータス", "最終コミット", "更新時刻", "コミットID"],
        "rows": [
            {
                "display": "FPL-2026",
                "repo": "Bishamon-G/FPL-2026",
                "description": "",  # 各自で記載
            },
            {
                "display": "Dev-Meeting（開発ミーティング議事録）",
                "repo": "Bishamon-Dev-Group/Dev-Meeting",
                "description": "",  # 各自で記載
            },
            {
                "display": "KAIHATU-Account-Link（アカウント連携）",
                "repo": "Bishamon-Dev-Group/KAIHATU-Account-Link",
                "description": "",  # 各自で記載
            },
            {
                "display": "matehan-toku-kai-ana",
                "repo": "Bishamon-Dev-Group/matehan-toku-kai-ana",
                "description": "",  # 各自で記載
            },
            # フレーム（追加用スロット）
            {
                "display": "＊＊＊",
                "repo": None,
                "description": "",
            },
            {
                "display": "＊＊＊",
                "repo": None,
                "description": "",
            },
            {
                "display": "＊＊＊",
                "repo": None,
                "description": "",
            },
        ],
    },
]


# =============================================================================
# GitHub API 設定
# =============================================================================
GITHUB_API_BASE = "https://api.github.com"

# APIリクエストのタイムアウト（秒）
REQUEST_TIMEOUT = 10

# 中間データ保存ファイル（.gitignore に追加済み）
STATUS_FILE = "scripts/repo_status.json"

# コミットメッセージの最大表示文字数
COMMIT_MESSAGE_MAX_LENGTH = 60


# =============================================================================
# ヘルパー関数
# =============================================================================
def get_monitored_repos():
    """
    DASHBOARD_ENTRIES から監視対象リポジトリを抽出する。

    Returns:
        list[str]: "owner/repo" 形式の文字列リスト（重複なし）
    """
    repos = []
    seen = set()
    for section in DASHBOARD_ENTRIES:
        for row in section["rows"]:
            repo = row.get("repo")
            if repo and repo not in seen:
                repos.append(repo)
                seen.add(repo)
    return repos


def get_repo_url(repo_full_name):
    """
    "owner/repo" からGitHubリポジトリURLを生成する。

    Args:
        repo_full_name: "owner/repo" 形式の文字列

    Returns:
        str: GitHubリポジトリURL
    """
    if not repo_full_name:
        return "#"
    return f"https://github.com/{repo_full_name}"
