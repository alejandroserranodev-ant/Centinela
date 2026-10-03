import json
from functools import cache
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from jsonschema.exceptions import best_match

from .paths import LENGUAJE
from .refusal import Refused


@cache
def validators() -> tuple[Draft202012Validator, Draft202012Validator]:
    schema = json.loads(LENGUAJE.read_text())
    card = {"$schema": schema["$schema"], "$defs": schema["$defs"], "$ref": "#/$defs/ficha"}
    return Draft202012Validator(schema), Draft202012Validator(card)


def refuse_first(validator: Draft202012Validator, document: Mapping[str, Any], root: str) -> None:
    error = best_match(validator.iter_errors(document))
    if error is not None:
        path = "/".join(str(step) for step in error.absolute_path) or root
        raise Refused("lenguaje", f"{path}: {error.message}")


def check_block(block: Mapping[str, Any]) -> None:
    refuse_first(validators()[0], block, "kernel")


def check_card(entry: Mapping[str, Any]) -> None:
    refuse_first(validators()[1], entry, "ficha")
