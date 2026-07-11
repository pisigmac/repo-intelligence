> I'm using the writing-plans skill to create the implementation plan.

# Parser Service Improvements — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the parser service so it correctly detects languages, extracts AST summaries, and classifies files for modern polyglot repos (TypeScript, HTML, config, CSS, SQL, Markdown, etc.).

**Architecture:** Extend the existing regex-based parser in `services/parser/main.py` with better extension mapping, reuse the JavaScript parser for TypeScript/TSX, add lightweight AST summaries for static/config files, and tighten classification heuristics. Add unit tests with sample files from the `devpet` repo and a regression test that re-parses it.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, pytest, regex.

---

## Current Anomalies Observed (devpet repo)

1. **TypeScript files have empty `functions`/`classes`/`dependencies`.**
   - Root cause: only `lang == "javascript"` triggers `parse_javascript`; `typescript` falls into the generic "unknown" branch.
2. **Static/config files show `language: "unknown"`.**
   - Examples: `.html`, `.css`, `.json`, `.yaml`, `.toml`, `.sql`, `.md`, `.gitignore`, `Dockerfile`.
3. **Misleading classifications.**
   - `landing-page/index.html` classified as `middleware`.
   - `web-dashboard/index.html` classified as `utility`.
   - `vscode-extension/src/extension.ts` classified as `config`.
   - `deploy-cli/src/index.ts` classified as `middleware`.
4. **Dependency graph is empty.**
   - Root cause: TypeScript imports are not extracted, so local relative imports are never resolved.
5. **Inconsistent lines-of-code counting.**
   - JavaScript excludes single-line `//` comments; TypeScript unknown branch counts all non-empty lines.
6. **No support for TSX, multi-line imports, or `export function/class`.**
   - `JS_PATTERNS` only matches `module.exports` exports and misses `export function`, `export class`, `export default`.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `services/parser/main.py` | Existing parser entrypoint and Kafka handler. Will be refactored to delegate to per-language parsers. |
| `services/parser/language.py` | New module: `detect_language()` and extension map. |
| `services/parser/javascript.py` | New module: JS/TS/TSX AST extraction, improved import/function/class/route detection. |
| `services/parser/static.py` | New module: lightweight AST summaries for HTML, CSS, JSON, YAML, TOML, SQL, Markdown, Dockerfile, etc. |
| `services/parser/classify.py` | New module: file classification heuristics. |
| `services/parser/graph.py` | New module: dependency graph resolution. |
| `services/parser/models.py` | New module: Pydantic models shared across parser modules. |
| `services/parser/tests/test_parser.py` | New test file: unit tests for each module plus devpet regression. |
| `test-repo/devpet-samples/` | New directory: small sample files copied/derived from devpet for deterministic tests. |

---

### Task 1: Extract parser models into a dedicated module

**Files:**
- Create: `services/parser/models.py`
- Modify: `services/parser/main.py`

- [x] **Step 1: Write the failing import test**

Create `services/parser/tests/test_models.py`:

```python
from services.parser.models import ParsedFile, ParsedRepo

def test_parsed_file_model():
    pf = ParsedFile(
        path="/tmp/test.ts",
        language="typescript",
        classification="utility",
        ast_summary={"functions": [], "classes": []},
        dependencies=["react"],
        lines_of_code=10,
    )
    assert pf.language == "typescript"
    assert pf.dependencies == ["react"]
```

- [x] **Step 2: Run test to verify it fails**

```bash
cd /home/oh20210736-ud/Documents/Kimi_projects/In_progress/git/repo-intelligence
python3 -m pytest services/parser/tests/test_models.py -v --confcutdir=services/parser/tests
```

Expected: `ModuleNotFoundError: No module named 'services.parser.models'`.

- [x] **Step 3: Create `services/parser/models.py`**

```python
from pydantic import BaseModel
from typing import Any


class ParsedFile(BaseModel):
    path: str
    language: str
    classification: str
    ast_summary: dict[str, Any]
    dependencies: list[str]
    lines_of_code: int


class ParsedRepo(BaseModel):
    repo_id: str
    commit: str
    files: list[ParsedFile]
    dependency_graph: dict[str, list[str]]
```

