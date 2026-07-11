> I'm using the writing-plans skill to create the implementation plan.

# Parser Fixes Phase 2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Fix the language-detection, AST-extraction, dependency-resolution, and classification gaps observed when running the parser against `expressjs/express`, `nestjs/nest`, and `langchain-ai/langchain`.

**Architecture:** Extend the regex-based parser modules introduced in Phase 1 with broader extension/filename maps, anonymous-function and decorator regexes for JavaScript/TypeScript, smarter directory-import resolution in the graph builder, a Python package-to-file index for monorepo imports, and a re-export-safe classification rule.

**Tech Stack:** Python 3.11, Pydantic, pytest, regex.

---

## Issues Addressed

1. `unknown` language for common dotfiles and modern extensions (`.mjs`, `.cjs`, `.gql`, `.graphql`, `.pyi`, `.svg`, `.lock`, `.txt`, `.snap`, `.ambr`, `.ipynb`, `.rst`, `.svelte`, `.vue`, `.cs`, `.cpp`/`.cc`/`.hpp`/`.h`, plus dotfiles like `.eslintignore`, `.editorconfig`, `CODEOWNERS`, `CITATION.cff`, `LICENSE`).
2. Anonymous callbacks in route definitions are not extracted as functions.
3. TypeScript decorators (`@Controller`, `@Get`, `@Post`, etc.) are ignored.
4. Directory imports (`".."`, `"./"`, `"./app.module"`) are flagged as unresolved even when a valid `index.*` exists, because the reporting script uses a naive stem match.
5. Python monorepo absolute imports (`from langchain_core.prompts ...`) produce no local graph edges.
6. `__init__.py` re-export files are misclassified as `middleware`/`controller`.

---

## File Structure

| File | Responsibility |
|------|---------------|
| `services/parser/language.py` | Extension and filename to language mapping. |
| `services/parser/javascript.py` | JS/TS AST extraction, including anonymous functions and decorators. |
| `services/parser/graph.py` | Dependency resolution: relative directory imports and Python package imports. |
| `services/parser/classify.py` | File classification heuristics, including `__init__.py` re-exports. |
| `services/parser/main.py` | Wire optional `repo_root` into `build_dependency_graph`. |
| `scripts/test_complex_repos.py` | Better unresolved-import detection using the resolver. |
| `services/parser/tests/test_language.py` | Regression tests for language detection. |
| `services/parser/tests/test_javascript.py` | Regression tests for anonymous functions and decorators. |
| `services/parser/tests/test_graph.py` | Regression tests for directory imports and Python package resolution. |
| `services/parser/tests/test_classify.py` | Regression tests for `__init__.py` classification. |

---

### Task 1: Expand language detection for dotfiles and modern extensions

**Files:**
- Modify: `services/parser/language.py`
- Test: `services/parser/tests/test_language.py`

- [x] **Step 1: Write the failing test**

Append to `services/parser/tests/test_language.py`:

```python
def test_modern_extensions():
    assert detect_language(Path("src/utils.mjs")) == "javascript"
    assert detect_language(Path("src/legacy.cjs")) == "javascript"
    assert detect_language(Path("schema.gql")) == "graphql"
    assert detect_language(Path("api.graphql")) == "graphql"
    assert detect_language(Path("types.pyi")) == "python"
    assert detect_language(Path("logo.svg")) == "svg"
    assert detect_language(Path("uv.lock")) == "lockfile"
    assert detect_language(Path("requirements.txt")) == "text"
    assert detect_language(Path("test.ambr")) == "snapshot"
    assert detect_language(Path("notebook.ipynb")) == "json"
    assert detect_language(Path("README.rst")) == "markdown"
    assert detect_language(Path("App.svelte")) == "svelte"
    assert detect_language(Path("App.vue")) == "vue"
    assert detect_language(Path("Program.cs")) == "csharp"
    assert detect_language(Path("main.cpp")) == "cpp"


def test_common_dotfiles_and_filenames():
    assert detect_language(Path(".eslintignore")) == "gitignore"
    assert detect_language(Path(".npmignore")) == "gitignore"
    assert detect_language(Path(".prettierignore")) == "gitignore"
    assert detect_language(Path(".dockerignore")) == "gitignore"
    assert detect_language(Path(".editorconfig")) == "config"
    assert detect_language(Path(".gitattributes")) == "config"
    assert detect_language(Path(".prettierrc")) == "config"
    assert detect_language(Path(".eslintrc")) == "config"
    assert detect_language(Path(".babelrc")) == "config"
    assert detect_language(Path(".npmrc")) == "config"
    assert detect_language(Path("CODEOWNERS")) == "config"
    assert detect_language(Path("CITATION.cff")) == "citation"
    assert detect_language(Path("LICENSE")) == "documentation"
```

