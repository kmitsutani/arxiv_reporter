# arXiv Paper Reporter

arXivの論文フィードを監視し、キーワードに基づいてフィルタリングした論文のデイリーレポートを生成するシステムです。著者の評価にSemantic Scholar APIを使用し、数式をMathML形式で表示するHTML形式のメールレポートを送信します。

## 機能

- **論文取得**: arXiv RSS フィード（hep-th、math-ph、quant-ph）から論文を取得
- **キーワードフィルタリング**: 量子場の理論、代数的量子場理論、共形ブートストラップなどのキーワードで論文をフィルタリング
- **著者評価**: Semantic Scholar APIを使用して著者のh-index、被引用数、論文数を取得
- **スコアリング**: 著者の最高h-indexに基づいて論文をスコアリング
- **数式サポート**: LaTeX数式をMathMLに変換（Chrome 109+、Firefox、Safari、Edgeで完全サポート）
- **HTMLメール送信**: レスポンシブデザインのHTML形式でメール送信
- **設定可能なバックアップ**: HTMLとMarkdownレポートをユーザー指定のディレクトリに保存（デフォルト: `~/.cache/arxiv-reporter/reports`）
- **GitHub Actions**: 毎日自動でレポートを生成してメール送信

## セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd arxiv-reporter
```

### 2. Python依存関係のインストール

```bash
python3 -m venv venv
source venv/bin/activate  # Windowsの場合: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 設定ファイルのカスタマイズ（オプション）

`config.json`を編集して、キーワード、RSSフィード、バックアップディレクトリをカスタマイズできます：

```json
{
  "keywords": [
    "axiomatic quantum field theory",
    "algebraic quantum field theory",
    "AQFT",
    ...
  ],
  "rss_feeds": [
    "https://rss.arxiv.org/rss/hep-th",
    "https://rss.arxiv.org/rss/math-ph",
    "https://rss.arxiv.org/rss/quant-ph"
  ],
  "backup_dir": "~/.cache/arxiv-reporter/reports"
}
```

### 4. 環境変数の設定

以下の環境変数を設定します：

```bash
export GMAIL_SENDER="your-email@gmail.com"
export GMAIL_RECEIVER="recipient@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
```

