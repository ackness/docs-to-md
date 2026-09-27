"""docs-to-md: convert ReadTheDocs-style documentation sites to Markdown."""

from docs_to_md.engines import (
    Converter,
    JinaConverter,
    LocalConverter,
    OpenAIConverter,
    Page,
    make_converter,
)
from docs_to_md.pipeline import ConvertResult, PageResult, convert_readthedocs

__version__ = "0.2.0"

__all__ = [
    "ConvertResult",
    "Converter",
    "JinaConverter",
    "LocalConverter",
    "OpenAIConverter",
    "Page",
    "PageResult",
    "__version__",
    "convert_readthedocs",
    "make_converter",
]
