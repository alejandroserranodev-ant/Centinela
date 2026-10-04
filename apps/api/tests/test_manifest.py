import ast
import re
import sys
import tomllib
from importlib.metadata import packages_distributions
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def imported_modules() -> set[str]:
    modules = set()
    for source in (PACKAGE / "src" / "centinela_api").rglob("*.py"):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.Import):
                modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                modules.add(node.module.split(".")[0])
    return modules - set(sys.stdlib_module_names) - {"centinela_api"}


def test_every_third_party_import_of_the_package_is_a_declared_dependency():
    manifest = tomllib.loads((PACKAGE / "pyproject.toml").read_text())
    declared = {normalized(re.split(r"[<>=!~\[ ;]", spec, maxsplit=1)[0]) for spec in manifest["project"]["dependencies"]}
    distributions = packages_distributions()
    undeclared = {
        module for module in imported_modules()
        if not {normalized(d) for d in distributions.get(module, [module])} & declared
    }
    assert not undeclared, f"imported but not declared in pyproject.toml: {sorted(undeclared)}"
