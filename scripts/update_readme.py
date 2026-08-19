# -*- coding: utf-8 -*-
"""
部署リポジトリ監視ダッシュボード - README更新スクリプト

repo_status.json の情報を元に、config.py の DASHBOARD_ENTRIES に従って
Markdownテーブルを生成し、README.md を更新する。

使用方法:
    python scripts/update_readme.py
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

# 同ディレクトリのconfig.pyをインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DASHBOARD_ENTRIES, STATUS_FILE, get_repo_url

# 日本標準時（UTC+9）
JST = timezone(timedelta(hours=9))


def load_status_data():
    """
    repo_status.json を読み込む。

    Returns:
        dict: ステータスデータ。ファイルが存在しない場合は空のデフォルト値
    """
    status_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        os.path.basename(STATUS_FILE),
    )

    if not os.path.exists(status_file_path):
        print(f"警告: {status_file_path} が見つかりません。空のステータスで生成します。")
        return {"timestamp": "—", "repos": {}}

    try:
        with open(status_file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"エラー: ステータスファイルの読み込みに失敗: {e}")
        return {"timestamp": "—", "repos": {}}


def escape_markdown(text):
    """
    Markdownテーブル内で問題になる文字をエスケープする。

    Args:
        text: エスケープ対象の文字列

    Returns:
        str: エスケープ済み文字列
    """
    if not text:
        return ""
    # パイプ文字をエスケープ
    return str(text).replace("|", "\\|")


def generate_section_table(section, status_data):
    """
    1つのセクション（開発グループ or 個人アカウント）のMarkdownテーブルを生成する。

    Args:
        section: DASHBOARD_ENTRIES の1セクション辞書
        status_data: repo_status.json の内容

    Returns:
        str: Markdownテーブル文字列
    """
    repos_data = status_data.get("repos", {})
    header_cols = section["header_cols"]
    rows = section["rows"]

    lines = []

    # ヘッダー行
    header_line = "| " + " | ".join(header_cols) + " |"
    # アライメント行（ステータス列は中央揃え）
    align_parts = []
    for col in header_cols:
        if col == "ステータス":
            align_parts.append(":---:")
        else:
            align_parts.append(":---")
    align_line = "| " + " | ".join(align_parts) + " |"

    lines.append(header_line)
    lines.append(align_line)

    # データ行
    for row in rows:
        repo = row.get("repo")
        account = escape_markdown(row.get("account", ""))
        display = escape_markdown(row.get("display", ""))

        if repo:
            # 監視対象リポジトリ
            repo_url = get_repo_url(repo)
            link_cell = f"[🔗]({repo_url})"

            # ステータスデータから情報を取得
            repo_status = repos_data.get(repo, {})
            status = repo_status.get("status", "❓")
            message = escape_markdown(repo_status.get("message", "—"))
            date = repo_status.get("date", "—")
            sha_short = repo_status.get("sha_short", "—")
            commit_url = repo_status.get("commit_url", "#")

            # コミットIDはリンク化（ハッシュが有効な場合）
            if sha_short and sha_short != "—":
                commit_id_cell = f"[{sha_short}]({commit_url})"
            else:
                commit_id_cell = "—"

            data_line = (
                f"| {account} | {display} | {link_cell} "
                f"| {status} | {message} | {date} | {commit_id_cell} |"
            )
        else:
            # 監視対象外（repo が None）
            if display:
                # 表示名がある場合（廣田GMの「＊＊＊」など）
                link_cell = "[🔗](#)"
                data_line = (
                    f"| {account} | {display} | {link_cell} "
                    f"| — | — | — | — |"
                )
            else:
                # 空行（将来の追加用スロット）
                data_line = f"| {account} |  |  | — | — | — | — |"

        lines.append(data_line)

    return "\n".join(lines)


def generate_readme(status_data):
    """
    README.md 全体のMarkdownを生成する。

    Args:
        status_data: repo_status.json の内容

    Returns:
        str: README.md の全文
    """
    timestamp = status_data.get("timestamp", "—")
    success = status_data.get("success_count", 0)
    error = status_data.get("error_count", 0)
    total = status_data.get("total_repos", 0)

    parts = []

    # タイトル
    parts.append("# 🔗 スギヤス開発GitHubアカウント一覧\n")

    # 最終更新タイムスタンプ
    parts.append(f"🔄 **最終チェック**: {timestamp} (JST) — "
                 f"取得 ✅{success} ❌{error} / {total}件\n")

    # 各セクションのテーブルを生成
    for section in DASHBOARD_ENTRIES:
        table = generate_section_table(section, status_data)
        parts.append(table)
        parts.append("")  # セクション間の空行

    # 凡例
    parts.append("## 凡例\n")
    parts.append("- ✅ : 正常に取得完了")
    parts.append("- ❌ : 取得エラー")
    parts.append("- — : 監視対象外 / 未設定")
    parts.append("- コミットID: 最新コミットのハッシュ（先頭7文字、クリックで詳細へ）\n")

    # フッター
    parts.append("---\n")
    parts.append("*このREADMEは自動生成されています。10分ごとに更新されます。*\n")

    return "\n".join(parts)


def main():
    """メイン処理: README.md を生成して上書き保存"""
    print("📝 README.md の生成を開始します...")

    # ステータスデータ読み込み
    status_data = load_status_data()
    timestamp = status_data.get("timestamp", "—")
    print(f"  データタイムスタンプ: {timestamp}")

    # README生成
    readme_content = generate_readme(status_data)

    # README.md に書き出し（リポジトリルートに配置）
    # スクリプトの親ディレクトリ = scripts/ → その親 = リポジトリルート
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    readme_path = os.path.join(repo_root, "README.md")

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)

    print(f"  ✅ README.md を更新しました: {readme_path}")
    print(f"  📊 テーブル: {len(DASHBOARD_ENTRIES)} セクション")

    # テーブル行数をカウント
    total_rows = sum(len(s["rows"]) for s in DASHBOARD_ENTRIES)
    print(f"  📋 テーブル行: {total_rows} 行")


if __name__ == "__main__":
    main()
