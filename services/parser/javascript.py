import re
from pathlib import Path


JS_PATTERNS = {
    "require": re.compile(r'''require\s*\(\s*['"]([^'"]+)['"]\s*\)'''),
    "import": re.compile(
        r'''import\s+(?:(?:\{[^}]*\}|[\w*]+)\s+from\s+)?['"]([^'"]+)['"];?'''
    ),
    "function_decl": re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)"),
    "arrow_function": re.compile(
        r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=]+)\s*=>"
    ),
    "method": re.compile(r"(\w+)\s*\((.*)\)(?:\s*:\s*[^{]+)?\s*\{"),
    "express_route": re.compile(
        r'''(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]'''
    ),
    "middleware_use": re.compile(r"(?:app|router)\.use\s*\(\s*([^)]+)\)"),
    "class_decl": re.compile(r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"),
    "export_default": re.compile(r"export\s+default\s+(?:function\s+)?(\w+)"),
    "export_named": re.compile(r"export\s+\{([^}]+)\}"),
    "decorator": re.compile(r"@(\w+)(?:\s*\(([^)]*)\))?"),
    "anonymous_function": re.compile(r"function\s*\(([^)]*)\)\s*\{"),
    "arrow_callback": re.compile(r"\(([^)]*)\)\s*=>\s*\{"),
}


def _count_loc(content: str) -> int:
    lines = content.splitlines()
    count = 0
    in_block_comment = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("//"):
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue
        count += 1
    return count


def _decorators_before(content: str, pos: int) -> list[str]:
    """Collect decorators immediately before a declaration at `pos`."""
    prefix = content[:pos]
    lines = prefix.splitlines()
    decorators: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        match = JS_PATTERNS["decorator"].match(stripped)
        if match:
            decorators.append(match.group(1))
        else:
            break
    return list(reversed(decorators))


def parse_javascript(file_path: Path, content: str) -> dict:
    loc = _count_loc(content)

    deps = []
    deps.extend(JS_PATTERNS["require"].findall(content))
    deps.extend(JS_PATTERNS["import"].findall(content))

    functions = []
    for match in JS_PATTERNS["function_decl"].finditer(content):
        prefix = content[max(0, match.start() - 20):match.start()]
        functions.append({
            "type": "function",
            "name": match.group(1),
            "signature": f"{match.group(1)}({match.group(2)})",
            "async": "async" in prefix,
            "decorators": _decorators_before(content, match.start()),
        })

    for match in JS_PATTERNS["anonymous_function"].finditer(content):
        functions.append({
            "type": "anonymous_function",
            "name": None,
            "signature": f"({match.group(1)})",
            "async": False,
            "decorators": _decorators_before(content, match.start()),
        })

    for match in JS_PATTERNS["arrow_callback"].finditer(content):
        functions.append({
            "type": "arrow_function",
            "name": None,
            "signature": f"({match.group(1)})",
            "async": False,
            "decorators": _decorators_before(content, match.start()),
        })

    for match in JS_PATTERNS["arrow_function"].finditer(content):
        functions.append({
            "type": "arrow_function",
            "name": match.group(1),
            "signature": f"{match.group(1)}()",
            "async": False,
            "decorators": _decorators_before(content, match.start()),
        })

    for match in JS_PATTERNS["method"].finditer(content):
        functions.append({
            "type": "method",
            "name": match.group(1),
            "signature": f"{match.group(1)}({match.group(2)})",
            "async": False,
            "decorators": _decorators_before(content, match.start()),
        })

    routes = []
    for match in JS_PATTERNS["express_route"].finditer(content):
        routes.append({
            "method": match.group(1).upper(),
            "path": match.group(2),
        })

    middlewares = []
    for match in JS_PATTERNS["middleware_use"].finditer(content):
        middlewares.append(match.group(1).strip())

    classes = []
    for match in JS_PATTERNS["class_decl"].finditer(content):
        classes.append({
            "name": match.group(1),
            "extends": match.group(2),
            "decorators": _decorators_before(content, match.start()),
        })

    exports = []
    exports.extend(JS_PATTERNS["export_default"].findall(content))
    for match in JS_PATTERNS["export_named"].finditer(content):
        exports.extend([x.strip().split()[0] for x in match.group(1).split(",") if x.strip()])

    return {
        "language": "javascript",
        "lines_of_code": loc,
        "functions": functions,
        "routes": routes,
        "middlewares": middlewares,
        "classes": classes,
        "exports": exports,
        "dependencies": list(set(deps)),
    }