- [x] **Step 4: Update `services/parser/main.py` to import from models**

Replace the inline `ParsedFile` and `ParsedRepo` class definitions in `services/parser/main.py` with:

```python
from services.parser.models import ParsedFile, ParsedRepo
```

- [x] **Step 5: Run tests**

```bash
python3 -m pytest services/parser/tests/test_models.py -v --confcutdir=services/parser/tests
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add services/parser/models.py services/parser/main.py services/parser/tests/test_models.py
git commit -m "refactor(parser): extract ParsedFile and ParsedRepo models"
```

---

### Task 2: Expand language detection

**Files:**
- Create: `services/parser/language.py`
- Modify: `services/parser/main.py`
- Test: `services/parser/tests/test_language.py`

- [x] **Step 1: Write failing language detection tests**

Create `services/parser/tests/test_language.py`:

```python
from pathlib import Path
from services.parser.language import detect_language

def test_typescript_detection():
    assert detect_language(Path("src/App.tsx")) == "typescript"
    assert detect_language(Path("src/lib/db.ts")) == "typescript"

def test_static_files():
    assert detect_language(Path("index.html")) == "html"
    assert detect_language(Path("styles.css")) == "css"
    assert detect_language(Path("package.json")) == "json"
    assert detect_language(Path("config.yaml")) == "yaml"
    assert detect_language(Path("wrangler.toml")) == "toml"
    assert detect_language(Path("schema.sql")) == "sql"
    assert detect_language(Path("README.md")) == "markdown"
    assert detect_language(Path("Dockerfile")) == "dockerfile"

def test_unknown_extension():
    assert detect_language(Path("README")) == "unknown"
```

- [x] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest services/parser/tests/test_language.py -v --confcutdir=services/parser/tests
```

Expected: `ModuleNotFoundError` or assertion failures.

- [x] **Step 3: Create `services/parser/language.py`**

```python
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
```

- [x] **Step 4: Update `services/parser/main.py`**

Remove the inline `EXTENSION_MAP` and `detect_language()` function. Add:

```python
from services.parser.language import detect_language
```

- [x] **Step 5: Run tests**

```bash
python3 -m pytest services/parser/tests/test_language.py -v --confcutdir=services/parser/tests
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add services/parser/language.py services/parser/main.py services/parser/tests/test_language.py
git commit -m "feat(parser): expand language detection for static and config files"
```

---

### Task 3: Extract JavaScript/TypeScript AST extraction into a reusable module

**Files:**
- Create: `services/parser/javascript.py`
- Modify: `services/parser/main.py`
- Test: `services/parser/tests/test_javascript.py`

- [x] **Step 1: Write failing tests for TypeScript parsing**

Create `services/parser/tests/test_javascript.py`:

```python
from pathlib import Path
from services.parser.javascript import parse_javascript

TS_SAMPLE = '''
import { useState } from 'react';
import supabase from './lib/supabase';

export function Dashboard() {
  return <div>Hello</div>;
}

export class PetStore {
  constructor(public name: string) {}
}

const handler = async (req: Request) => {
  return new Response('ok');
};
'''

def test_typescript_functions_and_classes():
    result = parse_javascript(Path("src/Dashboard.tsx"), TS_SAMPLE)
    names = {f["name"] for f in result["functions"]}
    assert "Dashboard" in names
    assert "handler" in names
    class_names = {c["name"] for c in result["classes"]}
    assert "PetStore" in class_names

def test_typescript_dependencies():
    result = parse_javascript(Path("src/Dashboard.tsx"), TS_SAMPLE)
    assert "react" in result["dependencies"]
    assert "./lib/supabase" in result["dependencies"]

def test_typescript_lines_of_code():
    result = parse_javascript(Path("src/Dashboard.tsx"), TS_SAMPLE)
    assert result["lines_of_code"] > 0
```

- [x] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest services/parser/tests/test_javascript.py -v --confcutdir=services/parser/tests
```

Expected: `ModuleNotFoundError`.

- [x] **Step 3: Create `services/parser/javascript.py`**

