# -*- coding: utf-8 -*-
"""
GitHubアカウント監視ダッシュボード - README更新スクリプト

既存のREADME.mdから「リポジトリ」「LINK」「概要」列を読み取り（保持）、
「ステータス」「最終コミット」「更新時刻」「コミットID」列のみ自動更新する。

■ 直接編集できる列（自動更新で上書きされない）
  - リポジトリ  : 表示名
  - LINK        : GitHubリポジトリへのリンク
  - 概要        : 各自が自由に記載

■ 自動更新される列
  - ステータス  : ✅ or ❌
  - 最終コミット: コミットメッセージ（先頭1行）
  - 更新時刻    : コミット日時（JST）
  - コミットID  : ハッシュ（先頭7文字）
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import STATUS_FILE

JST = timezone(timedelta(hours=9))

# READMEのパス（scriptsの親 = リポジトリルート）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(REPO_ROOT, "README.md")


def load_status_data():
    """repo_status.json を読み込む"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        os.path.basename(STATUS_FILE))
    if not os.path.exists(path):
        print(f"警告: {path} が見つかりません。空のステータスで生成します。")
        return {"timestamp": "—", "repos": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"エラー: {e}")
        return {"timestamp": "—", "repos": {}}


def extract_repo_from_url(url):
    """GitHub URL から owner/repo を抽出する"""
    m = re.search(r'github\.com/([^/#\s]+/[^/#\s]+)', url)
    return m.group(1) if m else None


def parse_existing_rows(readme_path):
    """
    既存のREADMEからテーブル行を解析する。

    Returns:
        list[dict]: 各行の display / link_cell / description / repo
    """
    if not os.path.exists(readme_path):
        return []

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    rows = []
    in_table = False
    skip_align = False

    for line in content.split("\n"):
        # ヘッダー行を検出
        if "| リポジトリ |" in line and "| LINK |" in line:
            in_table = True
            skip_align = True
            continue
        # アライメント行をスキップ
        if skip_align:
            skip_align = False
            continue
        # テーブル行を処理
        if in_table:
            if line.startswith("|"):
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if len(cells) >= 3:
                    display = cells[0]
                    link_cell = cells[1]
                    description = cells[2]
                    url_m = re.search(r'\((.*?)\)', link_cell)
                    url = url_m.group(1) if url_m else "#"
                    repo = extract_repo_from_url(url)
                    rows.append({
                        "display": display,
                        "link_cell": link_cell,
                        "description": description,
                        "repo": repo,
                    })
            else:
                in_table = False

    return rows


def generate_readme(status_data, readme_path):
    """
    README.md を生成する。
    リポジトリ・LINK・概要は既存READMEから引き継ぎ、
    ステータス系列のみ status_data で更新する。
    """
    timestamp = status_data.get("timestamp", "—")
    success = status_data.get("success_count", 0)
    error = status_data.get("error_count", 0)
    total = status_data.get("total_repos", 0)
    repos_data = status_data.get("repos", {})

    rows = parse_existing_rows(readme_path)

    parts = []

    # タイトル
    parts.append("# 🔗 GitHubアカウント一覧\n")

    # 最終更新タイムスタンプ
    parts.append(f"🔄 **最終チェック**: {timestamp} (JST) — "
                 f"取得 ✅{success} ❌{error} / {total}件\n")

    # テーブルヘッダー
    parts.append("| リポジトリ | LINK | 概要 | ステータス | 最終コミット | 更新時刻 | コミットID |")
    parts.append("| :--- | :--- | :--- | :---: | :--- | :--- | :--- |")

    # データ行（リポジトリ・LINK・概要は既存から保持）
    for row in rows:
        display = row["display"]
        link_cell = row["link_cell"]
        description = row["description"]
        repo = row["repo"]

        if repo and repo in repos_data:
            s = repos_data[repo]
            status = s.get("status", "❓")
            message = s.get("message", "—").replace("|", "\\|")
            date = s.get("date", "—")
            sha = s.get("sha_short", "—")
            commit_url = s.get("commit_url", "#")
            commit_id = f"[{sha}]({commit_url})" if sha and sha != "—" else "—"
        else:
            status = "—"
            message = "—"
            date = "—"
            commit_id = "—"

        parts.append(
            f"| {display} | {link_cell} | {description} "
            f"| {status} | {message} | {date} | {commit_id} |"
        )

    parts.append("")

    # 凡例
    parts.append("## 凡例\n")
    parts.append("- ✅ : 正常に取得完了")
    parts.append("- ❌ : 取得エラー")
    parts.append("- — : 監視対象外 / 未設定")
    parts.append("- コミットID: 最新コミットのハッシュ（先頭7文字、クリックで詳細へ）\n")

    # フッター
    parts.append("---\n")
    parts.append("*このREADMEは自動生成されています。10分ごとに更新されます。*\n")
    parts.append("> ✏️ **直接編集可能**: リポジトリ名・LINK・概要 の各列は自動更新で上書きされません。\n")

    return "\n".join(parts)


def main():
    print("📝 README.md の更新を開始します...")

    status_data = load_status_data()
    print(f"  データタイムスタンプ: {status_data.get('timestamp', '—')}")

    readme_content = generate_readme(status_data, README_PATH)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"  ✅ README.md を更新しました")


if __name__ == "__main__":
    main()
