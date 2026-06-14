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