```python
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
    "method": re.compile(r"(\w+)\s*\(([^)]*)\)\s*\{"),
    "express_route": re.compile(
        r'''(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['"]([^'"]+)['"]'''
    ),
    "middleware_use": re.compile(r"(?:app|router)\.use\s*\(\s*([^)]+)\)"),
    "class_decl": re.compile(r"(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?"),
    "export_default": re.compile(r"export\s+default\s+(?:function\s+)?(\w+)"),
    "export_named": re.compile(r"export\s+\{([^}]+)\}"),
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
        })

    for match in JS_PATTERNS["arrow_function"].finditer(content):
        functions.append({
            "type": "arrow_function",
            "name": match.group(1),
            "signature": f"{match.group(1)}()",
            "async": False,
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
```

- [x] **Step 4: Update `services/parser/main.py`**

Remove `JS_PATTERNS` and `parse_javascript()` from `main.py`. Add:

```python
from services.parser.javascript import parse_javascript
```

Update `parse_file()` to route `javascript` and `typescript` to the JS parser:

```python
if lang in ("javascript", "typescript"):
    ast = parse_javascript(file_path, content)
elif lang == "python":
    ast = parse_python(file_path, content)
else:
    ...
```

- [x] **Step 5: Run tests**

```bash
python3 -m pytest services/parser/tests/test_javascript.py -v --confcutdir=services/parser/tests
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add services/parser/javascript.py services/parser/main.py services/parser/tests/test_javascript.py
git commit -m "feat(parser): add reusable JS/TS/TSX AST extractor with export support"
```

---

### Task 4: Add lightweight static-file AST summaries

**Files:**
- Create: `services/parser/static.py`
- Modify: `services/parser/main.py`
- Test: `services/parser/tests/test_static.py`

- [x] **Step 1: Write failing tests**

Create `services/parser/tests/test_static.py`:

```python
from pathlib import Path
from services.parser.static import parse_static

HTML = '''<!DOCTYPE html>
<html>
  <head><title>DevPet</title></head>
  <body>
    <script src="./app.js"></script>
  </body>
</html>
'''

def test_html_summary():
    result = parse_static(Path("index.html"), "html", HTML)
    assert result["language"] == "html"
    assert "./app.js" in result["dependencies"]
    assert result["lines_of_code"] > 0

def test_json_summary():
    result = parse_static(Path("package.json"), "json", '{"name":"x"}')
    assert result["language"] == "json"
    assert result["dependencies"] == []

def test_markdown_summary():
    result = parse_static(Path("README.md"), "markdown", "# Hello\n\nWorld.")
    assert result["language"] == "markdown"
    assert result["lines_of_code"] == 2
```

- [x] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest services/parser/tests/test_static.py -v --confcutdir=services/parser/tests
```

Expected: `ModuleNotFoundError`.

- [x] **Step 3: Create `services/parser/static.py`**

```python
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
    elif language == "sql":
        tables = SQL_TABLE.findall(content)
    else:
        tables = []

    return {
        "language": language,
        "lines_of_code": loc,
        "functions": [],
        "classes": [],
        "dependencies": list(set(deps)),
        "tables": tables if language == "sql" else [],
    }
```

- [x] **Step 4: Update `services/parser/main.py`**

Add import:

```python
from services.parser.static import parse_static
```

Update the generic else branch in `parse_file()` to use `parse_static()`:

```python
else:
    ast = parse_static(file_path, lang, content)
```

- [x] **Step 5: Run tests**

```bash
python3 -m pytest services/parser/tests/test_static.py -v --confcutdir=services/parser/tests
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add services/parser/static.py services/parser/main.py services/parser/tests/test_static.py
git commit -m "feat(parser): add lightweight AST summaries for static/config files"
```

---

### Task 5: Improve file classification

**Files:**
- Create: `services/parser/classify.py`
- Modify: `services/parser/main.py`
- Test: `services/parser/tests/test_classify.py`

- [x] **Step 1: Write failing classification tests**

Create `services/parser/tests/test_classify.py`:

```python
from pathlib import Path
from services.parser.classify import classify_file

