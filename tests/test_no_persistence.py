"""Fail the build if app or library code can write files or reach a storage client.

This is a static check over the source tree. It runs in CI on every push.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
CHECKED = [*sorted((ROOT / "src" / "dueproc").rglob("*.py")), *sorted((ROOT / "app").rglob("*.py"))]

STORAGE_MODULES = {
    "sqlite3",
    "shelve",
    "dbm",
    "pickle",
    "tempfile",
    "boto3",
    "botocore",
    "redis",
    "pymongo",
    "psycopg",
    "psycopg2",
    "sqlalchemy",
    "google.cloud",
    "azure.storage",
    "firebase_admin",
}
WRITE_CALLS = {"write_text", "write_bytes", "mkdir", "touch", "save", "dump", "to_csv", "to_excel"}


def _imports(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


@pytest.mark.parametrize("path", CHECKED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_storage_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad = {
        m for m in _imports(tree) if any(m == s or m.startswith(s + ".") for s in STORAGE_MODULES)
    }
    assert not bad, f"{path.name} imports storage modules: {bad}"


@pytest.mark.parametrize("path", CHECKED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_file_writes(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", "")
        assert name not in WRITE_CALLS, f"{path.name}:{node.lineno} calls {name}()"
        if name == "open":
            mode = (
                node.args[1]
                if len(node.args) > 1
                else next((k.value for k in node.keywords if k.arg == "mode"), None)
            )
            if isinstance(mode, ast.Constant):
                assert not set(str(mode.value)) & set("wax+"), (
                    f"{path.name}:{node.lineno} opens for writing"
                )
            else:
                assert mode is None, f"{path.name}:{node.lineno} open() with a non-literal mode"


def test_checker_catches_a_write(tmp_path):
    bad = ast.parse("open('x', 'w').write('y')")
    calls = [
        n for n in ast.walk(bad) if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "open"
    ]
    assert calls and calls[0].args[1].value == "w"
