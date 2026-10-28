"""Guard the dependency direction of the domain-first modular monolith.

These checks intentionally enforce only boundaries already required by the
architecture: domain code cannot depend on outer layers, and application
use-cases cannot depend on the HTTP/API delivery layer.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = REPOSITORY_ROOT / "app" / "application"
DOMAIN_ROOT = REPOSITORY_ROOT / "app" / "domain"


def _resolve_imported_module(path: Path, node: ast.Import | ast.ImportFrom) -> set[str]:
    """Return absolute module names imported by an AST import statement."""
    if isinstance(node, ast.Import):
        return {alias.name for alias in node.names}

    if node.level == 0:
        base_parts = node.module.split(".") if node.module else []
    else:
        relative_path = path.relative_to(REPOSITORY_ROOT / "app")
        package_parts = ["app", *relative_path.parent.parts]
        keep_parts = max(1, len(package_parts) - node.level + 1)
        base_parts = package_parts[:keep_parts]
        if node.module:
            base_parts.extend(node.module.split("."))

    if not base_parts:
        return set()

    base_module = ".".join(base_parts)
    imported_modules = {base_module}
    for alias in node.names:
        if alias.name != "*":
            imported_modules.add(f"{base_module}.{alias.name}")
    return imported_modules


def _layer_imports(root: Path) -> list[tuple[str, str]]:
    """Collect imports from application modules into a forbidden outer layer."""
    findings: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise AssertionError(f"Could not inspect Python module {path}: {error}") from error

        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            for imported_module in _resolve_imported_module(path, node):
                findings.append((path.relative_to(REPOSITORY_ROOT).as_posix(), imported_module))
    return findings


def test_domain_does_not_depend_on_outer_layers() -> None:
    forbidden_prefixes = ("app.api", "app.application", "app.infrastructure")
    violations = [
        (path, imported)
        for path, imported in _layer_imports(DOMAIN_ROOT)
        if any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes)
    ]

    assert not violations, (
        "Domain modules must remain independent of API, application, and infrastructure. "
        f"Forbidden imports: {violations}"
    )


def test_application_does_not_depend_on_api_delivery_layer() -> None:
    forbidden_prefix = "app.api"
    violations = [
        (path, imported)
        for path, imported in _layer_imports(APPLICATION_ROOT)
        if imported == forbidden_prefix or imported.startswith(f"{forbidden_prefix}.")
    ]

    assert not violations, (
        "Application use-cases must not depend on the API/HTTP delivery layer. "
        f"Forbidden imports: {violations}"
    )



def test_import_resolver_detects_forbidden_alias_modules_from_app_package() -> None:
    path = REPOSITORY_ROOT / "app" / "domain" / "example.py"
    node = ast.parse("from app import api, application").body[0]

    imported = _resolve_imported_module(path, node)

    assert "app.api" in imported
    assert "app.application" in imported


def test_import_resolver_handles_relative_from_imports() -> None:
    path = REPOSITORY_ROOT / "app" / "domain" / "example.py"
    node = ast.parse("from . import model").body[0]

    imported = _resolve_imported_module(path, node)

    assert "app.domain.model" in imported
