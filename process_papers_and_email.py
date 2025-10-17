# process_papers_and_email.py
import os
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
import pandas as pd
import requests

KEYWORDS = [
    "axiomatic quantum field theory", "algebraic quantum field theory", "AQFT", "Ryu-Takayanagi",
    "measurement-induced", "resource theory", "resource theoretic",
    "Haag", "LSZ", "conformal bootstrap", "duality",
    "non-perturbative", "Yang Mills", "Renormalization Group", "MERA",
]
RSS_FEEDS = [
    "https://rss.arxiv.org/rss/hep-th", "https://rss.arxiv.org/rss/math-ph",
    "https://rss.arxiv.org/rss/quant-ph",
]
# スクリプトのディレクトリを基準にreportsディレクトリのパスを設定
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(SCRIPT_DIR, "reports")


def fetch_and_filter_papers():
    print("Fetching papers from RSS feeds...")
    unique_papers = {}
    for url in RSS_FEEDS:
        print(f"  - Fetching {url}")
        feed = feedparser.parse(url)
        for entry in feed.entries:
            if entry.id not in unique_papers:
                unique_papers[entry.id] = entry
        time.sleep(1)
    print(f"\nFound {len(unique_papers)} unique new papers. Filtering by keywords...")
    filtered_papers = []
    for entry in unique_papers.values():
        title_lower = entry.title.lower()
        summary_lower = entry.summary.lower()
        is_hit = [keyword.lower() in title_lower or keyword.lower()
                  in summary_lower for keyword in KEYWORDS]

        if sum(is_hit) > 0:
            true_idx = [i for i, val in enumerate(is_hit) if val]
            hit_keywords = [KEYWORDS[i] for i in true_idx]

            parsed_authors = []
            if hasattr(entry, 'authors') and entry.authors:
                author_string = entry.authors[0].get('name', '')
                author_names = [name.strip() for name in author_string.split(',')]
                for name in author_names:
                    parsed_authors.append({'name': name})
            filtered_papers.append({
                "id": entry.id, "published": entry.published, "title": entry.title,
                "summary": entry.summary, "url": entry.link, "authors": parsed_authors,
                "keywords": hit_keywords,
            })
    print(f"  -> Found {len(filtered_papers)} relevant papers.")
    return filtered_papers


def evaluate_authors_via_semantic_scholar(authors):
    evaluated_authors = []
    if not authors: return evaluated_authors
    for author in authors:
        author_name = author.get("name")
        if not author_name: continue
        print(f"    - Evaluating author: {author_name}")
        try:
            api_url = f"https://api.semanticscholar.org/graph/v1/author/search?query={requests.utils.quote(author_name)}&fields=hIndex,citationCount,paperCount,url"
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            if response.json().get("data"):
                author_data = response.json()["data"][0]
                evaluation = {"name": author_name, "hIndex": author_data.get("hIndex", 0),
                              "citations": author_data.get("citationCount", 0),
                              "papers": author_data.get("paperCount", 0),
                              "semantic_scholar_url": author_data.get("url", "#")}
                evaluated_authors.append(evaluation)
        except requests.exceptions.RequestException as e:
            print(f"      -> API Error for {author_name}: {e}")
        time.sleep(1)
    return evaluated_authors


def get_score_label_and_class(score):
    # (この関数は変更なし)
    if score >= 100: return "世界的権威", "score-s-plus"
    elif score >= 50: return "トップ研究者", "score-s"
    elif score >= 20: return "中核研究者", "score-a"
    elif score >= 10: return "注目研究者", "score-b"
    else: return "若手研究者", "score-c"


def get_score_emoji(score):
    # (この関数は変更なし)
    if score >= 100: return "🏆"
    elif score >= 50: return "🏅"
    elif score >= 20: return "🟢"
    elif score >= 10: return "🔵"
    else: return "⚪"


def extract_arxiv_id(arxiv_url):
    """arXiv URLからarXiv ID（例：2409.12345）を抽出する"""
    import re
    # arXiv URLからIDを抽出（例：http://arxiv.org/abs/2409.12345 → 2409.12345）
    match = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)', arxiv_url)
    if match:
        return match.group(1)
    # フォールバック：URLの最後の部分を使用
    return arxiv_url.split('/')[-1]


