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
