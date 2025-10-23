# 開発引き継ぎ資料 (handover.md)

このドキュメントは、次の開発者やコーディングエージェントがこのプロジェクトをスムーズに引き継げるように、技術的な詳細と設計判断をまとめたものです。

## 📋 プロジェクト概要

**目的**: arXivの論文を自動監視し、キーワードに基づいてフィルタリングした論文を著者評価付きでHTMLメール送信する。

**主な変更履歴**:
- 初期実装: GitHub Gistを使用したMarkdownレポート共有
- 現在: HTMLメール送信 + MathML数式サポート + 設定可能なバックアップ

---

## 🏗️ アーキテクチャ

### 処理フロー

```
1. 設定ファイル読み込み (config.json)
   ↓
2. arXiv RSSフィード取得
   ↓
3. キーワードフィルタリング
   ↓
4. 著者評価 (Semantic Scholar API)
   ↓
5. スコアリング (最高h-index)
   ↓
6. レポート生成 (HTML + Markdown)
   ↓
7. ローカルバックアップ保存
   ↓
8. HTMLメール送信
```

### ファイル構成

```
process_papers_and_email.py  # メインスクリプト (約480行)
├── fetch_and_filter_papers()           # RSSフィード取得とフィルタリング
├── evaluate_authors_via_semantic_scholar()  # 著者評価
├── get_score_label_and_class()         # スコアラベルとCSSクラス取得
├── get_score_emoji()                   # スコアに応じた絵文字取得
├── extract_arxiv_id()                  # arXiv IDの抽出
├── convert_latex_to_mathml()           # LaTeX→MathML変換 ⭐新機能
├── generate_markdown_report()          # Markdownレポート生成（バックアップ用）
├── generate_html_report()              # HTMLレポート生成 ⭐新機能
├── save_report_locally()               # ローカル保存 ⭐更新
├── send_html_email()                   # HTMLメール送信 ⭐新機能
└── main()                              # メイン処理
```

---

## 🔑 重要な設計判断

### 1. GitHub Gist → HTMLメール送信への変更

**理由**:
- Gistは外部依存で、トークン管理が必要
- HTMLメールなら直接閲覧可能で、追加の認証不要
- 数式をMathMLで埋め込むことで、外部リソースに依存しない

**影響**:
- `GH_TOKEN`環境変数が不要に
- `create_gist()`関数を削除
- `send_html_email()`関数を新規実装

### 2. LaTeX数式 → MathML変換

**選択したアプローチ**: `latex2mathml`ライブラリを使用

**検討した選択肢**:
1. **外部API (codecogs.com)** - 外部依存、ネットワーク必須
2. **matplotlib + LaTeX** - GitHub Actionsで重い（~数百MB）
3. **sympy** - パース機能が限定的
4. **latex2mathml** ✅ - 軽量、依存関係なし、Production/Stable

**実装**: `process_papers_and_email.py:104-133`
- インライン数式: `$...$` → `<math>...</math>`
- ディスプレイ数式: `$$...$$` → `<div><math>...</math></div>`
- エラーハンドリング: 変換失敗時は`<code>`タグで表示

**ブラウザサポート**:
- Chrome 109+ (2023年1月〜)
- Firefox: 完全サポート
- Safari: 完全サポート
- Edge: 完全サポート

### 3. バックアップ先の設定可能化

**設計**:
- `config.json`に`backup_dir`フィールドを追加
- デフォルト値: `~/.cache/arxiv-reporter/reports`
- チルダ展開対応: `os.path.expanduser()`を使用

**理由**:
- リポジトリ内の`reports/`ディレクトリは不要（Gitで管理する必要なし）
- ユーザーごとに保存場所をカスタマイズ可能
- キャッシュディレクトリ（`~/.cache/`）はLinuxの標準的な慣習

**実装**: `process_papers_and_email.py:365-388`

---

## 📦 依存関係

### requirements.txt

```txt
feedparser==6.0.11      # arXiv RSSフィードのパース
pandas==2.3.0           # データ処理
requests==2.32.4        # HTTP通信（Semantic Scholar API）
markdown>=3.5           # Markdownテキスト処理（バックアップ用）
latex2mathml>=3.77.0    # LaTeX→MathML変換
```

### 標準ライブラリ（インストール不要）

