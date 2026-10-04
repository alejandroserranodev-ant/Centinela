# The tree's versions in apps/api over an in-memory store: the base row a first day writes, the
# expansion three rejections draft, the evidence a version already used or a refused draft spent,
# the replay a change to what the validator reads forces, the status each expansion takes from
# the current tree, and the retirement of an expansion and its refusals, and why an inactive one
# is so.
import datetime as dt
from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from centinela_agents.expansion import Caps, Growth, depth
from centinela_agents.growth import Rejection
from centinela_agents.schema import index
from centinela_agents.validator import load_grounds

from centinela_api import agentes, arboles
from centinela_api.modelos import Persona
from corridas import ARBOL, CONTEXTO

DIA = dt.date(2026, 1, 15)
GERENTE = Persona(email="gerente@andina.test", name="Ana", role="gerente")
GROUNDS = load_grounds(agentes._ARBOL.parent, agentes.METRICAS, agentes._SKILLS, CONTEXTO.catalog)
GROWTH = Growth({"estratega": 3}, Caps(depth=100, nodes_per_stage=100))
DIVISION = "proponer.cartera.saldo_vencido.division_1"
ESTRECHO = Growth({"estratega": 3}, Caps(depth=3, nodes_per_stage=100))


class Almacen:
    def __init__(self):
        self.filas: list[arboles.Version] = []

    def versiones(self, conn):
        return list(self.filas)

    def insertar(self, conn, *, padre, origen, arbol, grounds, growth, dia, agente=None, autor=None, movimiento=None, evidencia=(), retira=None):
        fila = arboles.Version(len(self.filas) + 1, padre, origen, agente, autor, movimiento, list(evidencia), retira, arboles.huella(grounds, growth), arbol.model_dump(mode="json"), dia, dt.datetime(2026, 10, 4, 12, tzinfo=dt.UTC))
        self.filas.append(fila)
        return fila.id


@pytest.fixture
def almacen(monkeypatch):
    almacen = Almacen()
    monkeypatch.setattr(arboles, "versiones", almacen.versiones)
    monkeypatch.setattr(arboles, "insertar", almacen.insertar)
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: GROUNDS)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: GROWTH)
    monkeypatch.setattr(arboles.rechazos, "listar", lambda conn: [])
    monkeypatch.setattr(arboles.bitacora, "registrar", MagicMock())
    return almacen


def tres_rechazos(monkeypatch, fila="r1", desde=0, antes=()):
    rechazos = [*antes, *(Rejection(f"alerta_{n}", "saldo_vencido", "propuesta", (f"act-saldo_vencido-{fila}",)) for n in range(desde, desde + 3))]
    monkeypatch.setattr(arboles.rechazos, "listar", lambda conn: rechazos)
    return rechazos


def base_nueva(monkeypatch, version):
    nueva = GROUNDS.base.model_copy(update={"version": version})
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: replace(GROUNDS, base=nueva))


def test_el_primer_dia_guarda_el_arbol_base_y_lo_entrega_con_su_version(almacen):
    arbol = arboles.del_dia(MagicMock(), DIA)
    (fila,) = almacen.filas
    assert (fila.origen, fila.padre) == ("base", None)
    assert arbol.version == fila.id and arbol.nodos == ARBOL.nodos


def test_otro_dia_sobre_la_misma_base_no_escribe_otra_version(almacen):
    arboles.del_dia(MagicMock(), DIA)
    arboles.del_dia(MagicMock(), DIA)
    assert len(almacen.filas) == 1


