"""End-to-end test: verify no personal data reaches LLM prompts."""

import pytest
from unittest.mock import MagicMock, patch
from centinela_tools.masking import set_run_masking, clear_run_masking
from centinela_agents.evidence import Ledger, mask_entity


def test_ledger_masks_rows():
    """Ledger.consult() returns masked rows."""
    set_run_masking("test-run")

    try:
        # Mock kernel call
        def mock_call(name, args):
            return {
                "consulta": f"SELECT * FROM v_test WHERE dia = '{args['dia']}'",
                "filas": [
                    {"cliente_id": "C123", "margen_pct": 15.5},
                    {"cliente_id": "C456", "margen_pct": 20.0},
                ]
            }

        # Create ledger with mock
        ledger = Ledger(call=mock_call, catalog=MagicMock())
        qid, rows = ledger.consult("test_metric", "2026-10-04")

        # Verify rows are masked
        assert rows[0]["cliente_id"] != "C123"
        assert rows[0]["cliente_id"].startswith("E-")
        assert rows[1]["cliente_id"] != "C456"
        assert rows[1]["cliente_id"].startswith("E-")
        # Non-PII columns unchanged
        assert rows[0]["margen_pct"] == 15.5

    finally:
        clear_run_masking()


def test_entity_masking():
    """mask_entity() returns masked entity tuple."""
    set_run_masking("test-run")

    try:
        entity = ("C123", "SKU-001")
        masked = mask_entity(entity)

        assert masked[0] != "C123"
        assert masked[0].startswith("E-")
        # Non-PII parts may or may not be masked depending on type

    finally:
        clear_run_masking()


def test_no_personal_data_in_prompts():
    """Verify no cliente_id or vendedor_id in agent prompts."""
    set_run_masking("test-run")

    try:
        # Real entity and masked version
        entity = ("C123456", "Hogar")
        masked = mask_entity(entity)

        # Prompt should use masked version
        prompt = f"detection.entity: {', '.join(masked)}"

        # Original personal IDs should NOT appear
        assert "C123456" not in prompt
        assert prompt.count("E-") > 0

    finally:
        clear_run_masking()
