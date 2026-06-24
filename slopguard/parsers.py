"""
parsers.py — find dependency manifests in a project and pull out clean
package names (no version specifiers, no extras, no junk).
"""
from __future__ import annotations
import json
import re
from pathlib import Path

try:
    import tomllib  # py3.11+
except ImportError:
    tomllib = None


# Matches: requests==2.31.0 / requests>=2.0 / requests[security] / requests ; python_version<"3.8"
_REQ_LINE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def parse_requirements_txt(path: Path) -> list[str]:
    names = []
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        m = _REQ_LINE.match(line)
        if m:
            names.append(m.group(1))
    return names


def parse_pyproject_toml(path: Path) -> list[str]:
    if tomllib is None:
        return []
    data = tomllib.loads(path.read_text(errors="ignore"))
    names = []

    # PEP 621 standard deps
    for dep in data.get("project", {}).get("dependencies", []):
        m = _REQ_LINE.match(dep)
        if m:
            names.append(m.group(1))

    # Poetry-style deps
    poetry_deps = (
        data.get("tool", {}).get("poetry", {}).get("dependencies", {})
    )
    for name in poetry_deps:
        if name.lower() != "python":
            names.append(name)

    return names


def parse_package_json(path: Path) -> list[str]:
    data = json.loads(path.read_text(errors="ignore"))
    names = []
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        for name in data.get(key, {}) or {}:
            names.append(name)
    return names


def find_manifests(root: Path) -> dict[str, list[Path]]:
    """Walk the project and bucket manifest files by ecosystem, skipping
    the usual noise directories so this stays fast on real repos."""
    skip_dirs = {"node_modules", ".git", "venv", ".venv", "dist", "build", "__pycache__"}
    found = {"pypi": [], "npm": []}

    for path in root.rglob("*"):
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.name == "requirements.txt":
            found["pypi"].append(path)
        elif path.name == "pyproject.toml":
            found["pypi"].append(path)
        elif path.name == "package.json":
            found["npm"].append(path)

    return found


def collect_packages(root: Path) -> list[tuple[str, str, str]]:
    """Returns list of (package_name, ecosystem, source_file) ready for checker.check_all"""
    manifests = find_manifests(root)
    packages: list[tuple[str, str, str]] = []

    for path in manifests["pypi"]:
        rel = str(path.relative_to(root))
        if path.name == "requirements.txt":
            for name in parse_requirements_txt(path):
                packages.append((name, "pypi", rel))
        elif path.name == "pyproject.toml":
            for name in parse_pyproject_toml(path):
                packages.append((name, "pypi", rel))

    for path in manifests["npm"]:
        rel = str(path.relative_to(root))
        for name in parse_package_json(path):
            packages.append((name, "npm", rel))

    # de-dupe while keeping the first source file we saw each name in
    seen = {}
    for name, eco, src in packages:
        key = (name.lower(), eco)
        if key not in seen:
            seen[key] = (name, eco, src)
    return list(seen.values())