def test_tres_rechazos_de_una_fila_dividen_la_hoja_de_estratega(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arbol = arboles.del_dia(MagicMock(), DIA)
    base, expansion = almacen.filas
    assert (expansion.origen, expansion.agente, expansion.padre) == ("expansion", "estratega", base.id)
    assert expansion.evidencia == ["alerta_0", "alerta_1", "alerta_2"]
    assert arbol.version == expansion.id and DIVISION in {nodo.id for nodo in arbol.nodos}
    registro = arboles.bitacora.registrar.call_args.args
    assert registro[2] == "arbol" and registro[3].agent == "estratega"
    assert registro[4].startswith("Cambió el árbol de decisión: Deja de proponer en Cartera vencida: Borrador de correo")


def test_la_evidencia_de_una_version_no_cuenta_otra_vez(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion"]


def test_una_base_nueva_reaplica_las_expansiones_que_aun_pasan(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    nueva = GROUNDS.base.model_copy(update={"version": 2})
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: replace(GROUNDS, base=nueva))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "base"]
    assert DIVISION in {nodo.id for nodo in arbol.nodos} and arbol.version == almacen.filas[-1].id


def test_una_base_nueva_descarta_y_registra_la_expansion_que_ya_no_pasa(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    nueva = GROUNDS.base.model_copy(update={"version": 2})
    monkeypatch.setattr(arboles.agentes, "get_grounds", lambda: replace(GROUNDS, base=nueva))
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: Growth({"estratega": 3}, Caps(depth=3, nodes_per_stage=100)))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert DIVISION not in {nodo.id for nodo in arbol.nodos}
    detalle = arboles.bitacora.registrar.call_args_list[-1].args[4]
    assert detalle.startswith("Un cambio del árbol ya no cumple las reglas vigentes del árbol y se descartó")


def test_un_fallo_al_crecer_deja_correr_el_dia_sobre_la_version_vigente(almacen, monkeypatch, caplog):
    monkeypatch.setattr(arboles, "grow", MagicMock(side_effect=RuntimeError("roto")))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert arbol.version == almacen.filas[-1].id
    assert "Growing the tree failed" in caplog.text


def test_retirar_una_expansion_la_marca_y_su_evidencia_no_vuelve_a_contar(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    expansion = arboles.retirar(MagicMock(), 2, " No ayudó ", GERENTE, DIA, {})
    assert (expansion.status, expansion.retired_by, expansion.retire_reason) == ("retired", "Ana", "No ayudó")
    retiro = almacen.filas[-1]
    assert (retiro.origen, retiro.retira, retiro.autor) == ("retiro", 2, {"name": "Ana", "role": "gerente"})
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert next(nodo for nodo in arbol.nodos if nodo.id == DIVISION).retirado == "No ayudó"
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "retiro"]


@pytest.mark.parametrize(
    "id, motivo, error",
    [(9, "No ayudó", arboles.ExpansionDesconocida), (1, "No ayudó", arboles.ExpansionDesconocida), (2, "   ", arboles.RetiroRechazado)],
    ids=["unknown", "a base row", "no reason"],
)
def test_retirar_rechaza_lo_que_no_es_una_expansion_retirable(almacen, monkeypatch, id, motivo, error):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    with pytest.raises(error):
        arboles.retirar(MagicMock(), id, motivo, GERENTE, DIA, {})


def test_retirar_dos_veces_es_un_error(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    arboles.retirar(MagicMock(), 2, "No ayudó", GERENTE, DIA, {})
    with pytest.raises(arboles.YaRetirada):
        arboles.retirar(MagicMock(), 2, "Otra vez", GERENTE, DIA, {})


def test_la_lista_trae_las_expansiones_mas_nuevas_primero_con_el_titulo_de_su_evidencia(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    titulo = arboles.Sentence(text="Cartera vencida de CLI-001", figures=[])
    (expansion,) = arboles.expansiones(almacen.filas, {"alerta_0": titulo})
    assert (expansion.id, expansion.agent, expansion.status) == ("2", "estratega", "active")
    assert [evidencia.title.text for evidencia in expansion.evidence] == ["Cartera vencida de CLI-001", "alerta_1", "alerta_2"]


def test_un_borrador_rechazado_se_descarta_una_vez_y_su_evidencia_no_vuelve_a_contar(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: ESTRECHO)
    primero = arboles.del_dia(MagicMock(), DIA)
    segundo = arboles.del_dia(MagicMock(), DIA)
    base, descartada = almacen.filas
    assert (descartada.origen, descartada.evidencia) == ("descartada", ["alerta_0", "alerta_1", "alerta_2"])
    assert primero.version == segundo.version == base.id
    arboles.bitacora.registrar.assert_called_once()
    assert arboles.bitacora.registrar.call_args.args[4].startswith("Un cambio del árbol no pasó el validador y se descartó")
    assert arboles.expansiones(almacen.filas, {}) == []


def test_una_expansion_descartada_sobre_la_base_nueva_queda_inactiva_y_no_se_retira(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    base_nueva(monkeypatch, 2)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: ESTRECHO)
    arboles.del_dia(MagicMock(), DIA)
    arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "base", "descartada"]
    assert arboles.bitacora.registrar.call_count == 2
    (expansion,) = arboles.expansiones(almacen.filas, {})
    assert (expansion.id, expansion.status, expansion.inactive_reason) == ("2", "inactive", "dropped_by_base")
    with pytest.raises(arboles.YaNoAplica):
        arboles.retirar(MagicMock(), 2, "No ayudó", GERENTE, DIA, {})


def test_una_division_que_reusa_el_id_de_una_descartada_no_choca_con_ella(almacen, monkeypatch):
    rechazos = tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    base_nueva(monkeypatch, 2)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: ESTRECHO)
    arboles.del_dia(MagicMock(), DIA)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: GROWTH)
    tres_rechazos(monkeypatch, "r2", 3, rechazos)
    arboles.del_dia(MagicMock(), DIA)
    base_nueva(monkeypatch, 3)
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "base", "descartada", "base", "expansion", "base"]
    hoja = next(nodo for nodo in arbol.nodos if nodo.id == "hoja.estratega.proponer.saldo_vencido.1")
    assert hoja.hoja.excluye == ("act-saldo_vencido-r2",)
    assert [(expansion.id, expansion.status) for expansion in arboles.expansiones(almacen.filas, {})] == [("6", "active"), ("2", "inactive")]


