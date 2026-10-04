"""
Personal data masking per Ley 1581.

Masks sensitive entity IDs before they reach a model.
- Placeholders are deterministic within a run, random across runs (per-run salt)
- The mapping lives only for the run's duration
- Rows arrive already masked to agents
- Unmasking happens only in what a person reads (from SQL)
"""

import hashlib
import secrets
from typing import Any, Mapping


class RunMasking:
    """Per-run entity masking with deterministic placeholders."""

    # Columns that contain personal data (IDs that resolve to persons on screen)
    PII_COLUMNS = frozenset({
        "cliente_id",
        "proveedor_id",
        "vendedor_id",
        "cliente_nombre",
        "proveedor_nombre",
        "vendedor_nombre",
    })

    def __init__(self, run_id: str = ""):
        """
        Initialize masking for a run.

        Args:
            run_id: Unique identifier for this run (e.g., day + timestamp)
                   If empty, a random salt is generated
        """
        self.run_id = run_id or secrets.token_hex(8)
        self._mapping: dict[str, str] = {}  # Original → Placeholder

    def mask(self, entity_id: str, prefix: str = "E") -> str:
        """
        Get consistent placeholder for an entity within this run.
        Same entity always gets same placeholder during run.
        Different run = different placeholder for same entity.

        Args:
            entity_id: Original value (cliente_id, sku, etc)
            prefix: Placeholder prefix (E for entity, defaults)

        Returns:
            Placeholder like "E-a1b2c3d4"
        """
        if entity_id in self._mapping:
            return self._mapping[entity_id]

        # Deterministic but salted hash
        h = hashlib.sha256(f"{entity_id}|{self.run_id}".encode()).hexdigest()[:8]
        placeholder = f"{prefix}-{h.upper()}"
        self._mapping[entity_id] = placeholder
        return placeholder

    def unmask(self, placeholder: str) -> str | None:
        """Reverse lookup (only valid during run)."""
        for orig, ph in self._mapping.items():
            if ph == placeholder:
                return orig
        return None

    def mask_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """Mask all PII columns in a row."""
        masked = {}
        for key, value in row.items():
            if key in self.PII_COLUMNS and isinstance(value, str):
                masked[key] = self.mask(value)
            else:
                masked[key] = value
        return masked

    def mask_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Mask multiple rows."""
        return [self.mask_row(row) for row in rows]


# Global instance per run (created at request start, discarded at end)
_current_masking: RunMasking | None = None


def set_run_masking(run_id: str) -> RunMasking:
    """Set the masking context for this run."""
    global _current_masking
    _current_masking = RunMasking(run_id)
    return _current_masking


def get_run_masking() -> RunMasking:
    """Get current run's masking (must be set first)."""
    if _current_masking is None:
        raise RuntimeError("No run masking context set. Call set_run_masking first.")
    return _current_masking


def clear_run_masking() -> None:
    """Clear masking context (done at request end)."""
    global _current_masking
    _current_masking = None
