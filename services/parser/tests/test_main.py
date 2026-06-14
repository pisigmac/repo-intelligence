"""Tests for parser service."""
import pytest
from pathlib import Path
from services.parser.main import parse_file, build_dependency_graph, ParsedFile


def test_parse_javascript():
    content = """
const express = require('express');
const auth = require('./middleware/auth');

function login(req, res) {
    return res.json({token: 'abc'});
}

router.post('/login', login);
module.exports = router;
"""
    # Write temp file
    import tempfile, os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
        f.write(content)
        path = Path(f.name)

    try:
        result = parse_file(path)
        assert result is not None
        assert result.language == "javascript"
        assert result.classification in ["route", "utility"]
        assert len(result.ast_summary["functions"]) >= 1
        assert any(d == "express" for d in result.dependencies)
    finally:
        os.unlink(path)


def test_build_dependency_graph():
    files = [
        ParsedFile(
            path="/app/routes/auth.js",
            language="javascript",
            classification="route",
            ast_summary={},
            dependencies=["../middleware/auth", "express"],
            lines_of_code=10,
        ),
        ParsedFile(
            path="/app/middleware/auth.js",
            language="javascript",
            classification="middleware",
            ast_summary={},
            dependencies=["jsonwebtoken"],
            lines_of_code=5,
        ),
    ]
    graph = build_dependency_graph(files)
    assert "/app/routes/auth.js" in graph
    assert any("middleware" in dep for dep in graph["/app/routes/auth.js"])
