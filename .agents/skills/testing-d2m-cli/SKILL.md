---
name: testing-d2m-cli
description: How to run and end-to-end test the docs-to-md `d2m` CLI (uv-managed, pluggable engines, failure-path fixtures)
---

# Testing the d2m CLI

## Running
- `d2m` is a console script installed by `uv sync` into the project `.venv`. Run with:
  `cd ~/repos/docs-to-md && ~/.local/bin/uv run d2m <args>` (or `uv run --project <dir> d2m <args>`).
- Top-level commands: `readthedocs <url>` (main converter) and `version`. Old flag-style interface (`d2m -u <url>`) was removed — verify flags go *after* the `readthedocs` subcommand.
- Useful options: `-o/--output-dir`, `-n/--name`, `-e/--engine local|jina|openai`, `-k/--api-key` (env: `JINA_API_KEY`/`OPENAI_API_KEY`/`D2M_API_KEY`), `-c/--concurrency` (min 1), `--timeout`, `--retries` (min 0), `--save-html`, `-v`.

## Good live fixture site
- `https://example-sphinx-basic.readthedocs.io/en/latest/` — small (4 pages: index, usage, api, generated/lumache → `generated_lumache.md`), stable, no auth. Local engine needs no keys.

## Testing per-page failure paths without external deps
Serve a fake Sphinx TOC locally — discovery keys on `<a class="reference internal" href="*.html">` links:
```bash
mkdir -p /tmp/d2m-site && cd /tmp/d2m-site
printf '<ul><li><a class="reference internal" href="ok.html">ok</a></li>'\
'<li><a class="reference internal" href="missing.html">missing</a></li></ul>'\
'<div itemprop="articleBody"><h1>Index</h1></div>' > index.html
printf '<div itemprop="articleBody"><h1>OK</h1></div>' > ok.html
python3 -m http.server 8321 &   # missing.html -> 404
d2m readthedocs http://localhost:8321/ -o /tmp/d2m-fail --retries 0
# expect: exit 1, "2/3 pages", per-page "failed:" lines, no traceback
```
Note: failures on the *index* page itself (dead host / 404 root) currently surface as a rich traceback with exit 1, not a per-page failure line — that's expected behavior to verify, not necessarily a bug.

## Engines & secrets (Devin Secrets Needed)
- `local`: fully offline, no secrets — always testable.
- `jina`: hits `https://r.jina.ai`; without `JINA_API_KEY` expect per-page 403s (exit 1, graceful). Real run needs `JINA_API_KEY`.
- `openai`: OpenAI-compatible API; default `--api-base http://localhost:11434/v1`, `-m reader-lm`. Needs a running ollama (`ollama pull reader-lm`); if none is running, expect graceful per-page "Connection error" failures. Do not install ollama just for testing unless asked.

## Gotchas
- `pkill -f "http.server <port>"` will match your own exec shell's command line and kill it — use `pkill -f 'http.server' ` from a different cwd or `fuser -k <port>/tcp`.
- `--concurrency 0` / `--retries -1` are typer-validated (exit 2) — quick arg-validation checks.
- `d2m` bare prints help and exits 2 (no_args_is_help) — normal typer behavior.
