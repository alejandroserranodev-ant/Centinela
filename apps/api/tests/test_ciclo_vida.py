import pytest

from centinela_api.ciclo_vida import ESTADO_A_STATUS, FINALES, TransicionInvalida, recorrer, transicionar


def test_transiciones_validas():
    transicionar("new", "analyzing")
    transicionar("analyzing", "proposed")
    transicionar("proposed", "approved")
    transicionar("proposed", "rejected")
    transicionar("approved", "executed")
    transicionar("new", "merged")
    transicionar("analyzing", "merged")


@pytest.mark.parametrize(
    "actual,siguiente",
    [
        ("new", "proposed"),
        ("proposed", "executed"),
        ("rejected", "approved"),
        ("executed", "new"),
        ("proposed", "merged"),
        ("merged", "analyzing"),
    ],
)
def test_transiciones_invalidas(actual, siguiente):
    with pytest.raises(TransicionInvalida):
        transicionar(actual, siguiente)


def test_estado_a_status_cubre_el_ciclo_completo():
    assert set(ESTADO_A_STATUS.values()) == {
        "new",
        "analyzing",
        "proposed",
        "approved",
        "rejected",
        "executed",
        "merged",
    }


def test_unida_es_final():
    assert FINALES == {"rejected", "executed", "merged"}
    recorrer(["new", "analyzing", "merged"])
    recorrer(["new", "merged"])


def test_recorrer_acepta_un_camino_desde_new():
    recorrer(["new", "analyzing", "proposed"])
    recorrer(["new"])


@pytest.mark.parametrize("estados", [[], ["analyzing", "proposed"], ["new", "proposed"], ["new", "analyzing", "analyzing"]])
def test_recorrer_rechaza_un_camino_que_no_empieza_en_new_o_salta(estados):
    with pytest.raises(TransicionInvalida):
        recorrer(estados)
