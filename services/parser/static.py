import re
from pathlib import Path


HTML_SCRIPT_SRC = re.compile(r'<script[^>]+src=[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
HTML_LINK_HREF = re.compile(r'<link[^>]+href=[\'"]([^\'"]+)[\'"]', re.IGNORECASE)
CSS_IMPORT = re.compile(r'@import\s+[\'"]([^\'"]+)[\'"];?')
SQL_TABLE = re.compile(r'create\s+table\s+(?:if\s+not\s+exists\s+)?(\w+)', re.IGNORECASE)


def parse_static(file_path: Path, language: str, content: str) -> dict:
    lines = content.splitlines()
    loc = len([l for l in lines if l.strip()])
    deps: list[str] = []

    if language == "html":
        deps.extend(HTML_SCRIPT_SRC.findall(content))
        deps.extend(HTML_LINK_HREF.findall(content))
    elif language == "css":
        deps.extend(CSS_IMPORT.findall(content))

    tables = SQL_TABLE.findall(content) if language == "sql" else []

    return {
        "language": language,
        "lines_of_code": loc,
        "functions": [],
        "classes": [],
        "dependencies": list(set(deps)),
        "tables": tables,
    }
