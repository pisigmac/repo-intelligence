from pathlib import Path
from services.parser.models import ParsedFile


EXTENSION_PRIORITY = [".tsx", ".ts", ".jsx", ".js", ".py"]


def build_dependency_graph(files: list[ParsedFile]) -> dict[str, list[str]]:
    path_map = {f.path: f for f in files}
    graph: dict[str, list[str]] = {}

    for f in files:
        local_deps: list[str] = []
        for dep in f.dependencies:
            if dep.startswith(".") or dep.startswith("/"):
                base = Path(f.path).parent
                candidate = base / dep
                resolved = _resolve_candidate(candidate, path_map)
                if resolved:
                    local_deps.append(resolved)
                elif candidate.is_dir():
                    index_candidate = candidate / "index"
                    resolved = _resolve_candidate(index_candidate, path_map)
                    if resolved:
                        local_deps.append(resolved)
        graph[f.path] = local_deps
    return graph


def _resolve_candidate(candidate: Path, path_map: dict[str, ParsedFile]) -> str | None:
    if candidate.suffix:
        key = str(candidate)
        if key in path_map:
            return key
    else:
        for ext in EXTENSION_PRIORITY:
            key = str(candidate.with_suffix(ext))
            if key in path_map:
                return key
    return None
