import time
import sqlite3
import requests
from bs4 import BeautifulSoup


def parse_stars(star_text: str) -> int:
    """'1.2k' や '123' のようなスター表記を整数に変換する"""
    text = star_text.strip().lower().replace(",", "")
    if not text:
        return 0
    if text.endswith("k"):
        return int(float(text[:-1]) * 1000)
    if text.endswith("m"):
        return int(float(text[:-1]) * 1000000)
    try:
        return int(text)
    except ValueError:
        return 0


def scrape_google_repositories():
    """GitHubのGoogle組織のリポジトリ一覧を全件スクレイピングする"""
    base_url = "https://github.com/orgs/google/repositories"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    repos = []
    page = 1

    while True:
        url = f"{base_url}?page={page}"
        print(f"取得中: {url}")

        response = requests.get(url, headers=headers)
        # サーバー負荷軽減のため必ず1秒待機（課題の必須要件）
        time.sleep(1)

        if response.status_code != 200:
            print(f"アクセス終了 (ステータスコード: {response.status_code})")
            break

        soup = BeautifulSoup(response.text, "html.parser")

        # 各リポジトリのli要素を取得
        repo_items = soup.select("li[class*='listItem']")

        # リポジトリが1件も取得できなくなったら最終ページと判断して終了
        if not repo_items:
            print("全ページの取得が完了しました。")
            break

        page_count = 0
        for item in repo_items:
            # 1. リポジトリ名の取得
            name_tag = item.select_one("h3 a")
            if not name_tag:
                continue
            repo_name = name_tag.get_text(strip=True)

            # 2. 主要な言語の取得
            lang_tag = item.select_one("span[class*='PrimaryLanguageName']")
            language = lang_tag.get_text(strip=True) if lang_tag else "None"

            # 3. スター数の取得
            star_tag = item.select_one("a[href$='/stargazers']")
            stars = parse_stars(star_tag.get_text()) if star_tag else 0

            repos.append((repo_name, language, stars))
            page_count += 1

        if page_count == 0:
            print("全ページの取得が完了しました。")
            break

        print(f"  -> {page_count}件取得（累計: {len(repos)}件）")
        page += 1

    return repos


def save_and_display_db(repos):
    """SQLiteデータベースに保存し、SELECT文で取得して表示する"""
    db_name = "google_repos.db"
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # テーブル作成（再実行しても重複しないように一度削除してから作成）
    cursor.execute("DROP TABLE IF EXISTS repositories")
    cursor.execute("""
        CREATE TABLE repositories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            language TEXT,
            stars INTEGER
        )
    """)

    # データの挿入
    cursor.executemany(
        "INSERT INTO repositories (name, language, stars) VALUES (?, ?, ?)",
        repos
    )
    conn.commit()
    print(f"\nデータベース '{db_name}' に {len(repos)} 件のデータを保存しました。\n")

    # SELECT文でデータを取得して表示
    print("=== データベース内の保存データ（SELECT結果） ===")
    cursor.execute("SELECT id, name, language, stars FROM repositories")
    rows = cursor.fetchall()

    for row in rows:
        print(f"ID: {row[0]} | リポジトリ名: {row[1]} | 主要言語: {row[2]} | スター数: {row[3]}")

    print(f"\n合計表示件数: {len(rows)} 件")
    conn.close()


if __name__ == "__main__":
    scraped_data = scrape_google_repositories()
    if scraped_data:
        save_and_display_db(scraped_data)
    else:
        print("データが取得できませんでした。")