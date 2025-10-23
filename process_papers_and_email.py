# process_papers_and_email.py
import os
import json
import smtplib
import time
import re
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import feedparser
import pandas as pd
import requests
import markdown
from latex2mathml.converter import convert as latex_to_mathml


def fetch_and_filter_papers(rss_feeds, keywords):
    print("Fetching papers from RSS feeds...")
    unique_papers = {}
    for url in rss_feeds:
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
                  in summary_lower for keyword in keywords]

        if sum(is_hit) > 0:
            true_idx = [i for i, val in enumerate(is_hit) if val]
            hit_keywords = [keywords[i] for i in true_idx]

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
    if score >= 100: return "世界的権威", "score-s-plus"
    elif score >= 50: return "トップ研究者", "score-s"
    elif score >= 20: return "中核研究者", "score-a"
    elif score >= 10: return "注目研究者", "score-b"
    else: return "若手研究者", "score-c"


def get_score_emoji(score):
    if score >= 100: return "🏆"
    elif score >= 50: return "🏅"
    elif score >= 20: return "🟢"
    elif score >= 10: return "🔵"
    else: return "⚪"


def extract_arxiv_id(arxiv_url):
    """arXiv URLからarXiv ID（例：2409.12345）を抽出する"""
    match = re.search(r'arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)', arxiv_url)
    if match:
        return match.group(1)
    # フォールバック：URLの最後の部分を使用
    return arxiv_url.split('/')[-1]


def convert_latex_to_mathml(text):
    """テキスト内のLaTeX数式をMathMLに変換する

    $...$ (inline) と $$...$$ (display) の両方に対応
    """
    def replace_display_math(match):
        latex = match.group(1).strip()
        try:
            mathml = latex_to_mathml(latex)
            return f'<div style="text-align: center; margin: 1em 0;">{mathml}</div>'
        except Exception as e:
            print(f"Warning: Failed to convert display math: {latex[:50]}... Error: {e}")
            return f'<div style="text-align: center; margin: 1em 0;"><code>{latex}</code></div>'

    def replace_inline_math(match):
        latex = match.group(1).strip()
        try:
            mathml = latex_to_mathml(latex)
            return mathml
        except Exception as e:
            print(f"Warning: Failed to convert inline math: {latex[:50]}... Error: {e}")
            return f'<code>{latex}</code>'

    # まず $$...$$ (display math) を処理
    text = re.sub(r'\$\$(.*?)\$\$', replace_display_math, text, flags=re.DOTALL)

    # 次に $...$ (inline math) を処理
    text = re.sub(r'\$(.*?)\$', replace_inline_math, text)

    return text


def generate_markdown_report(processed_papers):
    """GitHub Flavored Markdownレポートを生成する（バックアップ用）"""
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


def generate_html_report(processed_papers):
    """HTMLレポートを生成する（MathML対応）"""
    today_str = datetime.now().strftime("%Y-%m-%d")

    # CSSスタイル
    css = """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .paper {
            margin: 30px 0;
            padding: 20px;
            background-color: #f9f9f9;
            border-left: 4px solid #3498db;
            border-radius: 4px;
        }
        .paper h2 {
            margin-top: 0;
            color: #2c3e50;
        }
        .paper h2 a {
            color: #2c3e50;
            text-decoration: none;
        }
        .paper h2 a:hover {
            color: #3498db;
        }
        .score {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            margin: 10px 0;
        }
        .score-s-plus { background-color: #ffd700; color: #000; }
        .score-s { background-color: #ff6b6b; color: white; }
        .score-a { background-color: #4ecdc4; color: white; }
        .score-b { background-color: #45b7d1; color: white; }
        .score-c { background-color: #95a5a6; color: white; }
        .meta {
            color: #7f8c8d;
            font-size: 0.9em;
            margin: 10px 0;
        }
        .keywords {
            color: #e74c3c;
            font-weight: 500;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .abstract {
            background-color: white;
            padding: 15px;
            border-left: 3px solid #95a5a6;
            margin: 15px 0;
            font-style: italic;
            color: #555;
        }
        .no-papers {
            text-align: center;
            color: #7f8c8d;
            padding: 40px;
            font-style: italic;
        }
    </style>
    """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>arXiv 論文レポート ({today_str})</title>
    {css}
</head>
<body>
    <div class="container">
        <h1>arXiv 論文レポート ({today_str})</h1>
