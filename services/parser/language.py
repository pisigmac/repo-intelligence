from pathlib import Path


EXTENSION_MAP = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".pyi": "python",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".rb": "ruby",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".json": "json",
    ".ipynb": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "markdown",
    ".sh": "shell",
    ".bash": "shell",
    ".dockerfile": "dockerfile",
    ".gql": "graphql",
    ".graphql": "graphql",
    ".svg": "svg",
    ".lock": "lockfile",
    ".txt": "text",
    ".snap": "snapshot",
    ".ambr": "snapshot",
    ".svelte": "svelte",
    ".vue": "vue",
}

FILENAME_MAP = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    ".gitignore": "gitignore",
    ".eslintignore": "gitignore",
    ".npmignore": "gitignore",
    ".prettierignore": "gitignore",
    ".dockerignore": "gitignore",
    ".editorconfig": "config",
    ".gitattributes": "config",
    ".prettierrc": "config",
    ".eslintrc": "config",
    ".babelrc": "config",
    ".npmrc": "config",
    "codeowners": "config",
    "citation.cff": "citation",
    "license": "documentation",
}


def detect_language(file_path: Path) -> str:
    lower_name = file_path.name.lower()
    if lower_name in FILENAME_MAP:
        return FILENAME_MAP[lower_name]
    return EXTENSION_MAP.get(file_path.suffix.lower(), "unknown")