**注意**: Gmailのアプリパスワードは、Googleアカウントの2段階認証を有効にした後、[アプリパスワード設定](https://myaccount.google.com/apppasswords)から生成できます。

### 5. ローカルでの実行

```bash
source venv/bin/activate
python process_papers_and_email.py
```

## GitHub Actionsでの自動実行

### 必要なSecrets

GitHub Actionsで自動実行するには、リポジトリのSecretsに以下の環境変数を設定します：

1. GitHubリポジトリの **Settings** > **Secrets and variables** > **Actions** に移動
2. 以下のSecretsを追加：
   - `GMAIL_SENDER`: 送信元メールアドレス
   - `GMAIL_RECEIVER`: 受信先メールアドレス
   - `GMAIL_APP_PASSWORD`: Gmailアプリパスワード

### ワークフローの実行スケジュール

`.github/workflows/daily-report.yml`が以下のスケジュールで自動実行されます：

- **定期実行**: 毎日UTC 00:00（日本時間 09:00）
- **手動実行**: GitHubの **Actions** タブから "Daily arXiv Report" ワークフローを選択して手動実行可能

### GitHub Actionsでの注意点

- **バックアップディレクトリ**: GitHub Actionsでは、バックアップファイルは保存されません（一時的なランナー環境のため）。メール送信のみが行われます。
- **レート制限**: Semantic Scholar APIのレート制限（1秒あたり1リクエスト）を考慮して、スクリプト内で`time.sleep(1)`を使用しています。

## ディレクトリ構造

```
arxiv-reporter/
├── process_papers_and_email.py  # メインスクリプト
├── config.json                  # 設定ファイル（キーワード、RSS、バックアップ先）
├── requirements.txt             # Python依存関係
├── .github/
│   └── workflows/
│       └── daily-report.yml     # GitHub Actionsワークフロー
├── venv/                        # Python仮想環境（.gitignoreで除外）
├── CLAUDE.md                    # Claude Code用プロジェクト情報
├── README.md                    # このファイル
└── handover.md                  # 引き継ぎ資料（開発者向け）
```

## レポートの形式

### HTMLメール

- **レスポンシブデザイン**: モバイルとデスクトップの両方に対応
- **スコアリング**: 著者のh-indexに基づいて論文をランク付け
  - 🏆 **世界的権威** (h-index ≥ 100)
  - 🏅 **トップ研究者** (h-index ≥ 50)
  - 🟢 **中核研究者** (h-index ≥ 20)
  - 🔵 **注目研究者** (h-index ≥ 10)
  - ⚪ **若手研究者** (h-index < 10)
- **著者情報テーブル**: Semantic Scholarの著者ページへのリンク付き
- **数式サポート**: LaTeX数式をMathMLに変換（ブラウザネイティブレンダリング）

### ローカルバックアップ

`config.json`で指定したディレクトリ（デフォルト: `~/.cache/arxiv-reporter/reports`）に以下の形式で保存されます：

```
~/.cache/arxiv-reporter/reports/
└── 2025/
    ├── 20251023.html
    └── 20251023.md
```

## キーワードのカスタマイズ

`config.json`の`keywords`配列を編集して、監視するキーワードをカスタマイズできます：

```json
{
  "keywords": [
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
    "MERA"
  ]
}
```

## RSSフィードのカスタマイズ

`config.json`の`rss_feeds`配列を編集して、監視するarXivカテゴリを変更できます：

```json
{
  "rss_feeds": [
    "https://rss.arxiv.org/rss/hep-th",
    "https://rss.arxiv.org/rss/math-ph",
    "https://rss.arxiv.org/rss/quant-ph"
  ]
}
```

利用可能なarXivカテゴリは[arXiv RSS feeds](https://arxiv.org/help/rss)を参照してください。

## トラブルシューティング

### メールが送信されない

1. 環境変数が正しく設定されているか確認
2. Gmailのアプリパスワードが正しいか確認
3. 2段階認証が有効になっているか確認
4. GmailのSMTPサーバー（smtp.gmail.com:465）へのアクセスが許可されているか確認

### GitHub Actionsでワークフローが失敗する

1. Repository Secretsが正しく設定されているか確認
2. Actionsログを確認してエラーメッセージを確認
3. 依存関係のインストールエラーの場合、`requirements.txt`を確認

### Semantic Scholar APIのレート制限

大量の論文を処理する場合、APIのレート制限に達する可能性があります。スクリプトには1秒の遅延が含まれていますが、必要に応じて`process_papers_and_email.py`の`time.sleep()`の値を増やしてください。

### 数式が正しく表示されない

- MathMLはChrome 109以降、Firefox、Safari、Edgeでサポートされています
- 古いブラウザやメールクライアントを使用している場合、数式が正しく表示されない可能性があります
- HTMLメールを表示できないメールクライアントの場合、フォールバック用のテキストメールが表示されます

## 技術スタック

- **Python 3.9+**: メインプログラミング言語
- **feedparser**: arXiv RSSフィードのパース
- **pandas**: データ処理
- **requests**: Semantic Scholar API呼び出し
- **latex2mathml**: LaTeX数式のMathML変換
- **markdown**: Markdownテキスト処理（バックアップ用）
- **GitHub Actions**: 自動実行環境

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 貢献

バグ報告や機能リクエストは、GitHubのIssuesで受け付けています。

## 関連資料

- [引き継ぎ資料 (handover.md)](handover.md) - 開発者向けの詳細な技術情報
- [CLAUDE.md](CLAUDE.md) - Claude Code用のプロジェクト情報
