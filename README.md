# Docs-to-Markdown [D2M]

---

![PyPI - Version](https://img.shields.io/pypi/v/docs-to-md)
![PyPI - Downloads](https://img.shields.io/pypi/dm/docs-to-md)

---

Docs-to-Markdown[D2M] is a tool using `Jina.ai` api or `openai` api (default: `ollama: reader-lm`) to convert project documentation to `markdown`.

For now, it only supports `readthedocs` project, but it will add more project type in the future.

# Usage

## Install

```bash
pip install docs-to-md
```

## Convert the documentation of a readthedocs project to markdown

```bash
d2m --help
```

```
Usage: d2m [OPTIONS]

Options:
  -u, --url TEXT           Root url of the documentation project
  -p, --project-name TEXT  Name of the project
  -t, --target-path TEXT   Path to save the html and md files
  -nj, --no_jina           Use open-based api (default: ollama reader-lm) to
                           parse html to markdown, if true, --token is
                           required, and will ignore --api and --model
  --api TEXT               Base url of the openai/jina api, only works when
                           --no_jina is false
  --token TEXT             Api key of the openai/jina api
  --model TEXT             Model to use for parsing html to markdown
  --help                   Show this message and exit.
```

### Example:

```bash

# use jina api
d2m -u https://example-sphinx-basic.readthedocs.io/en/latest/ -t saved/demo

# use openai api
# not recommend, seems like ollama reader-lm is not good enough compare to jina api
# make sure you have installed `ollama` and run ollama with `ollama run reader-lm`
d2m -u https://example-sphinx-basic.readthedocs.io/en/latest/ -t saved/demo-local -nj -a http://localhost:11434/v1 -m reader-lm
```


## Jina API Limitation

You can get the `api_key` from [Jina](https://jina.ai/).

[Jina Reader API](https://jina.ai/reader)

| Endpoint  	| Description   	| Rate limit with API key (premium plan) 	| Rate limit with API key 	| Rate limit w/o API key 	|
|-----------	|---------------	|----------------------------------------	|-------------------------	|------------------------	|
| r.jina.ai 	| Reader Read   	| 1000 RPM                               	| 200 RPM                 	| 20 RPM                 	|
| s.jina.ai 	| Reader Search 	| 100 RPM                                	| 40 RPM                  	| 5 RPM                  	|
