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
