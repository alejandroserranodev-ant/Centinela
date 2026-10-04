# A run's mapping masks the values of the columns fuentes.yaml lists under personales: the same
# value reads the same placeholder inside one Masking and another one in the next, a placeholder
# holds no digit, free text is masked by the mapping alone, and a placeholder the mapping lacks
# is left as written.
import re

from centinela_tools.masking import Masking, personal_columns

COLUMNS = frozenset({"cliente_id", "vendedor_id", "nombre"})


def test_the_catalogue_is_the_personales_of_fuentes():
    assert personal_columns() == frozenset({"cliente_id", "proveedor_id", "vendedor_id", "nombre"})


def test_a_value_reads_one_placeholder_inside_a_run_and_another_across_runs():
    run, other = Masking(COLUMNS), Masking(COLUMNS)
    first = run.register("cliente_id", "C0496")
    assert run.register("cliente_id", "C0496") == first
    assert first.startswith("CLIENTE_")
    assert other.register("cliente_id", "C0496") != first


def test_a_placeholder_holds_no_digit():
    run = Masking(COLUMNS)
    placeholders = [run.register("cliente_id", f"C{index:04d}") for index in range(300)]
    assert not any(re.search(r"\d", placeholder) for placeholder in placeholders)
    assert len(set(placeholders)) == 300


def test_a_column_outside_the_catalogue_passes_unchanged():
    run = Masking(COLUMNS)
    assert run.register("sku", "SKU-0001") is None
    run.register_row({"cliente_id": "C0496", "sku": "SKU-0001", "saldo": 120})
    assert run.text("C0496 compra SKU-0001") == f"{run.placeholder('C0496')} compra SKU-0001"


def test_text_is_masked_whole_tokens_only_and_ignoring_case():
    run = Masking(COLUMNS)
    run.register_row({"vendedor_id": "VEN-01"})
    run.register_row({"vendedor_id": "VEN-010"})
    masked = run.text("ven-01 vende menos que VEN-010; VEN-01X no es un vendedor")
    assert masked == f"{run.placeholder('VEN-01')} vende menos que {run.placeholder('VEN-010')}; VEN-01X no es un vendedor"


def test_a_name_is_masked_wherever_the_text_carries_it():
    run = Masking(COLUMNS)
    run.register_row({"cliente_id": "C0496", "nombre": "Ferretería López"})
    masked = run.text('La causa: "Ferretería López (C0496) dejó de pagar"')
    assert "López" not in masked and "C0496" not in masked
    assert run.placeholder("Ferretería López").startswith("NOMBRE_")


def test_register_tree_reads_personal_keys_at_any_depth():
    run = Masking(COLUMNS)
    run.register_tree({"actions": [{"parameters": {"cliente_id": "C0496", "owner": "Cartera"}}], "row": {"vendedor_id": "VEN-01"}})
    assert run.placeholder("C0496") and run.placeholder("VEN-01")
    assert run.placeholder("Cartera") is None


def test_unmask_fills_a_known_placeholder_and_leaves_an_unknown_one(caplog):
    run = Masking(COLUMNS)
    placeholder = run.register("cliente_id", "C0496")
    assert run.unmask(f"El cliente {placeholder} no paga") == "El cliente C0496 no paga"
    assert run.unmask("El cliente CLIENTE_QQQQQQ no paga") == "El cliente CLIENTE_QQQQQQ no paga"
    assert "CLIENTE_QQQQQQ" in caplog.text


def test_unmask_tree_fills_every_string_of_an_answer():
    run = Masking(COLUMNS)
    placeholder = run.register("cliente_id", "C0496")
    answer = {"sentence": f"{placeholder} debe {{0}}", "evidence": [{"claim": placeholder, "figures": ["f1"]}], "level": 2}
    assert run.unmask_tree(answer) == {"sentence": "C0496 debe {0}", "evidence": [{"claim": "C0496", "figures": ["f1"]}], "level": 2}