- [x] **Step 2: Run test to verify it fails**

```bash
cd /home/oh20210736-ud/Documents/Kimi_projects/In_progress/git/repo-intelligence
.venv/bin/python -m pytest services/parser/tests/test_language.py -v --confcutdir=services/parser/tests
```

Expected: assertion failures for the new extensions/filenames.

- [x] **Step 3: Update `services/parser/language.py`**

Replace `EXTENSION_MAP` and `FILENAME_MAP` with:

```python
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
```

- [x] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest services/parser/tests/test_language.py -v --confcutdir=services/parser/tests
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add services/parser/language.py services/parser/tests/test_language.py
git commit -m "feat(parser): expand language detection for dotfiles and modern extensions"
```

---

### Task 2: Extract anonymous function expressions

**Files:**
- Modify: `services/parser/javascript.py`
- Test: `services/parser/tests/test_javascript.py`

- [x] **Step 1: Write the failing test**

Append to `services/parser/tests/test_javascript.py`:

```python
ANONYMOUS_CALLBACK_SAMPLE = '''
const express = require('express');
const app = express();

app.get('/', function (req, res) {
  res.send('hello');
});

app.post('/json', (req, res) => {
  res.json({ ok: true });
});
'''


def test_anonymous_functions_and_arrow_callbacks():
    result = parse_javascript(Path("routes/index.js"), ANONYMOUS_CALLBACK_SAMPLE)
    anon_types = {f["type"] for f in result["functions"]}
    assert "anonymous_function" in anon_types
    assert "arrow_function" in anon_types
```

- [x] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest services/parser/tests/test_javascript.py::test_anonymous_functions_and_arrow_callbacks -v --confcutdir=services/parser/tests
```

Expected: assertion failure — `anonymous_function` not found.

- [x] **Step 3: Update `services/parser/javascript.py`**

Add to `JS_PATTERNS`:

```python
    "anonymous_function": re.compile(r"function\s*\(([^)]*)\)\s*\{"),
    "arrow_callback": re.compile(r"\(([^)]*)\)\s*=>\s*\{"),
```

After the existing `for match in JS_PATTERNS["function_decl"].finditer(content)` block, add:

```python
    for match in JS_PATTERNS["anonymous_function"].finditer(content):
        functions.append({
            "type": "anonymous_function",
            "name": None,
            "signature": f"({match.group(1)})",
            "async": False,
        })

    for match in JS_PATTERNS["arrow_callback"].finditer(content):
        functions.append({
            "type": "arrow_function",
            "name": None,
            "signature": f"({match.group(1)})",
            "async": False,
        })
```

- [x] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest services/parser/tests/test_javascript.py -v --confcutdir=services/parser/tests
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add services/parser/javascript.py services/parser/tests/test_javascript.py
git commit -m "feat(parser): extract anonymous functions and arrow callbacks"
```

---

### Task 3: Extract TypeScript decorators

**Files:**
- Modify: `services/parser/javascript.py`
- Test: `services/parser/tests/test_javascript.py`

- [x] **Step 1: Write the failing test**

Append to `services/parser/tests/test_javascript.py`:

```python
DECORATOR_SAMPLE = '''
import { Controller, Get, Post, Body } from '@nestjs/common';

@Controller('cats')
export class CatsController {
  @Get()
  findAll(): string {
    return 'This action returns all cats';
  }

  @Post()
  create(@Body() createCatDto: CreateCatDto) {
    return 'This action adds a new cat';
  }
}
'''


def test_typescript_class_decorators():
    result = parse_javascript(Path("cats.controller.ts"), DECORATOR_SAMPLE)
    classes = result["classes"]
    assert len(classes) == 1
    assert classes[0]["name"] == "CatsController"
    assert "Controller" in classes[0].get("decorators", [])


def test_typescript_method_decorators():
    result = parse_javascript(Path("cats.controller.ts"), DECORATOR_SAMPLE)
    method_decorators = set()
    for f in result["functions"]:
        method_decorators.update(f.get("decorators", []))
    assert "Get" in method_decorators
    assert "Post" in method_decorators
