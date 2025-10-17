# process_papers_and_email.py
import html
import os
import pathlib
import smtplib
import time
import webbrowser
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


def escape_html_preserve_math(text):
    r"""MathJax数式を保持しながらHTMLエスケープする

    LaTeX数式記号（$, \(, \), \[, \]など）はそのまま保持し、
    HTMLの特殊文字（<, >, &）のみをエスケープする。
    また、数式記号の周辺に適切なスペースを挿入してMathJaxの認識を改善する。
    """
    import re

    # まず基本的なHTMLエスケープ（数式記号は含まない）
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')

    # インライン数式 $...$ の周辺にスペースを確保
    # 前にスペースがない場合は追加（ただし文頭は除く）
    text = re.sub(r'(?<!\s)(?<!^)\$', r' $', text)
    # 後ろにスペースがない場合は追加（ただし文末、句読点の前は除く）
    text = re.sub(r'\$(?!\s)(?![.,;:!?\)])', r'$ ', text)

    # \(...\) 形式のインライン数式の周辺にもスペースを確保
    text = re.sub(r'(?<!\s)\\\(', r' \\(', text)
    text = re.sub(r'\\\)(?!\s)(?![.,;:!?\)])', r'\\) ', text)

    return text


def generate_html_report(processed_papers):
    """HTMLレポートを直接生成する"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    html_content = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>arXiv 論文レポート ({today_str})</title>
        <script type="text/javascript" id="MathJax-script" async
            src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js">
        </script>
        <script>
            MathJax = {{
                tex: {{
                    inlineMath: [['$', '$'], ['\\(', '\\)']],
                    displayMath: [['$$', '$$'], ['\\[', '\\]']]
                }}
            }};
        </script>
        <style>
            body {{ font-family: sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            h1, h2, h3 {{ color: #0056b3; }}
            h1 {{ border-bottom: 3px solid #0056b3; padding-bottom: 10px; }}
            h2 {{ border-bottom: 2px solid #0056b3; padding-bottom: 5px; margin-top: 40px; }}
            h3 {{ border-bottom: 1px solid #ccc; padding-bottom: 3px; }}
            .paper-header {{
                position: relative;
            }}
            .paper-header:hover::after {{
                content: "🔗";
                position: absolute;
                margin-left: 10px;
                opacity: 0.7;
                cursor: pointer;
            }}
            .paper-meta {{
                color: #666;
                font-size: 0.9em;
                margin: 10px 0;
            }}
            .keywords {{
                background-color: #e3f2fd;
                padding: 5px 10px;
                border-radius: 5px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .abstract {{
                border-left: 5px solid #eee;
                padding: 15px 20px;
                margin: 20px 0;
                background-color: #f9f9f9;
                font-style: italic;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #f2f2f2;
                font-weight: bold;
            }}
            a {{ color: #007bff; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .no-papers {{
                text-align: center;
                padding: 50px;
                color: #666;
                font-size: 1.2em;
            }}
            hr {{
                border: none;
                height: 2px;
                background-color: #eee;
                margin: 30px 0;
            }}
        </style>
    </head>
    <body>
        <h1>arXiv 論文レポート ({today_str})</h1>
    """

    if not processed_papers:
        html_content += '<div class="no-papers">本日、キーワードに合致する新着論文はありませんでした。</div>'
    else:
        processed_papers.sort(key=lambda p: p.get("preprint_score", 0), reverse=True)
        for i, paper in enumerate(processed_papers):
            score = paper.get("preprint_score", 0)
            score_label, _ = get_score_label_and_class(score)
            score_emoji = get_score_emoji(score)
            paper_id = extract_arxiv_id(paper['id'])
            published_date = pd.to_datetime(paper['published']).strftime('%Y-%m-%d %H:%M')

            html_content += f"""
        <h2 class="paper-header">
            <a id="{paper_id}">■</a>
            <a href="{paper['url']}" target="_blank">{escape_html_preserve_math(paper['title'])}</a>
            {score_emoji} Score: {score} ({score_label})
        </h2>

        <div class="keywords">Keywords: {' • '.join(paper['keywords'])}</div>
        <div class="paper-meta">公開日: {published_date}</div>
        """

            if paper.get("authors_evaluation"):
                html_content += """
        <h3>著者情報 (Semantic Scholar)</h3>
        <table>
            <tr><th>著者</th><th>h-index</th><th>被引用数</th><th>論文数</th></tr>
        """
                for author_eval in paper["authors_evaluation"]:
                    html_content += f"""
            <tr>
                <td><a href="{author_eval['semantic_scholar_url']}" target="_blank">{html.escape(author_eval['name'])}</a></td>
                <td>{author_eval['hIndex']}</td>
                <td>{author_eval['citations']:,}</td>
                <td>{author_eval['papers']}</td>
            </tr>
        """
                html_content += "</table>"

            html_content += f"""
        <h3>アブストラクト (原文)</h3>
        <div class="abstract">{escape_html_preserve_math(paper.get('summary', 'N/A'))}</div>
        <hr>
        """

    html_content += """
    </body>
    </html>
    """

    return html_content



