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


def test_init_reexport_utility():
    content = '''from .cats.controller import CatsController
from .cats.service import CatsService

__all__ = ["CatsController", "CatsService"]
'''
    assert classify_file(Path("src/cats/__init__.py"), content) == "utility"