def generate_markdown_report(processed_papers):
    """GitHub Flavored Markdownレポートを生成する"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    md_content = f"# arXiv 論文レポート ({today_str})\n\n"

    if not processed_papers:
        md_content += "_本日、キーワードに合致する新着論文はありませんでした。_\n"
    else:
        processed_papers.sort(key=lambda p: p.get("preprint_score", 0), reverse=True)
        for i, paper in enumerate(processed_papers):
            score = paper.get("preprint_score", 0)
            score_label, _ = get_score_label_and_class(score)
            score_emoji = get_score_emoji(score)
            paper_id = extract_arxiv_id(paper['id'])
            published_date = pd.to_datetime(paper['published']).strftime('%Y-%m-%d %H:%M')

            # 論文タイトルとスコア
            md_content += f"## {score_emoji} [{paper['title']}]({paper['url']})\n\n"
            md_content += f"**Score: {score} ({score_label})**\n\n"

            # キーワード
            md_content += f"**Keywords:** {' • '.join(paper['keywords'])}\n\n"

            # 公開日
            md_content += f"**公開日:** {published_date}\n\n"

            # 著者情報
            if paper.get("authors_evaluation"):
                md_content += "### 著者情報 (Semantic Scholar)\n\n"
                md_content += "| 著者 | h-index | 被引用数 | 論文数 |\n"
                md_content += "|------|---------|----------|--------|\n"
                for author_eval in paper["authors_evaluation"]:
                    name = author_eval['name']
                    url = author_eval['semantic_scholar_url']
                    h_index = author_eval['hIndex']
                    citations = f"{author_eval['citations']:,}"
                    papers = author_eval['papers']
                    md_content += f"| [{name}]({url}) | {h_index} | {citations} | {papers} |\n"
                md_content += "\n"

            # アブストラクト
            md_content += "### アブストラクト (原文)\n\n"
            md_content += f"> {paper.get('summary', 'N/A')}\n\n"
            md_content += "---\n\n"

    return md_content



def create_gist(markdown_content, public=False):
    """GitHub Gistを作成してURLを返す"""
    github_token = os.getenv("GH_TOKEN")

    if not github_token:
        print("Warning: GH_TOKEN environment variable not set. Skipping Gist creation.")
        return None

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    filename = f"arxiv_report_{now.strftime('%Y%m%d')}.md"

    # Gist APIリクエスト
    url = "https://api.github.com/gists"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "description": f"arXiv 論文レポート ({date_str})",
        "public": public,
        "files": {
            filename: {
                "content": markdown_content
            }
        }
    }

    try:
        print(f"Creating {'public' if public else 'secret'} Gist...")
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        gist_data = response.json()
        gist_url = gist_data.get("html_url")
        print(f"Gist created successfully: {gist_url}")

        return gist_url
    except requests.exceptions.RequestException as e:
        print(f"Failed to create Gist: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body: {e.response.text}")
        return None


def save_markdown_report_locally(markdown_content):
    """Markdownレポートをローカルファイルとして保存する（バックアップ用）"""
    now = datetime.now()
    year = now.strftime("%Y")
    date_str = now.strftime("%Y%m%d")

    # ディレクトリ作成（reportsディレクトリ以下に保存）
    report_dir = os.path.join(REPORTS_DIR, year)
    os.makedirs(report_dir, exist_ok=True)

    # Markdownファイル保存
    md_filepath = os.path.join(report_dir, f"{date_str}.md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"Markdown report saved locally: {md_filepath}")
    return md_filepath


def send_email_summary(paper_count, gist_url=None, local_filepath=None):
    """論文数とGist URLを含む簡潔なメールを送信する"""
    sender_email = os.getenv("GMAIL_SENDER")
    receiver_email = os.getenv("GMAIL_RECEIVER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not all([sender_email, receiver_email, app_password]):
        print("\nError: Email environment variables (GMAIL_SENDER, GMAIL_RECEIVER, GMAIL_APP_PASSWORD) are not set.")
        print("Skipping email sending.")
        return

    print("\nSending email summary...")

    today_str = datetime.now().strftime("%Y-%m-%d")

    # メールメッセージの作成
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"arXiv デイリーレポート ({today_str})"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    # メール本文を作成
    if gist_url:
        email_body = f"""arXiv デイリーレポート ({today_str})

本日の関連論文数: {paper_count}件

レポート閲覧: {gist_url}
"""
        if local_filepath:
            email_body += f"\nローカルバックアップ: {local_filepath}\n"
    else:
        email_body = f"""arXiv デイリーレポート ({today_str})

本日の関連論文数: {paper_count}件
"""
        if local_filepath:
            email_body += f"\nレポートファイル: {local_filepath}\n"

    # テキストパートのアタッチ
    part_text = MIMEText(email_body, 'plain', 'utf-8')
    msg.attach(part_text)

    # GmailのSMTPサーバーに接続して送信
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"Email sent successfully to {receiver_email}!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def main():
    papers_to_process = fetch_and_filter_papers()

    processed_papers = []
    if papers_to_process:
        for i, paper in enumerate(papers_to_process):
            try:
                print(f"\n--- Processing paper {i+1}/{len(papers_to_process)}: {paper['title'][:50]}... ---")
                print("  - Evaluating authors...")
                paper["authors_evaluation"] = evaluate_authors_via_semantic_scholar(paper["authors"])
                print("    -> Author evaluation complete.")
                max_h_index = 0
                if paper["authors_evaluation"]:
                    max_h_index = max(author.get("hIndex", 0) for author in paper["authors_evaluation"])
                paper["preprint_score"] = max_h_index
                processed_papers.append(paper)
            except Exception as e:
                print(f"An error occurred while processing paper ID {paper['id']}: {e}")
                continue

    print("\nAll processing finished!")

    # Markdownレポートを生成
    markdown_report = generate_markdown_report(processed_papers)

    # GitHub Gistを作成（Secret Gist）
    gist_url = create_gist(markdown_report, public=False)

    # ローカルにバックアップを保存
    local_filepath = save_markdown_report_locally(markdown_report)

    # 論文数とGist URLを含む簡潔なメールを送信
    send_email_summary(len(processed_papers), gist_url=gist_url, local_filepath=local_filepath)


if __name__ == "__main__":
    main()
