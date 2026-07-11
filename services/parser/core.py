"""Pure parsing logic — no Kafka, no DB, no FastAPI.

This module is intentionally free of heavy framework dependencies so it can
be imported in unit tests without a running Docker stack.
"""
import sys
import os
from pathlib import Path
from typing import Any

# Allow direct execution and local imports when run outside Docker.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from services.parser.models import ParsedFile
from services.parser.language import detect_language
from services.parser.static import parse_static
from services.parser.classify import classify_file
from services.parser.graph import build_dependency_graph  # re-exported for convenience
from services.parser.treesitter_parser import parse_python_ast, parse_js_ts_ast
from libs.utils import read_file_safe


def parse_file(file_path: Path) -> ParsedFile | None:
    """Parse a single file and return a :class:`ParsedFile`, or ``None`` on error."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    lang = detect_language(file_path)
    classification = classify_file(file_path, content)

    if lang == "javascript":
        ast = parse_js_ts_ast(content, is_typescript=False)
    elif lang == "typescript":
        ast = parse_js_ts_ast(content, is_typescript=True)
    elif lang == "python":
        ast = parse_python_ast(content)
    else:
        ast = parse_static(file_path, lang, content)

    return ParsedFile(
        path=str(file_path),
        language=lang,
        classification=classification,
        ast_summary=ast,
        dependencies=ast.get("dependencies", []),
        lines_of_code=ast.get("lines_of_code", 0),
    )


__all__ = ["parse_file", "build_dependency_graph"]
