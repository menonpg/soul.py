"""Modulizer — Zero-deps memory segmentation for soul.py.

Auto-segments large MEMORY.md files into indexed modules for ~90% token savings.
"""

from .chunker import chunk_markdown
from .classifier import classify_chunks
from .splitter import split_into_modules
from .indexer import generate_index
from .modulize import modulize, auto_modulize

__all__ = [
    "chunk_markdown",
    "classify_chunks",
    "split_into_modules",
    "generate_index",
    "modulize",
    "auto_modulize",
]
