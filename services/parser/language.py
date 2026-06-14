from pathlib import Path


EXTENSION_MAP = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".md": "markdown",
    ".markdown": "markdown",
    ".sh": "shell",
    ".bash": "shell",
    ".dockerfile": "dockerfile",
}

FILENAME_MAP = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    ".gitignore": "gitignore",
}


def detect_language(file_path: Path) -> str:
    lower_name = file_path.name.lower()
    if lower_name in FILENAME_MAP:
        return FILENAME_MAP[lower_name]
    return EXTENSION_MAP.get(file_path.suffix.lower(), "unknown")
