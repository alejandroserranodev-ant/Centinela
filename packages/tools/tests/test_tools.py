# The tools with no database: the catalogue built from metricas.yaml entries and approved records,
# and the refusals that must happen before any connection opens (hash, catalogo, lenguaje).
from datetime import date

import pytest

from centinela_tools.compiler import compile_kpi, freeze
from centinela_tools.refusal import Refused
from centinela_tools.settings import Settings
from centinela_tools.sources import load_sources
from centinela_tools.tools import catalogue_of, kpi_catalogo, kpi_consultar, kpi_validar

from support import fixture_block, fixture_entries

SOURCES = load_sources()
DAY = date(2026, 3, 2)


def never(role):
    raise AssertionError("a refusal before any SQL opens no connection")


def approved(kpi_id="aprobado_oc", tamper=False):
    frozen = freeze(compile_kpi(fixture_block("oc_abiertas"), SOURCES))
    entry = fixture_entries()["oc_abiertas"]
    return {
        "id": kpi_id,
        "sql": frozen.sql + (" " if tamper else ""),
        "hash": frozen.hash,
        "version_compilador": frozen.compiler_version,
        "ficha": {key: entry[key] for key in ("descripcion", "unidad", "rango", "tendencia", "temporalidad", "audiencia")},
        "descriptivo": True,
        "entidad": ["proveedor_id"],
        "columnas": [{"nombre": "proveedor_id", "tipo": "text"}, {"nombre": "ordenes_abiertas", "tipo": "bigint"}],
    }


def test_the_catalogue_lists_entries_with_a_block_and_approved_records():
    entries = {**fixture_entries(), "sin_bloque": {"descripcion": "no compila"}}
    listed = {kpi["id"]: kpi for kpi in kpi_catalogo(catalogue_of(entries, SOURCES, [approved()]))}
    assert set(listed) == {"oc_abiertas", "facturas_abiertas", "ventas_semana_linea", "aprobado_oc"}
    assert listed["oc_abiertas"]["descriptivo"] is True and listed["facturas_abiertas"]["descriptivo"] is False
    assert listed["aprobado_oc"]["origen"] == "aprobado"
    assert listed["ventas_semana_linea"]["entidad"] == ["linea"]
    assert listed["oc_abiertas"]["ficha"]["tendencia"] == "menor_es_mejor"


def test_an_approved_kpi_whose_text_no_longer_matches_its_hash_is_refused():
    catalogue = catalogue_of({}, SOURCES, [approved(tamper=True)])
    with pytest.raises(Refused) as refused:
        kpi_consultar("aprobado_oc", DAY, catalogue, never, Settings())
    assert refused.value.guard == "hash"


def test_a_kpi_in_no_catalogue_is_refused():
    with pytest.raises(Refused) as refused:
        kpi_consultar("inventado", DAY, catalogue_of({}, SOURCES), never, Settings())
    assert refused.value.guard == "catalogo"


def test_a_block_outside_the_language_is_refused_before_connecting():
    block = fixture_block("oc_abiertas")
    block["unir"] = ["proveedores", "productos", "proveedores", "productos"]
    with pytest.raises(Refused) as refused:
        kpi_validar(block, DAY, SOURCES, never, Settings())
    assert refused.value.guard == "lenguaje"


def test_an_approved_id_that_clashes_with_a_base_kpi_fails_the_catalogue():
    with pytest.raises(ValueError):
        catalogue_of(fixture_entries(), SOURCES, [approved("oc_abiertas")])