```

- [x] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest services/parser/tests/test_javascript.py::test_typescript_class_decorators services/parser/tests/test_javascript.py::test_typescript_method_decorators -v --confcutdir=services/parser/tests
```

Expected: `KeyError` or assertion failure on decorators.

- [x] **Step 3: Update `services/parser/javascript.py`**

Add to `JS_PATTERNS`:

```python
    "decorator": re.compile(r"@(\w+)(?:\s*\(([^)]*)\))?"),
```

Add a helper function before `parse_javascript`:

```python
def _decorators_before(content: str, pos: int) -> list[str]:
    """Collect decorators immediately before a declaration at `pos`."""
    prefix = content[:pos]
    lines = prefix.splitlines()
    decorators: list[str] = []
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            break
        match = JS_PATTERNS["decorator"].match(stripped)
        if match:
            decorators.append(match.group(1))
        else:
            break
    return list(reversed(decorators))
```

In `parse_javascript`, when building `functions`, append decorators:

```python
    for match in JS_PATTERNS["function_decl"].finditer(content):
        prefix = content[max(0, match.start() - 20):match.start()]
        functions.append({
            "type": "function",
            "name": match.group(1),
            "signature": f"{match.group(1)}({match.group(2)})",
            "async": "async" in prefix,
            "decorators": _decorators_before(content, match.start()),
        })
```

Also update the anonymous and arrow blocks to include `"decorators": _decorators_before(content, match.start())`.

When building `classes`, add decorators:

```python
    classes = []
    for match in JS_PATTERNS["class_decl"].finditer(content):
        classes.append({
            "name": match.group(1),
            "extends": match.group(2),
            "decorators": _decorators_before(content, match.start()),
        })
```

- [x] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest services/parser/tests/test_javascript.py -v --confcutdir=services/parser/tests
```

Expected: all tests pass.

- [x] **Step 5: Commit**

```bash
git add services/parser/javascript.py services/parser/tests/test_javascript.py
git commit -m "feat(parser): extract TypeScript class and method decorators"
```

---

### Task 4: Improve directory-import resolution and reporting

**Files:**
- Modify: `services/parser/graph.py`, `scripts/test_complex_repos.py`
- Test: `services/parser/tests/test_graph.py`

- [x] **Step 1: Write the failing test**

Append to `services/parser/tests/test_graph.py`:

```python
def test_directory_import_to_index():
    files = [
        ParsedFile(
            path="/repo/src/app.js",
            language="javascript",
            classification="route",
            ast_summary={},
            dependencies=["."],
            lines_of_code=10,
        ),
        ParsedFile(
            path="/repo/src/index.js",
            language="javascript",
            classification="utility",
            ast_summary={},
            dependencies=[],
            lines_of_code=20,
        ),
    ]
    graph = build_dependency_graph(files)
    assert graph["/repo/src/app.js"] == ["/repo/src/index.js"]


def test_parent_directory_import_to_root_index():
    files = [
        ParsedFile(
            path="/repo/test/foo.js",
            language="javascript",
            classification="test",
            ast_summary={},
            dependencies=[".."],
            lines_of_code=10,
        ),
        ParsedFile(
            path="/repo/index.js",
            language="javascript",
            classification="utility",
            ast_summary={},
            dependencies=[],
            lines_of_code=20,
        ),
    ]
    graph = build_dependency_graph(files)
    assert graph["/repo/test/foo.js"] == ["/repo/index.js"]


def test_named_directory_import_to_index():
    files = [
        ParsedFile(
            path="/repo/src/app.js",
            language="javascript",
            classification="route",
            ast_summary={},
            dependencies=["./lib"],
            lines_of_code=10,
        ),
        ParsedFile(
            path="/repo/src/lib/index.js",
            language="javascript",
            classification="utility",
            ast_summary={},
            dependencies=[],
            lines_of_code=20,
        ),
    ]
    graph = build_dependency_graph(files)
    assert graph["/repo/src/app.js"] == ["/repo/src/lib/index.js"]
```

- [x] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest services/parser/tests/test_graph.py -v --confcutdir=services/parser/tests
```

Expected: the new directory-import tests may already pass; if not, fix in Step 3.

- [x] **Step 3: Update `services/parser/graph.py` if needed**

Current `_resolve_candidate` already tries `candidate / "index"` for directory imports. If tests fail, adjust `_resolve_candidate` to use `os.path.normpath` and ensure directory candidate detection works for `..` / `.`:

