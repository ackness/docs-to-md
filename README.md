# Docs-to-Markdown [D2M]

Docs-to-Markdown is a tool to convert `readthedocs` project to `markdown`.

# Usage

```bash
pip install docs-to-md
```

```bash
d2m --url [target_url]
```

example:

```bash
# use jina api
d2m -u https://example-sphinx-basic.readthedocs.io/en/latest/ -t saved/demo

# use openai api
# not recommend, seems like ollama reader-lm is not good enough compare to jina api
# make sure you have installed `ollama` and run ollama with `ollama run reader-lm`
d2m -u https://example-sphinx-basic.readthedocs.io/en/latest/ -t saved/demo-local -nj -a http://localhost:11434/v1 -m reader-lm
```
