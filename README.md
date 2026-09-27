# Docs-to-Markdown [D2M]

![PyPI - Version](https://img.shields.io/pypi/v/docs-to-md)
![PyPI - Downloads](https://img.shields.io/pypi/dm/docs-to-md)

`docs-to-md` (`d2m`) converts ReadTheDocs/Sphinx documentation sites into clean
Markdown files — useful as input for LLMs, RAG pipelines, or offline reading.

It discovers every page linked from a project's table of contents, downloads
the pages concurrently, and converts each one with a pluggable engine:

| Engine   | Description                                                        | Needs a key?        |
|----------|--------------------------------------------------------------------|---------------------|
| `local`  | Offline HTML → Markdown via `markdownify` (default, zero config)   | No                  |
| `jina`   | Hosted [Jina Reader](https://jina.ai/reader/) API (`r.jina.ai`)    | `JINA_API_KEY`      |
| `openai` | Any OpenAI-compatible chat API — Ollama `reader-lm`, OpenAI, vLLM… | `OPENAI_API_KEY`    |

## Install

```bash
pip install docs-to-md
# or run directly with uv
uvx docs-to-md --help
```

## Usage

```bash
d2m readthedocs <root-url> [OPTIONS]
```

```text
Options:
  -o, --output-dir PATH   Directory the <project>/ output is written to
                          [default: output]
  -n, --name TEXT         Project name (default: derived from the URL)
  -e, --engine            local | jina | openai  [default: local]
  -k, --api-key TEXT      API key (or JINA_API_KEY / OPENAI_API_KEY / D2M_API_KEY)
      --api-base TEXT     OpenAI-compatible base URL [default: http://localhost:11434/v1]
  -m, --model TEXT        Model for the openai engine [default: reader-lm]
  -c, --concurrency INT   Max parallel requests [default: 4]
      --timeout FLOAT     Per-request timeout in seconds [default: 30]
      --retries INT       Retries on 429/5xx/network errors [default: 3]
      --save-html         Also keep the downloaded HTML under html/
  -v, --verbose           Debug logging
```

### Examples

```bash
# offline, no keys needed
d2m readthedocs https://example-sphinx-basic.readthedocs.io/en/latest/

# Jina Reader API (export JINA_API_KEY=... first)
d2m readthedocs https://example-sphinx-basic.readthedocs.io/en/latest/ -e jina

# local Ollama model (`ollama pull reader-lm`, serving on :11434)
d2m readthedocs https://example-sphinx-basic.readthedocs.io/en/latest/ \
    -e openai --api-base http://localhost:11434/v1 -m reader-lm
```

Output layout:

```text
output/
└── <project>/
    ├── index.md
    ├── <page>.md
    └── html/           # only with --save-html
        └── <page>.html
```

## Library use

```python
import asyncio
from docs_to_md import LocalConverter, convert_readthedocs

result = asyncio.run(
    convert_readthedocs(
        "https://example-sphinx-basic.readthedocs.io/en/latest/",
        converter=LocalConverter(),
        output_dir="output",
    )
)
for page in result.failed:
    print("failed:", page.url, page.error)
```

## Jina API rate limits

Get an API key from [Jina](https://jina.ai/). Unauthenticated requests to
`r.jina.ai` are heavily rate-limited (20 RPM) and may be rejected — export
`JINA_API_KEY` (or pass `--api-key`) for reliable results.

## Development

This project is managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync            # create .venv and install all deps (incl. dev group)
uv run pytest      # run the offline test suite (network calls are mocked)
uv run ruff check  # lint
uv run ruff format # format
uv build           # build wheel + sdist
```

Pre-commit hooks (ruff + hygiene checks):

```bash
uv run pre-commit install
uv run pre-commit run --all-files
```