```python
def _resolve_candidate(candidate: Path, path_map: dict[str, ParsedFile]) -> str | None:
    candidate = Path(os.path.normpath(candidate))
    if candidate.suffix:
        key = str(candidate)
        if key in path_map:
            return key
    else:
        for ext in EXTENSION_PRIORITY:
            key = str(candidate.with_suffix(ext))
            if key in path_map:
                return key
        # Directory import: try index file inside the directory
        index_candidate = candidate / "index"
        for ext in EXTENSION_PRIORITY:
            key = str(index_candidate.with_suffix(ext))
            if key in path_map:
                return key
    return None
```

Then simplify `build_dependency_graph` to rely on `_resolve_candidate` for both file and directory candidates:

```python
    for f in files:
        local_deps: list[str] = []
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                base = Path(f.path).parent
                candidate = Path(os.path.normpath(base / dep))
                resolved = _resolve_candidate(candidate, path_map)
                if resolved:
                    local_deps.append(resolved)
        graph[f.path] = local_deps
    return graph
```

- [x] **Step 4: Update `scripts/test_complex_repos.py`**

Replace the unresolved-local block in `analyze()` with:

```python
    def _is_resolved(path: str, dep: str) -> bool:
        if not (dep.startswith(".") or dep.startswith("/")):
            return True
        base = Path(path).parent
        candidate = Path(os.path.normpath(base / dep))
        if str(candidate) in path_map:
            return True
        for ext in [".tsx", ".ts", ".jsx", ".js", ".py"]:
            if str(candidate.with_suffix(ext)) in path_map:
                return True
        for ext in [".tsx", ".ts", ".jsx", ".js", ".py"]:
            if str((candidate / "index").with_suffix(ext)) in path_map:
                return True
        return False

    unresolved_local = []
    for f in parsed:
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                if not _is_resolved(f.path, dep):
                    unresolved_local.append((f.path, dep))
```

- [x] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest services/parser/tests/test_graph.py -v --confcutdir=services/parser/tests
```

Expected: all graph tests pass.

- [x] **Step 6: Commit**

```bash
git add services/parser/graph.py services/parser/tests/test_graph.py scripts/test_complex_repos.py
git commit -m "fix(parser): resolve directory imports and improve unresolved-import detection"
```

---

### Task 5: Resolve Python monorepo package imports

**Files:**
- Modify: `services/parser/graph.py`, `services/parser/main.py`
- Test: `services/parser/tests/test_graph.py`

- [x] **Step 1: Write the failing test**

Append to `services/parser/tests/test_graph.py`:

```python
def test_python_package_import_resolution():
    files = [
        ParsedFile(
            path="/repo/libs/core/langchain_core/prompts.py",
            language="python",
            classification="utility",
            ast_summary={},
            dependencies=[],
            lines_of_code=50,
        ),
        ParsedFile(
            path="/repo/libs/langchain/langchain/chat.py",
            language="python",
            classification="utility",
            ast_summary={},
            dependencies=["langchain_core.prompts"],
            lines_of_code=20,
        ),
    ]
    graph = build_dependency_graph(files, repo_root="/repo")
    assert graph["/repo/libs/langchain/langchain/chat.py"] == ["/repo/libs/core/langchain_core/prompts.py"]
```

- [x] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest services/parser/tests/test_graph.py::test_python_package_import_resolution -v --confcutdir=services/parser/tests
```

Expected: `TypeError` or empty graph edge.

- [x] **Step 3: Update `services/parser/graph.py`**

Add a helper to build a Python package index:

```python
def _build_python_package_index(files: list[ParsedFile], repo_root: str) -> dict[str, str]:
    root = Path(repo_root).resolve()
    index: dict[str, str] = {}
    for f in files:
        if f.language != "python":
            continue
        path = Path(f.path).resolve()
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            module_parts = parts[:-1]
        else:
            module_parts = parts[:-1] + [Path(parts[-1]).stem]
        dotted = ".".join(module_parts)
        if dotted:
            index[dotted] = f.path
    return index
```

Update `build_dependency_graph` signature and logic:

```python
def build_dependency_graph(
    files: list[ParsedFile],
    repo_root: str | None = None,
) -> dict[str, list[str]]:
    path_map = {f.path: f for f in files}
    py_index = _build_python_package_index(files, repo_root) if repo_root else {}
    graph: dict[str, list[str]] = {}

    for f in files:
        local_deps: list[str] = []
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                base = Path(f.path).parent
                candidate = Path(os.path.normpath(base / dep))
                resolved = _resolve_candidate(candidate, path_map)
                if resolved:
                    local_deps.append(resolved)
            elif f.language == "python" and "." in dep:
                # Try to resolve absolute Python package imports in a monorepo
                parts = dep.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    if prefix in py_index:
                        local_deps.append(py_index[prefix])
                        break
        graph[f.path] = local_deps
    return graph
```

