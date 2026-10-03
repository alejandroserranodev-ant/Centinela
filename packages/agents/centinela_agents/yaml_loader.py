import re
from pathlib import Path
from typing import Any

import yaml

BOOL_TAG = "tag:yaml.org,2002:bool"


class StrictBoolLoader(yaml.SafeLoader):
    pass


StrictBoolLoader.yaml_implicit_resolvers = {
    first: [(tag, pattern) for tag, pattern in resolvers if tag != BOOL_TAG]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
StrictBoolLoader.add_implicit_resolver(BOOL_TAG, re.compile(r"^(?:true|false)$"), list("tf"))


def parse_yaml(text: str) -> Any:
    return yaml.load(text, Loader=StrictBoolLoader)


def load_yaml(path: Path) -> Any:
    return parse_yaml(path.read_text(encoding="utf-8"))