"""

    if not processed_papers:
        html_content += '<div class="no-papers">本日、キーワードに合致する新着論文はありませんでした。</div>'
    else:
        processed_papers.sort(key=lambda p: p.get("preprint_score", 0), reverse=True)
        for paper in processed_papers:
            score = paper.get("preprint_score", 0)
            score_label, score_class = get_score_label_and_class(score)
            score_emoji = get_score_emoji(score)
            published_date = pd.to_datetime(paper['published']).strftime('%Y-%m-%d %H:%M')

            html_content += f'''
        <div class="paper">
            <h2>{score_emoji} <a href="{paper['url']}" target="_blank">{paper['title']}</a></h2>
            <div class="score {score_class}">Score: {score} ({score_label})</div>
            <div class="meta">
                <span class="keywords">Keywords: {' • '.join(paper['keywords'])}</span><br>
                公開日: {published_date}
            </div>
'''

            # 著者情報
            if paper.get("authors_evaluation"):
                html_content += '''
            <h3>著者情報 (Semantic Scholar)</h3>
            <table>
                <tr>
                    <th>著者</th>
                    <th>h-index</th>
                    <th>被引用数</th>
                    <th>論文数</th>
                </tr>
'''
                for author_eval in paper["authors_evaluation"]:
                    name = author_eval['name']
                    url = author_eval['semantic_scholar_url']
                    h_index = author_eval['hIndex']
                    citations = f"{author_eval['citations']:,}"
                    papers_count = author_eval['papers']
                    html_content += f'''
                <tr>
                    <td><a href="{url}" target="_blank">{name}</a></td>
                    <td>{h_index}</td>
                    <td>{citations}</td>
                    <td>{papers_count}</td>
                </tr>
'''
                html_content += '''
            </table>
'''

            # アブストラクト（LaTeX数式をMathMLに変換）
            abstract = paper.get('summary', 'N/A')
            abstract_with_mathml = convert_latex_to_mathml(abstract)
            html_content += f'''
            <h3>アブストラクト (原文)</h3>
            <div class="abstract">{abstract_with_mathml}</div>
        </div>
'''

    html_content += """
    </div>
</body>
</html>
"""

    return html_content



def save_report_locally(html_content, markdown_content, backup_dir):
    """HTMLとMarkdownレポートをローカルファイルとして保存する（バックアップ用）"""
    now = datetime.now()
    year = now.strftime("%Y")
    date_str = now.strftime("%Y%m%d")

    # チルダ展開とディレクトリ作成
    backup_dir = os.path.expanduser(backup_dir)
    report_dir = os.path.join(backup_dir, year)
    os.makedirs(report_dir, exist_ok=True)

    # HTMLファイル保存
    html_filepath = os.path.join(report_dir, f"{date_str}.html")
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"HTML report saved locally: {html_filepath}")

    # Markdownファイル保存
    md_filepath = os.path.join(report_dir, f"{date_str}.md")
    with open(md_filepath, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    print(f"Markdown report saved locally: {md_filepath}")

    return html_filepath, md_filepath


def send_html_email(html_content, paper_count):
    """HTMLメールを送信する（MathML対応）"""
    sender_email = os.getenv("GMAIL_SENDER")
    receiver_email = os.getenv("GMAIL_RECEIVER")
    app_password = os.getenv("GMAIL_APP_PASSWORD")

    if not all([sender_email, receiver_email, app_password]):
        print("\nError: Email environment variables (GMAIL_SENDER, GMAIL_RECEIVER, GMAIL_APP_PASSWORD) are not set.")
        print("Skipping email sending.")
        return

    print("\nSending HTML email...")

    today_str = datetime.now().strftime("%Y-%m-%d")

    # メールメッセージの作成
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"arXiv デイリーレポート ({today_str}) - {paper_count}件"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    # テキストパート（フォールバック用）
    text_body = f"""arXiv デイリーレポート ({today_str})

本日の関連論文数: {paper_count}件

※このメールはHTML形式で表示してください。
"""
    part_text = MIMEText(text_body, 'plain', 'utf-8')
    msg.attach(part_text)

    # HTMLパート
    part_html = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(part_html)

    # GmailのSMTPサーバーに接続して送信
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()
        print(f"HTML email sent successfully to {receiver_email}!")
    except Exception as e:
        print(f"Failed to send email: {e}")


def main():
    # 設定ファイルを読み込む
    with open('config.json', 'r', encoding='utf-8') as fin:
        config = json.load(fin)

    # 論文を取得してフィルタリング
    papers_to_process = fetch_and_filter_papers(config['rss_feeds'], config['keywords'])

    # 著者評価とスコアリング
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

    # Markdownレポートを生成（バックアップ用）
    markdown_report = generate_markdown_report(processed_papers)

    # HTMLレポートを生成（MathML対応）
    html_report = generate_html_report(processed_papers)

    # ローカルにバックアップ保存
    backup_dir = config.get('backup_dir', '~/.cache/arxiv-reporter/reports')
    save_report_locally(html_report, markdown_report, backup_dir)

    # HTMLメールを送信
    send_html_email(html_report, len(processed_papers))


if __name__ == "__main__":
    main()
