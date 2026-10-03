# fuentes.yaml is checked against data/sql/01_esquema.sql, so it cannot name a table, a column, a
# key or a join the schema does not hold, and every column of the schema is either readable or
# excluded with a reason. A planted inconsistency per rule of sources.py:load_sources fails the load.
import copy

import pytest
import yaml

from centinela_tools.paths import FUENTES
from centinela_tools.sources import load_sources

from support import schema_tables

SCHEMA = schema_tables()
SOURCES = load_sources()


def test_every_table_and_column_exists_in_the_schema_with_its_type():
    for name, table in SOURCES.tables.items():
        assert name in SCHEMA, name
        for column, kind in table.columns.items():
            assert SCHEMA[name].columns.get(column) == kind, f"{name}.{column}"


def test_every_column_of_the_schema_is_readable_or_excluded_with_a_reason():
    for name, table in SOURCES.tables.items():
        assert set(table.columns) | set(table.excluded) == set(SCHEMA[name].columns), name
        assert all(reason.strip() for reason in table.excluded.values()), name


def test_every_key_is_the_primary_key_of_the_schema():
    for name, table in SOURCES.tables.items():
        assert set(table.key) == set(SCHEMA[name].key), name


def test_every_join_follows_a_foreign_key_or_reaches_a_ref_tables_key():
    for source in SOURCES.sources.values():
        owners = {source.name: source.name, **{join.name: join.table for join in source.joins.values()}}
        for join in source.joins.values():
            origin = owners[join.origin]
            for local in join.on:
                assert SCHEMA[origin].references.get(local) == join.table or join.table.startswith("ref_"), f"{source.name}.{join.name}"


def test_every_closing_reads_a_child_that_references_its_source():
    for source in SOURCES.sources.values():
        for closing in source.closings.values():
            for child_column in closing.on:
                assert SCHEMA[closing.table].references.get(child_column) == source.name, f"{source.name}.{closing.name}"


def test_a_persons_name_is_excluded_and_the_two_states_are_fuga():
    assert "nombre" in SOURCES.tables["vendedores"].excluded
    assert SOURCES.tables["pedidos"].leaks["estado"] == ("Cancelado",)
    assert SOURCES.tables["ordenes_compra"].leaks["estado"] == ()


def test_every_date_column_has_a_role():
    for name, table in SOURCES.tables.items():
        assert set(table.dates) == {c for c, kind in table.columns.items() if kind == "date"}, name


def planted(change, tmp_path):
    data = copy.deepcopy(yaml.safe_load(FUENTES.read_text()))
    change(data)
    path = tmp_path / "fuentes.yaml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True))
    return path


@pytest.mark.parametrize(
    "change",
    [
        pytest.param(lambda d: d["tablas"]["facturas"]["fechas"].pop("fecha_vencimiento"), id="a-date-without-role"),
        pytest.param(lambda d: d["tablas"]["facturas"]["fechas"].update(fecha_factura="hoy"), id="a-role-outside-the-list"),
        pytest.param(lambda d: d["fuentes"]["pagos"]["uniones"]["facturas"].update(por={"factura_id": "cliente_id"}), id="a-join-short-of-the-key"),
        pytest.param(lambda d: d["fuentes"]["pagos"]["uniones"]["clientes"].update(desde="nadie"), id="a-join-from-nowhere"),
        pytest.param(lambda d: d["fuentes"]["pedidos_detalle"].pop("fechada_por"), id="a-source-with-no-date"),
        pytest.param(lambda d: d["fuentes"]["pedidos"]["dimensiones"].append("pedidos.estado"), id="a-fuga-dimension"),
        pytest.param(lambda d: d["fuentes"]["facturas"]["cierres"]["pagada"].update(fecha="valor"), id="a-closing-without-event"),
    ],
)
def test_an_inconsistent_fuentes_fails_the_load(change, tmp_path):
    with pytest.raises(ValueError, match="fuentes.yaml"):
        load_sources(planted(change, tmp_path))
