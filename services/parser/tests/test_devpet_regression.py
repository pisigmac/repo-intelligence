from pathlib import Path
from services.parser.main import parse_file, build_dependency_graph

SAMPLES = Path("services/parser/tests/fixtures/devpet-samples")


def test_dashboard_typescript_parsed():
    path = SAMPLES / "web-dashboard/src/components/Dashboard.tsx"
    result = parse_file(path)
    assert result is not None
    assert result.language == "typescript"
    assert len(result.ast_summary["functions"]) > 0
    assert "@supabase/supabase-js" in result.dependencies or "../lib/supabase" in result.dependencies


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