- `smtplib`, `email.mime.*` - メール送信
- `json` - 設定ファイル読み込み
- `datetime` - 日付処理
- `re` - 正規表現（LaTeX数式検出、arXiv ID抽出）
- `os`, `time` - ファイル操作、スリープ

---

## 🔐 環境変数

### 必須

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `GMAIL_SENDER` | 送信元メールアドレス | `sender@gmail.com` |
| `GMAIL_RECEIVER` | 受信先メールアドレス | `receiver@gmail.com` |
| `GMAIL_APP_PASSWORD` | Gmailアプリパスワード | `abcd efgh ijkl mnop` |

### 削除された環境変数

- ~~`GH_TOKEN`~~ - GitHub Gist機能を削除したため不要

---

## ⚙️ 設定ファイル (config.json)

### 構造

```json
{
  "keywords": [string[]],      // フィルタリング用キーワード
  "rss_feeds": [string[]],     // arXiv RSSフィードURL
  "backup_dir": string         // バックアップディレクトリ（オプション）
}
```

### デフォルト値

- `backup_dir`: 未設定の場合は`~/.cache/arxiv-reporter/reports`を使用
  - 実装: `config.get('backup_dir', '~/.cache/arxiv-reporter/reports')`

### キーワードの仕様

- 大文字小文字を区別しない（`.lower()`で正規化）
- タイトルまたはアブストラクトに含まれていればマッチ
- 複数キーワードマッチは`OR`条件（いずれか1つでOK）

---

## 🎨 HTMLレポートの設計

### CSSスタイル

- **レスポンシブデザイン**: `max-width: 900px`、モバイル対応
- **カラースキーム**:
  - スコアS+: 🏆 ゴールド (`#ffd700`)
  - スコアS: 🏅 レッド (`#ff6b6b`)
  - スコアA: 🟢 ティール (`#4ecdc4`)
  - スコアB: 🔵 ブルー (`#45b7d1`)
  - スコアC: ⚪ グレー (`#95a5a6`)
- **テーブル**: Semantic Scholar著者ページへのリンク付き

### スコアリングロジック

```python
def get_score_label_and_class(score):
    if score >= 100: return "世界的権威", "score-s-plus"
    elif score >= 50: return "トップ研究者", "score-s"
    elif score >= 20: return "中核研究者", "score-a"
    elif score >= 10: return "注目研究者", "score-b"
    else: return "若手研究者", "score-c"
```

### 実装場所

- HTML生成: `process_papers_and_email.py:184-361`
- インラインCSS: 190-280行目（メール互換性のため外部CSSは使用しない）

---

## 🌐 外部API

### Semantic Scholar API

**エンドポイント**:
```
GET https://api.semanticscholar.org/graph/v1/author/search?query={name}&fields=hIndex,citationCount,paperCount,url
```

**レート制限**:
- 公式制限: 1秒あたり1リクエスト
- 実装: `time.sleep(1)`を各リクエスト後に挿入

**エラーハンドリング**:
- `requests.exceptions.RequestException`をキャッチ
- エラー発生時は警告を表示し、その著者をスキップ
- スクリプト全体は停止しない

**取得データ**:
```python
{
    "name": str,
    "hIndex": int,
    "citations": int,
    "papers": int,
    "semantic_scholar_url": str
}
```

### arXiv RSS API

**フィード形式**: RSS 2.0

**エントリー構造**:
```python
{
    "id": str,              # arXiv URL
    "title": str,
    "summary": str,         # アブストラクト
    "published": str,       # ISO 8601形式
    "authors": [{"name": str}],
    "link": str
}
```

**重複排除**: `entry.id`をキーとした辞書で管理

---

## 🐛 既知の問題と制約

### 1. GitHub Actions環境でのバックアップ

**問題**: GitHub Actionsの一時的なランナー環境では、バックアップファイルは保存されない。

**対策**: メール送信が主目的なので、バックアップは補助的な機能として扱う。ローカル実行時のみバックアップが有効。

### 2. 著者名の曖昧性

**問題**: Semantic Scholar APIは著者名の文字列検索を行うため、同姓同名の別人が返される可能性がある。

**現状の対策**: 最初にマッチした著者を使用（APIの`data[0]`）。

**将来的な改善案**:
- arXivのAuthor IDとSemantic ScholarのAuthor IDをマッピング
- 論文タイトルや共著者情報を使った検証

### 3. 数式変換の制約

**問題**: `latex2mathml`は全てのLaTeXコマンドをサポートしているわけではない。

