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
