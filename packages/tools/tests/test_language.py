# One planted violation per bound of the language table in data/kernel/lenguaje.schema.json. Each
# must be refused by the guard lenguaje, with the detail naming the key that broke the bound.
import pytest

from centinela_tools.language import check_block, check_card
from centinela_tools.refusal import Refused

from support import fixture_block, fixture_entries

COL = "pedidos_detalle.valor_neto"


def weekly():
    return fixture_block("ventas_semana_linea")


def with_(change):
    block = weekly()
    change(block)
    return block


def op(left, right):
    return {"op": "+", "izq": left, "der": right}


@pytest.mark.parametrize("metric", ["oc_abiertas", "facturas_abiertas", "ventas_semana_linea"])
def test_every_fixture_block_and_card_is_in_the_language(metric):
    check_block(fixture_block(metric))
    check_card(fixture_entries()[metric])


@pytest.mark.parametrize(
    "block, path",
    [
        pytest.param(with_(lambda b: b.update(unir=["pedidos", "productos", "clientes", "topes"])), "unir", id="four-joins"),
        pytest.param(with_(lambda b: (b.pop("linea_base"), b["salida"].pop("base"), b["salida"].pop("delta"), b.update(ventana={"columna": "pedidos.fecha", "dias": 366}))), "ventana/dias", id="window-past-365"),
        pytest.param(with_(lambda b: b.update(filtro=[{"columna": "pedidos_detalle.cantidad", "op": ">", "valor": i} for i in range(6)])), "filtro", id="six-filters"),
        pytest.param(with_(lambda b: b.update(agrupar=["productos.linea", "productos.clase_abc", "pedidos.canal", "pedidos.ciudad"])), "agrupar", id="four-groups"),
        pytest.param(with_(lambda b: b.update(medida={"agregado": "sum", "de": op(op(op(COL, COL), COL), COL)})), "medida/de", id="expression-depth-three"),
        pytest.param(with_(lambda b: (b.pop("medida"), b.update(razon={"numerador": {"razon": {}}, "denominador": {"agregado": "count"}}))), "razon/numerador", id="ratio-of-a-ratio"),
        pytest.param(with_(lambda b: b["linea_base"].update(n=13)), "linea_base/n", id="baseline-past-12"),
        pytest.param(with_(lambda b: b["salida"].pop("valor")), "salida", id="no-output-value"),
        pytest.param(with_(lambda b: b.update(color="rojo")), "kernel", id="unknown-key"),
        pytest.param(with_(lambda b: b.update(razon={"numerador": {"agregado": "count"}, "denominador": {"agregado": "count"}})), "kernel", id="measure-and-ratio"),
        pytest.param(with_(lambda b: b.update(ventana={"columna": "pedidos.fecha", "dias": 7})), "kernel", id="two-time-frames"),
        pytest.param(with_(lambda b: b["filtro"][0].update(op="like")), "filtro/0/op", id="operator-outside-the-list"),
        pytest.param(with_(lambda b: b["medida"].update(agregado="stddev")), "medida/agregado", id="aggregate-outside-the-list"),
        pytest.param(with_(lambda b: b["filtro"][0].update(valor="50%")), "filtro/0/valor", id="percent"),
        pytest.param(with_(lambda b: b["filtro"][0].update(op="en", valor=[str(i) for i in range(21)])), "filtro/0/valor", id="list-past-20"),
        pytest.param(with_(lambda b: b["salida"].pop("base")), "salida", id="baseline-without-base"),
        pytest.param(with_(lambda b: b["filtro"][0].update(valor="x" * 201)), "filtro/0/valor", id="text-past-200"),
        pytest.param(with_(lambda b: b.pop("linea_base")), "salida", id="base-without-baseline"),
        pytest.param(with_(lambda b: b.update(agrupar=[])), "agrupar", id="empty-groups"),
    ],
)
def test_a_bound_of_the_language_is_refused(block, path):
    with pytest.raises(Refused) as refused:
        check_block(block)
    assert refused.value.guard == "lenguaje"
    assert refused.value.detail.startswith(path), refused.value.detail


def test_an_unknown_key_is_named():
    with pytest.raises(Refused, match="color"):
        check_block(with_(lambda b: b.update(color="rojo")))


def test_a_card_without_tendencia_is_refused():
    entry = fixture_entries()["oc_abiertas"]
    entry.pop("tendencia")
    with pytest.raises(Refused, match="tendencia") as refused:
        check_card(entry)
    assert refused.value.guard == "lenguaje"