def get_github_html_url():
    """git remoteの情報からGitHub上のHTMLファイルURLを生成する"""
    import subprocess
    import re

    try:
        # git remoteのURLを取得
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return None

        remote_url = result.stdout.strip()

        # SSH形式 (git@github.com:user/repo.git) またはHTTPS形式を解析
        # SSH形式の場合
        ssh_match = re.match(r'git@github\.com:(.+)/(.+?)(?:\.git)?$', remote_url)
        if ssh_match:
            user, repo = ssh_match.groups()
        else:
            # HTTPS形式の場合
            https_match = re.match(r'https://github\.com/(.+)/(.+?)(?:\.git)?$', remote_url)
            if https_match:
                user, repo = https_match.groups()
            else:
                return None

        # 現在のブランチ名を取得
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=SCRIPT_DIR,
            capture_output=True,
            text=True,
            timeout=5
        )

        if branch_result.returncode != 0:
            branch = "main"  # デフォルトブランチ
        else:
            branch = branch_result.stdout.strip()

        # レポートファイルの相対パスを生成
        now = datetime.now()
        year = now.strftime("%Y")
        date_str = now.strftime("%Y%m%d")
        relative_path = f"reports/{year}/{date_str}.html"

        # GitHub上のHTMLファイルURLを生成
        github_url = f"https://github.com/{user}/{repo}/blob/{branch}/{relative_path}"
        return github_url

    except Exception as e:
        print(f"Failed to generate GitHub URL: {e}")
        return None


def save_html_report(html_content):
    """HTMLレポートをローカルファイルとして保存する"""
    now = datetime.now()
    year = now.strftime("%Y")
    date_str = now.strftime("%Y%m%d")

    # ディレクトリ作成（reportsディレクトリ以下に保存）
    html_dir = os.path.join(REPORTS_DIR, year)
    os.makedirs(html_dir, exist_ok=True)

    # HTMLファイル保存
    html_filepath = os.path.join(html_dir, f"{date_str}.html")
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"HTML report saved: {html_filepath}")

    # GitHub上のHTMLファイルURLを取得
    github_url = get_github_html_url()

    return html_filepath, github_url


def send_email_summary(paper_count, report_filepath, github_url=None):
    """論文数とGitHub URLを含む簡潔なメールを送信する"""
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
    if github_url:
        email_body = f"""arXiv デイリーレポート ({today_str})

本日の関連論文数: {paper_count}件

レポート閲覧: {github_url}

ローカルファイル: {report_filepath}
"""
    else:
        email_body = f"""arXiv デイリーレポート ({today_str})

本日の関連論文数: {paper_count}件

レポートファイル: {report_filepath}
"""

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

    # HTMLレポートを直接生成
    html_report = generate_html_report(processed_papers)

    # HTMLレポートをローカルファイルに保存
    report_filepath, github_url = save_html_report(html_report)

    # 論文数とGitHub URLを含む簡潔なメールを送信
    send_email_summary(len(processed_papers), report_filepath, github_url)


if __name__ == "__main__":
    main()
