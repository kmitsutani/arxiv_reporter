# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an arXiv paper monitoring and reporting system that fetches papers from arXiv RSS feeds, filters them by keywords, evaluates authors using the Semantic Scholar API, and generates daily HTML email reports with MathML-formatted mathematical expressions.

## Commands

### Running the Application
```bash
# Activate venv and run
source venv/bin/activate
python process_papers_and_email.py
```

### Setup
```bash
# Install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Environment Variables
The application requires these environment variables:
- `GMAIL_SENDER`: Email address for sending reports
- `GMAIL_RECEIVER`: Email address for receiving reports
- `GMAIL_APP_PASSWORD`: Gmail app password for authentication

**Note**: `GH_TOKEN` is no longer required (GitHub Gist functionality has been removed).

## Architecture

### Core Workflow
1. **Configuration Loading**: Reads `config.json` for keywords, RSS feeds, and backup directory
2. **Paper Fetching** (`fetch_and_filter_papers()`): Retrieves papers from multiple arXiv RSS feeds (hep-th, math-ph, quant-ph)
3. **Keyword Filtering**: Filters papers based on configurable keywords
4. **Author Evaluation** (`evaluate_authors_via_semantic_scholar()`): Uses Semantic Scholar API to get author metrics (h-index, citations, paper count)
5. **Scoring**: Papers are scored based on the highest h-index among authors
6. **LaTeX to MathML Conversion** (`convert_latex_to_mathml()`): Converts LaTeX math expressions to MathML for browser-native rendering
7. **Report Generation**:
   - `generate_markdown_report()`: Creates Markdown reports (for backup only)
   - `generate_html_report()`: Creates styled HTML reports with MathML support
8. **Local Backup** (`save_report_locally()`): Saves HTML and Markdown reports to user-configurable directory (default: `~/.cache/arxiv-reporter/reports`)
9. **Email Sending** (`send_html_email()`): Sends HTML email with embedded MathML expressions

### Key Configuration (config.json)
```json
{
  "keywords": [...],           // Configurable keyword list
  "rss_feeds": [...],          // arXiv RSS feed URLs
  "backup_dir": "~/.cache/arxiv-reporter/reports"  // Backup directory (supports tilde expansion)
}
```

- **Keywords**: Focused on quantum field theory, algebraic QFT, conformal bootstrap, and related physics topics
- **RSS Feeds**: arXiv high-energy physics theory, mathematical physics, and quantum physics
- **Backup Directory**: User-configurable via `config.json` (default: `~/.cache/arxiv-reporter/reports`)
- **Output Format**: HTML with inline CSS and MathML (no external dependencies)

### Dependencies (requirements.txt)
- `feedparser==6.0.11`: arXiv RSS feed parsing
- `pandas==2.3.0`: Data processing
- `requests==2.32.4`: Semantic Scholar API calls
- `markdown>=3.5`: Markdown processing (for backup files)
- `latex2mathml>=3.77.0`: LaTeX to MathML conversion

Standard library modules: `smtplib`, `email.mime.*`, `json`, `datetime`, `re`, `os`, `time`

### MathML Support
- **Conversion**: LaTeX expressions (`$...$` and `$$...$$`) are automatically converted to MathML
- **Browser Support**: Chrome 109+, Firefox, Safari, Edge (native MathML support)
- **Error Handling**: If conversion fails, displays LaTeX code in `<code>` tags with warning message

### Rate Limiting
The application includes sleep delays (1 second) between Semantic Scholar API calls to respect rate limits.