def test_una_division_anidada_bajo_una_retirada_queda_inactiva_y_no_se_retira(almacen, monkeypatch):
    rechazos = tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    tres_rechazos(monkeypatch, "r2", 3, rechazos)
    arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "expansion"]
    arboles.retirar(MagicMock(), 2, "No ayudó", GERENTE, DIA, {})
    assert [(expansion.id, expansion.status, expansion.inactive_reason) for expansion in arboles.expansiones(almacen.filas, {})] == [("3", "inactive", "parent_retired"), ("2", "retired", None)]
    with pytest.raises(arboles.YaNoAplica):
        arboles.retirar(MagicMock(), 3, "No ayudó", GERENTE, DIA, {})


def test_una_division_anidada_describe_solo_la_fila_que_agrega(almacen, monkeypatch):
    rechazos = tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    tres_rechazos(monkeypatch, "r2", 3, rechazos)
    arboles.del_dia(MagicMock(), DIA)
    primera, segunda = (expansion.description for expansion in reversed(arboles.expansiones(almacen.filas, {})))
    assert ";" not in segunda and segunda != primera
    assert arboles.bitacora.registrar.call_args.args[4].count(";") == 0


def test_un_fallo_al_rehacer_la_version_guardada_sale_del_dia(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    base_nueva(monkeypatch, 2)
    monkeypatch.setattr(arboles, "replay", MagicMock(side_effect=RuntimeError("roto")))
    with pytest.raises(RuntimeError, match="roto"):
        arboles.del_dia(MagicMock(), DIA)


def test_un_cambio_en_lo_que_lee_el_validador_reaplica_las_expansiones(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: Growth({"estratega": 4}, GROWTH.caps))
    arboles.del_dia(MagicMock(), DIA)
    assert [fila.origen for fila in almacen.filas] == ["base", "expansion", "base"]


def test_una_base_nueva_que_descarta_una_expansion_retirada_conserva_el_retiro(almacen, monkeypatch):
    tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    arboles.retirar(MagicMock(), 2, "No ayudó", GERENTE, DIA, {})
    arboles.bitacora.registrar.reset_mock()
    base_nueva(monkeypatch, 2)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: ESTRECHO)
    arboles.del_dia(MagicMock(), DIA)
    assert [(fila.origen, fila.retira) for fila in almacen.filas] == [("base", None), ("expansion", None), ("retiro", 2), ("base", None), ("descartada", 2)]
    arboles.bitacora.registrar.assert_called_once()
    (expansion,) = arboles.expansiones(almacen.filas, {})
    assert (expansion.status, expansion.retired_by, expansion.retire_reason, expansion.inactive_reason) == ("retired", "Ana", "No ayudó", None)


def test_una_base_nueva_descarta_en_la_misma_pasada_una_division_y_la_que_anida_bajo_ella(almacen, monkeypatch):
    rechazos = tres_rechazos(monkeypatch)
    arboles.del_dia(MagicMock(), DIA)
    tres_rechazos(monkeypatch, "r2", 3, rechazos)
    arboles.del_dia(MagicMock(), DIA)
    arboles.bitacora.registrar.reset_mock()
    base_nueva(monkeypatch, 2)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: ESTRECHO)
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert [(fila.origen, fila.retira) for fila in almacen.filas] == [("base", None), ("expansion", None), ("expansion", None), ("base", None), ("descartada", 2), ("descartada", 3)]
    assert arbol.nodos == ARBOL.nodos and arboles.bitacora.registrar.call_count == 2
    assert [(expansion.id, expansion.status, expansion.inactive_reason) for expansion in arboles.expansiones(almacen.filas, {})] == [("3", "inactive", "dropped_by_base"), ("2", "inactive", "dropped_by_base")]


def test_una_base_nueva_descarta_la_division_anidada_y_conserva_la_primera(almacen, monkeypatch):
    rechazos = tres_rechazos(monkeypatch)
    primera = arboles.del_dia(MagicMock(), DIA)
    tres_rechazos(monkeypatch, "r2", 3, rechazos)
    segunda = arboles.del_dia(MagicMock(), DIA)
    assert depth(index(segunda)) > depth(index(primera))
    base_nueva(monkeypatch, 2)
    monkeypatch.setattr(arboles.agentes, "get_growth", lambda: Growth({"estratega": 3}, Caps(depth=depth(index(primera)), nodes_per_stage=100)))
    arbol = arboles.del_dia(MagicMock(), DIA)
    assert [(fila.origen, fila.retira) for fila in almacen.filas][-2:] == [("base", None), ("descartada", 3)]
    assert DIVISION in {nodo.id for nodo in arbol.nodos}
    assert [(expansion.id, expansion.status, expansion.inactive_reason) for expansion in arboles.expansiones(almacen.filas, {})] == [("3", "inactive", "dropped_by_base"), ("2", "active", None)]