- [x] **Step 4: Update `services/parser/main.py`**

In `handle_repo_ingested`, change:

```python
        graph = build_dependency_graph(parsed_files)
```

To:

```python
        graph = build_dependency_graph(parsed_files, repo_root=storage_path)
```

- [x] **Step 5: Run tests**

```bash
.venv/bin/python -m pytest services/parser/tests/test_graph.py -v --confcutdir=services/parser/tests
```

Expected: all graph tests pass.

- [x] **Step 6: Commit**

```bash
git add services/parser/graph.py services/parser/main.py services/parser/tests/test_graph.py
git commit -m "feat(parser): resolve Python monorepo package imports in dependency graph"
```

---

### Task 6: Fix `__init__.py` re-export classification

**Files:**
- Modify: `services/parser/classify.py`
- Test: `services/parser/tests/test_classify.py`

- [x] **Step 1: Write the failing test**

Append to `services/parser/tests/test_classify.py`:

```python
def test_init_reexport_utility():
    content = '''from .cats.controller import CatsController
from .cats.service import CatsService

__all__ = ["CatsController", "CatsService"]
'''
    assert classify_file(Path("src/cats/__init__.py"), content) == "utility"
```

- [x] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest services/parser/tests/test_classify.py::test_init_reexport_utility -v --confcutdir=services/parser/tests
```

Expected: classification is not `utility`.

- [x] **Step 3: Update `services/parser/classify.py`**

Add a helper function before `classify_file`:

```python
def _has_definitions(content: str) -> bool:
    """Return True if the content declares functions or classes."""
    return bool(
        re.search(r"(?:async\s+)?def\s+\w+\s*\(", content)
        or re.search(r"class\s+\w+", content)
        or re.search(r"(?:async\s+)?function\s+\w+\s*\(", content)
    )
```

In `classify_file`, after the filename/extension checks and before content pattern scoring, add:

```python
    if lower_name == "__init__.py" and not _has_definitions(content):
        return "utility"
```

- [x] **Step 4: Run test to verify it passes**

```bash
.venv/bin/python -m pytest services/parser/tests/test_classify.py -v --confcutdir=services/parser/tests
```

Expected: all classification tests pass.

- [x] **Step 5: Commit**

```bash
git add services/parser/classify.py services/parser/tests/test_classify.py
git commit -m "fix(parser): classify re-export-only __init__.py files as utility"
```

---

### Task 7: Regenerate complex-repo report

**Files:**
- Modify: `scripts/test_complex_repos.py` (already updated in Task 4)
- Create: `complex-repo-parser-results.md` (overwritten)

- [x] **Step 1: Run the reporting script**

```bash
cd /home/oh20210736-ud/Documents/Kimi_projects/In_progress/git/repo-intelligence
.venv/bin/python scripts/test_complex_repos.py
```

- [x] **Step 2: Inspect the new report**

```bash
wc -l complex-repo-parser-results.md
head -50 complex-repo-parser-results.md
```

- [x] **Step 3: Commit**

```bash
git add scripts/test_complex_repos.py complex-repo-parser-results.md
git commit -m "chore(parser): regenerate complex-repo report with improved resolver"
```

---

### Task 8: Run full parser test suite

**Files:**
- All parser tests

- [x] **Step 1: Run parser tests and utility tests**

```bash
.venv/bin/python -m pytest services/parser/tests scripts/tests/test_utilities.py -v --confcutdir=services/parser/tests
```

Expected: all tests pass.

- [x] **Step 2: Verify parser service compiles**

```bash
.venv/bin/python -m py_compile services/parser/main.py
```

Expected: no output (success).

- [x] **Step 3: Commit if any final fixes are needed**

Only commit if tests required additional changes.

---

## Self-Review Checklist

- [x] Spec coverage: each of the six identified issues has a dedicated task.
- [x] No placeholders: every step contains exact file paths, code, and commands.
- [x] Type consistency: `ParsedFile`/`build_dependency_graph` signatures remain compatible (new `repo_root` is optional).
- [x] Test-driven: each task starts with a failing test.
- [x] Incremental commits: every task ends with a commit.
- [x] Gaps: none identified.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-15-parser-fixes-phase2.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach would you like?
