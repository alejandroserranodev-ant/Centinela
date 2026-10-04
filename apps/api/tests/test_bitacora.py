# The bitácora keeps each masked prompt as a row of type prompt, written whole, and the log the
# screens read leaves it out, as it leaves out costo.
import datetime

from centinela_api import bitacora

DIA = datetime.date(2026, 3, 2)


class Conexion:
    def __init__(self):
        self.sentencias = []

    def execute(self, sql, parametros=()):
        self.sentencias.append((sql, parametros))
        return self

    def fetchall(self):
        return []


def test_un_prompt_se_guarda_como_fila_prompt_con_su_texto_entero():
    conn = Conexion()
    bitacora.registrar_prompts(conn, "alerta_1", [{"agent": "analista", "system": "contrato", "user": "detection.entity: CLIENTE_QWERTY"}], DIA)
    ((sql, (alerta, actor, detalle, dia)),) = conn.sentencias
    assert "'prompt'" in sql
    assert (alerta, actor.obj, dia) == ("alerta_1", {"kind": "agent", "agent": "analista"}, DIA)
    assert detalle == "analista\n--- system\ncontrato\n--- user\ndetection.entity: CLIENTE_QWERTY"


def test_la_bitacora_que_leen_las_pantallas_no_trae_prompts():
    conn = Conexion()
    bitacora.listar(conn, None, None)
    ((sql, _),) = conn.sentencias
    assert "tipo NOT IN ('costo', 'prompt')" in sql
