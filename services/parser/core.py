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
from services.parser.javascript import parse_javascript
from services.parser.static import parse_static
from services.parser.classify import classify_file
from services.parser.graph import build_dependency_graph  # re-exported for convenience
from libs.utils import read_file_safe

import re


def parse_python(file_path: Path, content: str) -> dict[str, Any]:
    """Extract an AST summary from a Python source file."""
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])

    import_pattern = re.compile(r"^(?:from|import)\s+([\w.]+)")
    deps = [m for m in import_pattern.findall(content) if not m.startswith(".")]

    func_pattern = re.compile(r"(?:async\s+)?def\s+(\w+)\(([^)]*)\):")
    functions = []
    for match in func_pattern.finditer(content):
        functions.append({
            "name": match.group(1),
            "signature": f"{match.group(1)}({match.group(2)})",
            "async": "async" in content[max(0, match.start() - 10):match.start()],
        })

    class_pattern = re.compile(r"class\s+(\w+)(?:\(([^)]*)\))?:")
    classes = [{"name": m[0], "extends": m[1]} for m in class_pattern.findall(content)]

    return {
        "language": "python",
        "lines_of_code": loc,
        "functions": functions,
        "classes": classes,
        "dependencies": list(set(deps)),
    }


def parse_file(file_path: Path) -> ParsedFile | None:
    """Parse a single file and return a :class:`ParsedFile`, or ``None`` on error."""
    content = read_file_safe(file_path)
    if content is None:
        return None

    lang = detect_language(file_path)
    classification = classify_file(file_path, content)

    if lang in ("javascript", "typescript"):
        ast = parse_javascript(file_path, content)
    elif lang == "python":
        ast = parse_python(file_path, content)
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


__all__ = ["parse_file", "parse_python", "build_dependency_graph"]
