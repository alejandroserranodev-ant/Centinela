import hashlib
import hmac
import logging
import re
import secrets
from functools import cache
from typing import Any, Mapping

from .sources import Sources, load_sources

logger = logging.getLogger(__name__)

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
WIDTH = 6
EDGE_BEFORE = r"(?<![\w-])"
EDGE_AFTER = r"(?![\w-])"


@cache
def catalogue() -> frozenset[str]:
    return personal_columns(load_sources())


def personal_columns(sources: Sources | None = None) -> frozenset[str]:
    if sources is None:
        return catalogue()
    return frozenset(column for table in sources.tables.values() for column in table.personal)


def kind_of(column: str) -> str:
    return column.removesuffix("_id").upper()


def letters(digest: bytes, width: int) -> str:
    number = int.from_bytes(digest, "big")
    drawn = []
    for _ in range(width):
        number, index = divmod(number, len(LETTERS))
        drawn.append(LETTERS[index])
    return "".join(drawn)


class Masking:
    def __init__(self, columns: frozenset[str] | None = None, salt: bytes | None = None):
        self.columns = catalogue() if columns is None else frozenset(columns)
        self._salt = salt or secrets.token_bytes(16)
        self._placeholders: dict[str, str] = {}
        self._originals: dict[str, str] = {}
        self._kinds = re.compile(EDGE_BEFORE + "(?:" + "|".join(sorted({kind_of(column) for column in self.columns})) + r")_[A-Z]{" + str(WIDTH) + "}[A-Z]*" + EDGE_AFTER) if self.columns else None
        self._known: re.Pattern[str] | None = None

    def register(self, column: str, value: Any) -> str | None:
        if column not in self.columns or not isinstance(value, str) or not value.strip():
            return None
        key = value.casefold()
        if key in self._placeholders:
            return self._placeholders[key]
        digest = hmac.new(self._salt, f"{column}\0{value}".encode(), hashlib.sha256).digest()
        width = WIDTH
        placeholder = f"{kind_of(column)}_{letters(digest, width)}"
        while placeholder in self._originals:
            width += 1
            placeholder = f"{kind_of(column)}_{letters(digest, width)}"
        self._placeholders[key] = placeholder
        self._originals[placeholder] = value
        self._known = None
        return placeholder

    def register_row(self, row: Mapping[str, Any]) -> None:
        for column, value in row.items():
            self.register(column, value)

    def register_tree(self, value: Any) -> None:
        if isinstance(value, Mapping):
            for key, inner in value.items():
                if isinstance(inner, str):
                    self.register(str(key), inner)
                else:
                    self.register_tree(inner)
        elif isinstance(value, (list, tuple)):
            for inner in value:
                self.register_tree(inner)

    def placeholder(self, original: str) -> str | None:
        return self._placeholders.get(original.casefold())

    def text(self, text: str) -> str:
        if not self._placeholders:
            return text
        if self._known is None:
            originals = sorted(self._originals.values(), key=len, reverse=True)
            self._known = re.compile(EDGE_BEFORE + "(" + "|".join(map(re.escape, originals)) + ")" + EDGE_AFTER, re.IGNORECASE)
        return self._known.sub(lambda match: self._placeholders[match.group(1).casefold()], text)

    def unmask(self, text: str) -> str:
        if self._kinds is None:
            return text

        def filled(match: re.Match[str]) -> str:
            original = self._originals.get(match.group(0))
            if original is None:
                logger.warning("A model wrote %s, a placeholder no row of the run holds; it stays as written", match.group(0))
                return match.group(0)
            return original

        return self._kinds.sub(filled, text)

    def unmask_tree(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.unmask(value)
        if isinstance(value, Mapping):
            return {key: self.unmask_tree(inner) for key, inner in value.items()}
        if isinstance(value, list):
            return [self.unmask_tree(inner) for inner in value]
        return value