**対策**:
- エラーハンドリングで変換失敗時は`<code>`タグで表示
- 警告メッセージを出力（デバッグ用）

**よくある失敗例**:
- カスタムマクロ（`\newcommand`など）
- 特殊な数学記号

---

## 🧪 テスト

### 構文チェック

```bash
source venv/bin/activate
python -m py_compile process_papers_and_email.py
```

### MathML変換テスト

テストスクリプト（`.gitignore`で除外）:
```bash
python test_mathml.py
```

### 手動テスト（メール送信なし）

```python
# process_papers_and_email.pyの最後を一時的に変更
if __name__ == "__main__":
    # main()をコメントアウトして個別テスト
    with open('config.json', 'r') as f:
        config = json.load(f)
    papers = fetch_and_filter_papers(config['rss_feeds'], config['keywords'])
    print(f"Found {len(papers)} papers")
```

---

## 🚀 GitHub Actions

### ワークフロー (`.github/workflows/daily-report.yml`)

**トリガー**:
- `cron: '0 0 * * *'` - 毎日UTC 00:00（JST 09:00）
- `workflow_dispatch` - 手動実行可能

**ステップ**:
1. リポジトリのチェックアウト
2. Python 3.10のセットアップ
3. 依存関係のインストール (`pip install -r requirements.txt`)
4. スクリプトの実行

**環境変数**:
- `GMAIL_SENDER`, `GMAIL_RECEIVER`, `GMAIL_APP_PASSWORD`
- Repository Secretsから取得

**実行時間**:
- 論文数により変動（Semantic Scholar APIのレート制限による）
- 目安: 10論文で約10-15秒

---

## 🔧 よくある開発タスク

### 1. 新しいキーワードを追加

**ファイル**: `config.json`

```json
{
  "keywords": [
    "existing keyword",
    "new keyword"  // 追加
  ]
}
```

### 2. 新しいarXivカテゴリを追加

**ファイル**: `config.json`

```json
{
  "rss_feeds": [
    "https://rss.arxiv.org/rss/hep-th",
    "https://rss.arxiv.org/rss/new-category"  // 追加
  ]
}
```

### 3. スコアリングロジックの変更

**ファイル**: `process_papers_and_email.py`

**関数**: `get_score_label_and_class()` (76-82行目)

```python
def get_score_label_and_class(score):
    if score >= 150: return "新ランク", "score-new"  # 追加
    if score >= 100: return "世界的権威", "score-s-plus"
    # ...
```

**注意**: CSSクラス（`.score-new`）も追加する必要あり（`generate_html_report()`内）

### 4. メールテンプレートのカスタマイズ

**ファイル**: `process_papers_and_email.py`

**関数**: `generate_html_report()` (184-361行目)

- CSSスタイル: 189-280行目
- HTMLテンプレート: 283-359行目

### 5. バックアップ形式の変更

現在: HTML + Markdown両方を保存

HTMLのみに変更する場合:

**ファイル**: `process_papers_and_email.py`

**関数**: `save_report_locally()` (365-388行目)

```python
# Markdownファイル保存の部分をコメントアウト
# md_filepath = os.path.join(report_dir, f"{date_str}.md")
# with open(md_filepath, "w", encoding="utf-8") as f:
#     f.write(markdown_content)

return html_filepath, None  # 2番目の戻り値をNoneに
```

---

## 📊 パフォーマンス最適化の余地

### 1. 著者評価の並列化

**現状**: 逐次処理（レート制限対応）

**改善案**:
```python
import asyncio
import aiohttp

async def evaluate_authors_async(authors):
    # 非同期処理で複数の著者を並列評価
    # レート制限を守りつつ効率化
    pass
```

**注意**: Semantic Scholar APIのレート制限を超えないよう注意

### 2. キャッシング

**現状**: 毎回全ての著者を評価

**改善案**:
- 著者情報をローカルにキャッシュ（SQLite、JSON等）
- TTL（Time To Live）を設定（例: 30日）

```python
import sqlite3

def get_cached_author(name):
    # キャッシュから取得
    pass

def cache_author(name, data):
    # キャッシュに保存
    pass
```

### 3. 論文の重複検出

**現状**: RSSフィード内の重複のみ除外

**改善案**:
- 過去に処理した論文のIDを保存
- 既に処理済みの論文をスキップ

---

