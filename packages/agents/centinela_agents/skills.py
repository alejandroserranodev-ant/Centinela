import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

SKILLS = Path(__file__).resolve().parents[1] / "skills"


@cache
def skill(agent: str, *names: str) -> str:
    return "\n\n".join((SKILLS / agent / f"{name}.md").read_text(encoding="utf-8").strip() for name in names)


@dataclass(frozen=True)
class ActionRow:
    ref: str
    condition: str
    type: str
    parameters: tuple[str, ...]
    formula: str | None
    policy: str


def cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


@cache
def actions_table(root: Path) -> str:
    return (root / "estratega" / "acciones.md").read_text(encoding="utf-8").strip().split("\n## ", 1)[0]


def action_rows(metric: str, root: Path = SKILLS) -> list[ActionRow]:
    table = actions_table(root)
    rows = []
    for line in table.splitlines():
        if not line.startswith(f"| `{metric}` |"):
            continue
        _, condition, kind, parameters, formula, policy = cells(line)
        formula_name = formula.strip("`")
        rows.append(
            ActionRow(
                ref=f"r{len(rows) + 1}",
                condition=condition,
                type=kind.strip("`"),
                parameters=tuple(re.findall(r"`([^`]+)`", parameters)),
                formula=None if formula_name == "none" else formula_name,
                policy=policy.replace("`", ""),
            )
        )
    return rows
