from pydantic import BaseModel
from typing import Any


class ParsedFile(BaseModel):
    path: str
    language: str
    classification: str
    ast_summary: dict[str, Any]
    dependencies: list[str]
    lines_of_code: int


class ParsedRepo(BaseModel):
    repo_id: str
    commit: str
    files: list[ParsedFile]
    dependency_graph: dict[str, list[str]]
