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
