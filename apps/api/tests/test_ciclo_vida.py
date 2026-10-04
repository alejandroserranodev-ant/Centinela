import pytest

from centinela_api.ciclo_vida import ESTADO_A_STATUS, TransicionInvalida, transicionar


def test_transiciones_validas():
    transicionar("new", "analyzing")
    transicionar("analyzing", "proposed")
    transicionar("proposed", "approved")
    transicionar("proposed", "rejected")
    transicionar("approved", "executed")


@pytest.mark.parametrize(
    "actual,siguiente",
    [
        ("new", "proposed"),
        ("proposed", "executed"),
        ("rejected", "approved"),
        ("executed", "new"),
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
    }
