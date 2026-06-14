import re
from pathlib import Path


CLASSIFICATION_PATTERNS = {
    "route": re.compile(r'\b(app|router)\.(get|post|put|delete|patch|use)\s*\(', re.IGNORECASE),
    "middleware": re.compile(r'\b(middleware|verifyToken|authenticate|auth|authorize)\b', re.IGNORECASE),
    "test": re.compile(r'\b(test|it|describe)\s*\(', re.IGNORECASE),
    "controller": re.compile(r'\b(controller|handler|service|repository)\b', re.IGNORECASE),
    "component": re.compile(r'\b(export\s+default\s+function|export\s+function\s+\w+\s*\([^)]*\)\s*\{\s*return\s*<)', re.IGNORECASE),
}

EXTENSION_CLASSIFICATION = {
    ".html": "static",
    ".css": "static",
    ".scss": "static",
    ".json": "config",
    ".yaml": "config",
    ".yml": "config",
    ".toml": "config",
    ".sql": "database",
    ".md": "documentation",
    ".dockerfile": "infrastructure",
}

FILENAME_CLASSIFICATION = {
    "dockerfile": "infrastructure",
    "makefile": "infrastructure",
    ".gitignore": "config",
    "readme.md": "documentation",
}


def classify_file(file_path: Path, content: str) -> str:
    lower_name = file_path.name.lower()
    if lower_name in FILENAME_CLASSIFICATION:
        return FILENAME_CLASSIFICATION[lower_name]

    ext = file_path.suffix.lower()
    if ext in EXTENSION_CLASSIFICATION:
        return EXTENSION_CLASSIFICATION[ext]

    fname = lower_name
    if CLASSIFICATION_PATTERNS["test"].search(fname):
        return "test"
    if "test" in fname or "spec" in fname:
        return "test"
    if "middleware" in fname:
        return "middleware"
    if "route" in fname:
        return "route"
    if "config" in fname:
        return "config"

    scores = {}
    for category, pattern in CLASSIFICATION_PATTERNS.items():
        scores[category] = len(pattern.findall(content))

    if scores:
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best

    return "utility"
