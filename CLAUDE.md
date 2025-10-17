# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an arXiv paper monitoring and reporting system that fetches papers from arXiv RSS feeds, filters them by keywords, evaluates authors using the Semantic Scholar API, and generates daily reports in both Markdown and HTML formats. Reports are automatically emailed to recipients.

## Commands

### Running the Application
```bash
# Run the main reporter (activates venv and runs the script)
./run_reporter.sh

# Or manually activate venv and run
source venv/bin/activate
python process_papers_and_email.py
```

### Environment Setup
The application requires these environment variables (set in run_reporter.sh):
- `GMAIL_SENDER`: Email address for sending reports
- `GMAIL_RECEIVER`: Email address for receiving reports
- `GMAIL_APP_PASSWORD`: Gmail app password for authentication

## Architecture

### Core Workflow
1. **Paper Fetching** (`fetch_and_filter_papers()`): Retrieves papers from multiple arXiv RSS feeds (hep-th, math-ph, quant-ph)
2. **Keyword Filtering**: Filters papers based on predefined physics/quantum field theory keywords
3. **Author Evaluation** (`evaluate_authors_via_semantic_scholar()`): Uses Semantic Scholar API to get author metrics (h-index, citations, paper count)
4. **Scoring**: Papers are scored based on the highest h-index among authors
5. **Report Generation**: Creates both Markdown and HTML reports with author tables and paper rankings
6. **Output**: Saves reports locally and sends email summaries with web links

### Key Configuration
- **Keywords**: Focused on quantum field theory, algebraic QFT, conformal bootstrap, and related physics topics
- **RSS Feeds**: arXiv high-energy physics theory, mathematical physics, and quantum physics
- **Reports Directory**: `/home/kazuya/projects/arxiv-reporter/reports/`
- **HTML Output**: `/var/www/html/arxiv_report/{year}/{date}.html`
- **Web Access**: Reports accessible at `192.168.3.21/arxiv_report/{year}/{date}.html`

### Dependencies
The main script imports: feedparser, markdown, pandas, requests, smtplib, and standard library modules for HTML processing, email handling, and file operations.

### Rate Limiting
The application includes sleep delays (1 second) between API calls to respect Semantic Scholar rate limits.