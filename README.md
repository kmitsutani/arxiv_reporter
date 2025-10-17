# arXiv Paper Reporter

arXivの論文フィードを監視し、キーワードに基づいてフィルタリングした論文のデイリーレポートを生成するシステムです。著者の評価にSemantic Scholar APIを使用し、HTMLレポートを生成してメールで通知します。

## 機能

- **論文取得**: arXiv RSS フィード（hep-th、math-ph、quant-ph）から論文を取得
- **キーワードフィルタリング**: 量子場の理論、代数的量子場理論、共形ブートストラップなどのキーワードで論文をフィルタリング
- **著者評価**: Semantic Scholar APIを使用して著者のh-index、被引用数、論文数を取得
- **スコアリング**: 著者の最高h-indexに基づいて論文をスコアリング
- **レポート生成**: MarkdownとHTML形式でレポートを生成（MathJax対応）
- **メール通知**: レポートのGitHub URLとローカルパスを含むメールを送信
- **GitHub Actions**: 毎日自動でレポートを生成し、リポジトリにコミット

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd arxiv-reporter
```

### 2. Python依存関係のインストール

```bash
python -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install feedparser pandas requests
```

### 3. 環境変数の設定

ローカルで実行する場合は、`run_reporter.sh`に環境変数を設定します：

```bash
export GMAIL_SENDER="your-email@gmail.com"
export GMAIL_RECEIVER="recipient@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
```

**注意**: Gmailのアプリパスワードは、Googleアカウントの2段階認証を有効にした後、[アプリパスワード設定](https://myaccount.google.com/apppasswords)から生成できます。

### 4. GitHub Actionsの設定

GitHub Actionsで自動実行するには、リポジトリのSecretsに以下の環境変数を設定します：

1. GitHubリポジトリの **Settings** > **Secrets and variables** > **Actions** に移動
2. 以下のSecretsを追加：
   - `GMAIL_SENDER`: 送信元メールアドレス
   - `GMAIL_RECEIVER`: 受信先メールアドレス
   - `GMAIL_APP_PASSWORD`: Gmailアプリパスワード

### 5. ワークフローの有効化

`.github/workflows/daily-report.yml`が自動的に以下のスケジュールで実行されます：

- **定期実行**: 毎日UTC 00:00（日本時間 09:00）
- **手動実行**: GitHubの **Actions** タブから "Daily arXiv Report" ワークフローを選択して手動実行可能

## ローカルでの実行

### シェルスクリプトで実行

```bash
./run_reporter.sh
```

### Pythonスクリプトを直接実行

```bash
source venv/bin/activate
python process_papers_and_email.py
```

## ディレクトリ構造

```
arxiv-reporter/
├── process_papers_and_email.py  # メインスクリプト
├── run_reporter.sh              # 実行用シェルスクリプト
├── reports/                     # 生成されたレポート
│   └── YYYY/                    # 年ごとのディレクトリ
│       └── YYYYMMDD.html        # 日付ごとのHTMLレポート
├── .github/
│   └── workflows/
│       └── daily-report.yml     # GitHub Actionsワークフロー
├── venv/                        # Python仮想環境
├── CLAUDE.md                    # Claude Code用プロジェクト情報
└── README.md                    # このファイル
```

## レポートの閲覧

### GitHubで閲覧

メールに記載されたGitHub URLをクリックすると、GitHubのHTMLプレビュー機能でレポートを閲覧できます。

例: `https://github.com/username/arxiv-reporter/blob/main/reports/2025/20251017.html`

### ローカルで閲覧

生成されたHTMLファイルを直接ブラウザで開きます：

```bash
open reports/2025/20251017.html  # macOS
xdg-open reports/2025/20251017.html  # Linux
```

## キーワードのカスタマイズ

`process_papers_and_email.py`の`KEYWORDS`リストを編集して、監視するキーワードをカスタマイズできます：

```python
KEYWORDS = [
    "axiomatic quantum field theory",
    "algebraic quantum field theory",
    "AQFT",
    "Ryu-Takayanagi",
    "measurement-induced",
    "resource theory",
    "resource theoretic",
    "Haag",
    "LSZ",
    "conformal bootstrap",
    "duality",
    "non-perturbative",
    "Yang Mills",
    "Renormalization Group",
    "MERA",
]
```

## RSSフィードのカスタマイズ

`RSS_FEEDS`リストを編集して、監視するarXivカテゴリを変更できます：

```python
RSS_FEEDS = [
    "https://rss.arxiv.org/rss/hep-th",
    "https://rss.arxiv.org/rss/math-ph",
    "https://rss.arxiv.org/rss/quant-ph",
]
```

利用可能なarXivカテゴリは[arXiv RSS feeds](https://arxiv.org/help/rss)を参照してください。

## トラブルシューティング

### メールが送信されない

1. 環境変数が正しく設定されているか確認
2. Gmailのアプリパスワードが正しいか確認
3. 2段階認証が有効になっているか確認

### GitHub Actionsでワークフローが失敗する

1. Repository Secretsが正しく設定されているか確認
2. Actionsログを確認してエラーメッセージを確認
3. リポジトリの権限設定で **Settings** > **Actions** > **General** > **Workflow permissions** が "Read and write permissions" になっているか確認

### Semantic Scholar APIのレート制限

大量の論文を処理する場合、APIのレート制限に達する可能性があります。スクリプトには1秒の遅延が含まれていますが、必要に応じて`time.sleep()`の値を増やしてください。

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能リクエストは、GitHubのIssuesで受け付けています。
# arxiv_reporter