def test_static_files_by_extension():
    assert classify_file(Path("index.html"), "") == "static"
    assert classify_file(Path("styles.css"), "") == "static"
    assert classify_file(Path("package.json"), "") == "config"
    assert classify_file(Path("tsconfig.json"), "") == "config"
    assert classify_file(Path("README.md"), "") == "documentation"
    assert classify_file(Path("schema.sql"), "") == "database"

def test_typescript_components():
    content = 'export function Dashboard() { return <div/>; }'
    assert classify_file(Path("src/components/Dashboard.tsx"), content) == "component"

def test_tests():
    assert classify_file(Path("App.test.tsx"), 'test("x", () => {})') == "test"
```

- [x] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest services/parser/tests/test_classify.py -v --confcutdir=services/parser/tests
```

Expected: `ModuleNotFoundError` or assertion failures.

- [x] **Step 3: Create `services/parser/classify.py`**

```python
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
```

- [x] **Step 4: Update `services/parser/main.py`**

Remove the inline `CLASSIFICATION_PATTERNS` and `classify_file()`. Add:

```python
from services.parser.classify import classify_file
```

- [x] **Step 5: Run tests**

```bash
python3 -m pytest services/parser/tests/test_classify.py -v --confcutdir=services/parser/tests
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add services/parser/classify.py services/parser/main.py services/parser/tests/test_classify.py
git commit -m "feat(parser): improve file classification heuristics"
```

---

### Task 6: Improve dependency graph resolution

**Files:**
- Create: `services/parser/graph.py`
- Modify: `services/parser/main.py`
- Test: `services/parser/tests/test_graph.py`

- [x] **Step 1: Write failing graph tests**

Create `services/parser/tests/test_graph.py`:

```python
from services.parser.models import ParsedFile
from services.parser.graph import build_dependency_graph

def test_relative_import_resolution():
    files = [
        ParsedFile(
            path="/repo/src/App.tsx",
            language="typescript",
            classification="component",
            ast_summary={},
            dependencies=["./lib/db"],
            lines_of_code=10,
        ),
        ParsedFile(
            path="/repo/src/lib/db.ts",
            language="typescript",
            classification="utility",
            ast_summary={},
            dependencies=[],
            lines_of_code=20,
        ),
    ]
    graph = build_dependency_graph(files)
    assert graph["/repo/src/App.tsx"] == ["/repo/src/lib/db.ts"]
```

- [x] **Step 2: Run tests to verify failure**

```bash
python3 -m pytest services/parser/tests/test_graph.py -v --confcutdir=services/parser/tests
```

Expected: `ModuleNotFoundError`.

- [x] **Step 3: Create `services/parser/graph.py`**

```python
from pathlib import Path
from services.parser.models import ParsedFile


EXTENSION_PRIORITY = [".tsx", ".ts", ".jsx", ".js", ".py"]


def build_dependency_graph(files: list[ParsedFile]) -> dict[str, list[str]]:
    path_map = {f.path: f for f in files}
    graph: dict[str, list[str]] = {}

    for f in files:
        local_deps: list[str] = []
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                base = Path(f.path).parent
                candidate = base / dep
                resolved = _resolve_candidate(candidate, path_map)
                if resolved:
                    local_deps.append(resolved)
                elif candidate.is_dir():
                    # index file inside a directory import
                    index_candidate = candidate / "index"
                    resolved = _resolve_candidate(index_candidate, path_map)
                    if resolved:
                        local_deps.append(resolved)
        graph[f.path] = local_deps
    return graph


def _resolve_candidate(candidate: Path, path_map: dict[str, ParsedFile]) -> str | None:
    if candidate.suffix:
        key = str(candidate)
        if key in path_map:
            return key
    else:
        for ext in EXTENSION_PRIORITY:
            key = str(candidate.with_suffix(ext))
            if key in path_map:
                return key
    return None
```

- [x] **Step 4: Update `services/parser/main.py`**

Remove `build_dependency_graph()` from `main.py`. Add:

```python
from services.parser.graph import build_dependency_graph
```

- [x] **Step 5: Run tests**

```bash
python3 -m pytest services/parser/tests/test_graph.py -v --confcutdir=services/parser/tests
```

