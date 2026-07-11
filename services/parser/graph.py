import os
from pathlib import Path
from services.parser.models import ParsedFile


EXTENSION_PRIORITY = [".tsx", ".ts", ".jsx", ".js", ".py"]


def _build_python_package_index(files: list[ParsedFile], repo_root: str) -> dict[str, str]:
    root = Path(repo_root).resolve()
    index: dict[str, str] = {}
    for f in files:
        if f.language != "python":
            continue
        path = Path(f.path).resolve()
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = list(rel.parts)
        if parts[-1] == "__init__.py":
            module_parts = parts[:-1]
        else:
            module_parts = parts[:-1] + [Path(parts[-1]).stem]
        for i in range(len(module_parts)):
            dotted = ".".join(module_parts[i:])
            if dotted:
                index[dotted] = f.path
    return index


def build_dependency_graph(
    files: list[ParsedFile],
    repo_root: str | None = None,
) -> dict[str, list[str]]:
    path_map = {f.path: f for f in files}
    py_index = _build_python_package_index(files, repo_root) if repo_root else {}
    graph: dict[str, list[str]] = {}

    for f in files:
        local_deps: list[str] = []
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                base = Path(f.path).parent
                candidate = Path(os.path.normpath(base / dep))
                resolved = _resolve_candidate(candidate, path_map)
                if resolved:
                    local_deps.append(resolved)
            elif f.language == "python" and "." in dep:
                # Try to resolve absolute Python package imports in a monorepo
                parts = dep.split(".")
                for i in range(len(parts), 0, -1):
                    prefix = ".".join(parts[:i])
                    if prefix in py_index:
                        local_deps.append(py_index[prefix])
                        break
        graph[f.path] = local_deps
    return graph


def _resolve_candidate(candidate: Path, path_map: dict[str, ParsedFile]) -> str | None:
    candidate = Path(os.path.normpath(candidate))
    if candidate.suffix:
        key = str(candidate)
        if key in path_map:
            return key
    else:
        for ext in EXTENSION_PRIORITY:
            key = str(candidate.with_suffix(ext))
            if key in path_map:
                return key
        # Directory import: try index file inside the directory
        index_candidate = candidate / "index"
        for ext in EXTENSION_PRIORITY:
            key = str(index_candidate.with_suffix(ext))
            if key in path_map:
                return key
    return None
