# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Agent Instructions

You're working inside the **WAT framework** (Workflows, Agents, Tools). This architecture separates concerns so that probabilistic AI handles reasoning while deterministic code handles execution. That separation is what makes this system reliable.

## The WAT Architecture

**Layer 1: Workflows (The Instructions)**

- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**

- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself

**Layer 3: Tools (The Execution)**

- Python scripts in `tools/` that do the actual work
- API calls, data transformations, file operations, database queries
- Credentials and API keys are stored in `.env`
- These scripts are consistent, testable, and fast

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps. By offloading execution to deterministic scripts, you stay focused on orchestration and decision-making where you excel.

## Tool Inventory

All tools run from the project root: `python tools/<script>.py`

| Tool | CLI | Reads | Writes |
|------|-----|-------|--------|
| `discover_competitors.py` | `--query "AI writing tools"` and/or `--url "https://company.com"` | DuckDuckGo search | `.tmp/competitors.json` |
| `scrape_competitor.py` | `--url "https://company.com"` | Live site via Playwright (falls back to requests) | `.tmp/scraped/{domain}.json` |
| `detect_tech_stack.py` | `--url "https://company.com"` | Live site (Wappalyzer + DNS) | `.tmp/techstack/{domain}.json` |
| `fetch_github_presence.py` | `--company "Notion" --domain "notion.so"` | GitHub API (`GITHUB_TOKEN` optional but recommended) | `.tmp/github/{domain}.json` |
| `analyze_seo.py` | `--domain "notion.so"` | `.tmp/scraped/{domain}.json` — **must run after scrape** | `.tmp/seo/{domain}.json` |
| `export_to_sheets.py` | `[--sheet-id "SHEET_ID"]` | All `.tmp/` subdirs | Google Sheets (Master tab + one tab per competitor) |
| `export_to_markdown.py` | `[--output "path.md"]` | All `.tmp/` subdirs | `.tmp/competitor_analysis.md` |
| `export_to_html.py` | `[--output "path.html"]` | All `.tmp/` subdirs | `.tmp/competitor_analysis.html` (self-contained, no server needed) |

**Critical dependency:** `analyze_seo.py` reads `raw_html` from `.tmp/scraped/{domain}.json`. Always run `scrape_competitor.py` for a domain before `analyze_seo.py`.

## Standard Research Pipeline

**Fully automated (recommended):** use `scout.py` to run the entire pipeline with a single command:

```bash
python scout.py --url https://writesonic.com
python scout.py --query "AI writing tools" --max-competitors 8
python scout.py --url https://notion.so --export sheets
```

`--max-competitors` defaults to 5. `--export` accepts `html` (default), `markdown`, or `sheets`.

**Manual / step-by-step:** follow `workflows/scout.md`. The execution order per competitor is:

```
scrape_competitor → detect_tech_stack → fetch_github_presence → analyze_seo
```

Then export with one or more of the export tools. Check `.tmp/errors.json` after each step — errors are appended there and don't raise exceptions to the caller.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium   # required for scrape_competitor.py
```

## Running Tests

```bash
# All tests
pytest

# Single test file
pytest tests/test_discover_competitors.py

# Single test by name
pytest tests/test_discover_competitors.py::test_deduplicate_removes_duplicate_domain
```

Tests use `pytest-mock` for mocking. No network calls are made in tests — all external services are patched. `conftest.py` just adds the project root to `sys.path`.

## Environment Variables

Required in `.env`:

```
GITHUB_TOKEN=       # GitHub personal access token (read-only); unauthenticated requests are rate-limited to 60/hour
GOOGLE_SHEET_ID=    # Existing sheet ID for export_to_sheets.py; if omitted, a new sheet is created automatically
```

Google OAuth for Sheets (`credentials.json` + `token.json`) is configured separately — see `workflows/export_to_google_sheets.md` for the one-time setup.

## Tool Module Interface

Each tool in `tools/` exposes a callable function that `scout.py` imports directly. These are the stable internal APIs:

| Script | Importable function | Signature |
|--------|---------------------|-----------|
| `discover_competitors.py` | `discover(query, url)` | returns `list[dict]` |
| `scrape_competitor.py` | `scrape(url)` | returns `dict` |
| `detect_tech_stack.py` | `detect(url)` | returns `dict` |
| `fetch_github_presence.py` | `fetch(company, domain)` | returns `dict` |
| `analyze_seo.py` | `analyze(domain)` | returns `dict` |
| `export_to_html.py` | `export(output?)` | returns output path |
| `export_to_markdown.py` | `export(output?)` | returns output path |
| `export_to_sheets.py` | `export(sheet_id?)` | returns Sheet URL |

Non-fatal errors are appended to `.tmp/errors.json` and never raised to the caller — callers must check that file after each step.

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/` based on what your workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when things fail**
When you hit an error:

- Read the full error message and trace
- Fix the script and retest (if it uses paid API calls or credits, check with me before running again)
- Document what you learned in the workflow (rate limits, timing quirks, unexpected behavior)

**3. Keep workflows current**
Workflows should evolve as you learn. When you find better methods, discover constraints, or encounter recurring issues, update the workflow. Don't create or overwrite workflows without asking unless explicitly told to — these are preserved instructions, not throwaway notes.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:

1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Move on with a more robust system

## File Structure

```
.tmp/               # All intermediates — fully regenerable, gitignored
  competitors.json  # Output of discover_competitors.py
  scraped/          # {domain}.json per competitor
  techstack/        # {domain}.json per competitor
  github/           # {domain}.json per competitor
  seo/              # {domain}.json per competitor
  errors.json       # Appended by any tool that catches a non-fatal error
tools/              # Python scripts for deterministic execution
workflows/          # Markdown SOPs
tests/              # pytest test suite (one file per tool)
.env                # API keys and environment variables
credentials.json    # Google OAuth client secrets (gitignored)
token.json          # Google OAuth refresh token (gitignored)
```

**Core principle:** Local files are just for processing. Anything the user needs to see or use lives in cloud services (Google Sheets) or is exported as a portable file (HTML/Markdown). Everything in `.tmp/` is disposable.

## Bottom Line

You sit between what the user wants (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.