Expected: PASS.

- [x] **Step 6: Commit**

```bash
git add services/parser/graph.py services/parser/main.py services/parser/tests/test_graph.py
git commit -m "feat(parser): improve dependency graph resolution for directory and extensionless imports"
```

---

### Task 7: Add devpet regression test

**Files:**
- Create: `services/parser/tests/test_devpet_regression.py`
- Create: `test-repo/devpet-samples/` sample files

- [x] **Step 1: Create sample files**

Create a minimal sample set under `test-repo/devpet-samples/`:

- `test-repo/devpet-samples/web-dashboard/src/components/Dashboard.tsx`
- `test-repo/devpet-samples/web-dashboard/src/lib/supabase.ts`
- `test-repo/devpet-samples/web-dashboard/index.html`
- `test-repo/devpet-samples/supabase/schema.sql`
- `test-repo/devpet-samples/README.md`

Copy representative snippets from the actual devpet output into these files.

- [x] **Step 2: Write regression test**

Create `services/parser/tests/test_devpet_regression.py`:

```python
from pathlib import Path
from services.parser.main import parse_file, build_dependency_graph

SAMPLES = Path("test-repo/devpet-samples")


def test_dashboard_typescript_parsed():
    path = SAMPLES / "web-dashboard/src/components/Dashboard.tsx"
    result = parse_file(path)
    assert result is not None
    assert result.language == "typescript"
    assert len(result.ast_summary["functions"]) > 0
    assert "@supabase/supabase-js" in result.dependencies or "./lib/supabase" in result.dependencies


def test_html_static():
    path = SAMPLES / "web-dashboard/index.html"
    result = parse_file(path)
    assert result.language == "html"
    assert result.classification == "static"


def test_sql_database():
    path = SAMPLES / "supabase/schema.sql"
    result = parse_file(path)
    assert result.language == "sql"
    assert result.classification == "database"


def test_dependency_graph_resolves_local_imports():
    paths = [
        SAMPLES / "web-dashboard/src/components/Dashboard.tsx",
        SAMPLES / "web-dashboard/src/lib/supabase.ts",
    ]
    files = [parse_file(p) for p in paths]
    files = [f for f in files if f]
    graph = build_dependency_graph(files)
    dashboard_path = str(paths[0])
    supabase_path = str(paths[1])
    assert supabase_path in graph.get(dashboard_path, [])
```

- [x] **Step 3: Run tests**

```bash
python3 -m pytest services/parser/tests/test_devpet_regression.py -v --confcutdir=services/parser/tests
```

Expected: PASS after Tasks 1-6 are complete.

- [x] **Step 4: Commit**

```bash
git add test-repo/devpet-samples services/parser/tests/test_devpet_regression.py
git commit -m "test(parser): add devpet regression samples and assertions"
```

---

### Task 8: Run full parser test suite and update docs

**Files:**
- Modify: `docs/superpowers/specs/2026-06-14-repo-intelligence-ui-design.md` (if needed, not required)
- Modify: `README.md` (optional)

- [x] **Step 1: Run all parser tests**

```bash
python3 -m pytest services/parser/tests -v --confcutdir=services/parser/tests
```

Expected: all tests pass.

- [x] **Step 2: Run existing project tests**

```bash
python3 -m pytest scripts/tests/test_utilities.py -v --confcutdir=scripts/tests
```

Expected: PASS.

- [x] **Step 3: Verify parser service still starts**

```bash
cd services/parser
python3 -m py_compile main.py
```

Expected: no syntax errors.

- [x] **Step 4: Commit any doc updates**

If the README parser section is updated, commit:

```bash
git add README.md
git commit -m "docs: document parser capabilities and supported file types"
```

---

## Self-Review Checklist

- [x] Spec coverage: every anomaly listed in the overview has a corresponding task.
- [x] No placeholders: each task includes exact file paths, code snippets, and commands.
- [x] Type consistency: `ParsedFile`/`ParsedRepo` models are reused across modules.
- [x] Test-driven: each task starts with a failing test.
- [x] Incremental commits: every task ends with a commit.
- [x] Gaps: none identified.
