"""Tests for data masking per Ley 1581."""

import pytest
from centinela_tools.masking import RunMasking, set_run_masking, get_run_masking, clear_run_masking


def test_mask_consistency_within_run():
    """Same entity gets same placeholder during a run."""
    run = RunMasking("test-run-1")

    ph1 = run.mask("C123")
    ph2 = run.mask("C123")

    assert ph1 == ph2
    assert ph1.startswith("E-")


def test_mask_differs_across_runs():
    """Same entity gets different placeholders in different runs."""
    run1 = RunMasking("test-run-1")
    run2 = RunMasking("test-run-2")

    ph1 = run1.mask("C123")
    ph2 = run2.mask("C123")

    assert ph1 != ph2


def test_mask_row():
    """Mask all PII columns in a row."""
    run = RunMasking("test-run-1")

    row = {
        "cliente_id": "C123",
        "margen_pct": 15.5,
        "vendedor_id": "V456",
    }

    masked = run.mask_row(row)

    assert masked["cliente_id"].startswith("E-")
    assert masked["margen_pct"] == 15.5  # Not masked
    assert masked["vendedor_id"].startswith("E-")
    assert masked["cliente_id"] != "C123"


def test_unmask():
    """Unmask placeholder to original value."""
    run = RunMasking("test-run-1")

    original = "C123"
    masked = run.mask(original)
    unmasked = run.unmask(masked)

    assert unmasked == original


def test_mask_rows():
    """Mask multiple rows."""
    run = RunMasking("test-run-1")

    rows = [
        {"cliente_id": "C123", "saldo": 1000000},
        {"cliente_id": "C456", "saldo": 2000000},
    ]

    masked = run.mask_rows(rows)

    assert len(masked) == 2
    assert masked[0]["cliente_id"] != "C123"
    assert masked[1]["cliente_id"] != "C456"
    # Different clients get different placeholders
    assert masked[0]["cliente_id"] != masked[1]["cliente_id"]


def test_global_run_masking():
    """Global masking context works correctly."""
    try:
        set_run_masking("test-run")
        m = get_run_masking()

        ph = m.mask("C123")
        assert ph.startswith("E-")
    finally:
        clear_run_masking()


def test_pii_columns():
    """Only listed PII columns are masked."""
    run = RunMasking("test-run-1")

    row = {
        "cliente_id": "C123",  # Masked
        "cliente_nombre": "Acme Inc",  # Masked
        "linea": "Hogar",  # Not masked
        "margen_pct": 25.5,  # Not masked
    }

    masked = run.mask_row(row)

    assert masked["cliente_id"] != "C123"
    assert masked["cliente_nombre"] != "Acme Inc"
    assert masked["linea"] == "Hogar"
    assert masked["margen_pct"] == 25.5