## 🔐 セキュリティ考慮事項

### 1. 環境変数

- **絶対にコミットしない**: `.env`ファイルは`.gitignore`に含まれている
- **GitHub Actions Secrets**: 適切に設定し、ログに出力しない

### 2. Gmailアプリパスワード

- 2段階認証必須
- アプリパスワードは定期的に再生成することを推奨

### 3. APIトークン

- 現在は不要（Semantic Scholar APIは認証不要）
- 将来的にAPIキーが必要になった場合は、環境変数またはSecretsで管理

---

## 🐞 デバッグのヒント

### 1. メールが送信されない

**確認項目**:
```bash
# 環境変数の確認
echo $GMAIL_SENDER
echo $GMAIL_RECEIVER
echo $GMAIL_APP_PASSWORD

# SMTPサーバーへの接続テスト
python -c "import smtplib; server = smtplib.SMTP_SSL('smtp.gmail.com', 465); print('OK')"
```

### 2. MathML変換エラー

**デバッグログ**:
```python
# convert_latex_to_mathml()内でprintデバッグ
print(f"Converting LaTeX: {latex}")
print(f"MathML result: {mathml}")
```

### 3. Semantic Scholar API エラー

**レート制限確認**:
```bash
# APIレスポンスヘッダーを確認
curl -I "https://api.semanticscholar.org/graph/v1/author/search?query=test"
```

---

## 📝 今後の拡張アイデア

### 1. 論文の要約生成

- OpenAI APIやClaude APIを使用
- アブストラクトを日本語で要約

### 2. 論文の類似度計算

- ベクトル埋め込み（embeddings）を使用
- 過去の興味深い論文との類似度をスコアに反映

### 3. Webダッシュボード

- Flask/FastAPIでWebアプリ化
- ブラウザで過去のレポートを閲覧

### 4. Slack/Discord通知

- メールに加えて、SlackやDiscordに通知
- Webhook URLを`config.json`に追加

### 5. 論文のPDF自動ダウンロード

- 高スコア論文のPDFを自動ダウンロード
- ローカルまたはクラウドストレージに保存

---

## 🤝 コントリビューションガイド

### コーディング規約

- **PEP 8準拠**: Pythonの標準スタイルガイド
- **関数名**: `snake_case`
- **定数**: `UPPER_SNAKE_CASE`（現在は未使用）
- **docstring**: 主要な関数に日本語のdocstringを付与

### コミットメッセージ

現在のコミット履歴を参考に：
```
feat: 新機能の追加
fix: バグ修正
docs: ドキュメントのみの変更
refactor: コードのリファクタリング
```

### Pull Request

1. `main`ブランチから新しいブランチを作成
2. 変更を実装
3. テストを実行（構文チェック、MathML変換テスト）
4. Pull Requestを作成

---

## 📞 サポート

### ドキュメント

- **README.md**: ユーザー向けの使用方法
- **CLAUDE.md**: Claude Code用のプロジェクト情報
- **handover.md**: このファイル（開発者向け）

### 問題が発生した場合

1. GitHub Issuesで報告
2. エラーログとスタックトレースを添付
3. 環境情報（Python版、OS）を記載

---

## ✅ チェックリスト

新しい開発者が最初に確認すべき項目：

- [ ] Python 3.9以上がインストールされているか
- [ ] `requirements.txt`から依存関係をインストールしたか
- [ ] `config.json`が存在し、正しい形式か
- [ ] 環境変数（GMAIL_*）が設定されているか
- [ ] `python -m py_compile process_papers_and_email.py`が成功するか
- [ ] `test_mathml.py`が正常に動作するか
- [ ] GitHub Actions Secretsが設定されているか

---

## 📚 参考リンク

- [arXiv RSS Feeds](https://arxiv.org/help/rss)
- [Semantic Scholar API Documentation](https://api.semanticscholar.org/)
- [latex2mathml GitHub Repository](https://github.com/roniemartinez/latex2mathml)
- [MathML Browser Support](https://caniuse.com/mathml)
- [Gmail App Passwords](https://myaccount.google.com/apppasswords)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

---

**最終更新日**: 2025-10-23

**作成者**: Claude Code (Anthropic)

**次の開発者へ**: このプロジェクトは、研究者が最新の論文を効率的に追跡するために作られました。あなたの貢献が、誰かの研究活動をサポートすることを願っています！🚀
