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
