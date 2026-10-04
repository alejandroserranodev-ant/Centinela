import datetime
import hashlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from centinela_agents.agents.estratega import described
from centinela_agents.expansion import MOVE, Branch, Retire, Split, apply_move, entry_of, expansion_problems, layer_hash, replay
from centinela_agents.growth import grow
from centinela_agents.schema import ROOT, Tree, index, live
from centinela_agents.skills import action_rows

from . import agentes, bitacora, configuracion, rechazos
from .modelos import ActorAgent, ActorPerson, ExpansionEvidence, Persona, Sentence, TreeExpansion

logger = logging.getLogger(__name__)

CLIENTE = "distribuidora_andina"
CERROJO = "SELECT pg_advisory_xact_lock(hashtext('api.arbol_versiones'))"
COLUMNAS = "id, padre, origen, agente, autor, movimiento, evidencia, retira, base_hash, arbol, dia_simulado, creado_en"
CAMBIOS = ("expansion", "retiro")
DESCARTADA = "descartada"


@dataclass(frozen=True)
class Version:
    id: int
    padre: int | None
    origen: str
    agente: str | None
    autor: Mapping[str, Any] | None
    movimiento: Mapping[str, Any] | None
    evidencia: list[str]
    retira: int | None
    base_hash: str
    arbol: Mapping[str, Any]
    dia_simulado: datetime.date | None
    creado_en: datetime.datetime


class ExpansionDesconocida(Exception):
    pass


class YaRetirada(Exception):
    pass


class RetiroRechazado(Exception):
    def __init__(self, problemas: list[str]):
        super().__init__("; ".join(problemas))
        self.problemas = problemas


def huella(base: Tree) -> str:
    return hashlib.sha256(base.model_dump_json().encode()).hexdigest()


def versiones(conn: psycopg.Connection) -> list[Version]:
    filas = conn.execute(f"SELECT {COLUMNAS} FROM api.arbol_versiones WHERE cliente = %s ORDER BY id", (CLIENTE,)).fetchall()
    return [Version(*fila) for fila in filas]


def insertar(conn: psycopg.Connection, *, padre, origen, arbol: Tree, base: Tree, dia, agente=None, autor=None, movimiento=None, evidencia=(), retira=None) -> int:
    return conn.execute(
        "INSERT INTO api.arbol_versiones (cliente, padre, origen, agente, autor, movimiento, evidencia, retira, "
        "base_version, base_hash, hash_l01, arbol, dia_simulado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (
            CLIENTE, padre, origen, agente,
            None if autor is None else Jsonb(dict(autor)),
            None if movimiento is None else Jsonb(dict(movimiento)),
            Jsonb(list(evidencia)), retira, base.version, huella(base), layer_hash(arbol),
            Jsonb(arbol.model_dump(mode="json")), dia,
        ),
    ).fetchone()[0]


def con_version(arbol: Tree, id: int) -> Tree:
    return arbol.model_copy(update={"version": id})


def actor(fila: Version):
    return ActorAgent(agent=fila.agente) if fila.agente else ActorPerson(**fila.autor)


def accion(metrica: str, id: str) -> str:
    fila = {f"act-{metrica}-{fila.ref}": fila for fila in action_rows(metrica)}.get(id)
    if fila is None:
        return id
    dueno = next((parametro.split(":", 1)[1].strip() for parametro in fila.parameters if parametro.startswith("owner:")), None)
    return described(configuracion.TIPOS.get(fila.type, fila.type) + (f" para {dueno}" if dueno else ""), fila.policy)


def describir(movimiento) -> str:
    if isinstance(movimiento, Split):
        metrica = movimiento.nodo.predicado.valor
        return f"Deja de proponer en {agentes.etiqueta(metrica)}: {'; '.join(accion(metrica, id) for id in movimiento.nueva.hoja.excluye)}"
    if isinstance(movimiento, Branch):
        return f"Vigila {agentes.etiqueta(movimiento.metrica)} en {movimiento.familia}"
    return f"Retira {movimiento.nodo}: {movimiento.motivo}"


def cabeza(filas: list[Version]) -> Version | None:
    return next((fila for fila in reversed(filas) if fila.origen != DESCARTADA), None)


def descartadas(filas: list[Version]) -> set[int]:
    return {fila.retira for fila in filas if fila.origen == DESCARTADA and fila.retira is not None}


def retiros(filas: list[Version]) -> dict[int, Version]:
    caidas = descartadas(filas)
    return {fila.retira: fila for fila in filas if fila.origen == "retiro" and fila.id not in caidas}


def vigente(conn: psycopg.Connection, grounds, growth, dia: datetime.date) -> Tree:
    filas = versiones(conn)
    ultima = cabeza(filas)
    if ultima is not None and ultima.base_hash == huella(grounds.base):
        return con_version(Tree.model_validate(ultima.arbol), ultima.id)
    caidas = descartadas(filas)
    cambios = [fila for fila in filas if fila.origen in CAMBIOS and fila.id not in caidas and fila.retira not in caidas]
    arbol, dropped = replay(grounds.base, [MOVE.validate_python(fila.movimiento) for fila in cambios], grounds, growth.caps)
    id = insertar(conn, padre=ultima.id if ultima else None, origen="base", arbol=arbol, base=grounds.base, dia=dia)
    for posicion, problemas in dropped:
        fila = cambios[posicion]
        logger.warning("Version %s does not apply over the new base: %s", fila.id, problemas)
        insertar(conn, padre=id, origen=DESCARTADA, arbol=arbol, base=grounds.base, dia=dia, agente=fila.agente, autor=fila.autor, movimiento=fila.movimiento, retira=fila.id)
        bitacora.registrar(conn, None, "arbol", actor(fila), f"Un cambio del árbol no se aplicó sobre la base nueva y se descartó: {describir(MOVE.validate_python(fila.movimiento))}", dia)
    return con_version(arbol, id)


def consumidas(filas: list[Version]) -> set[str]:
    return {alerta for fila in filas for alerta in fila.evidencia}


def del_dia(conn: psycopg.Connection, dia: datetime.date) -> Tree:
    grounds, growth = agentes.get_grounds(), agentes.get_growth()
    with conn.transaction():
        conn.execute(CERROJO)
        arbol = vigente(conn, grounds, growth, dia)
        try:
            crecidos = grow(arbol, grounds, growth, rechazos.listar(conn), consumidas(versiones(conn)))
        except Exception as error:
            logger.error("Growing the tree failed: %s", error, exc_info=True)
            crecidos = []
        for crecido in crecidos:
            quien = ActorAgent(agent=crecido.agent)
            movimiento = crecido.move.model_dump(mode="json")
            if crecido.tree is None:
                logger.warning("A draft of %s was refused: %s", crecido.agent, crecido.problems)
                insertar(conn, padre=arbol.version, origen=DESCARTADA, arbol=arbol, base=grounds.base, dia=dia, agente=crecido.agent, movimiento=movimiento, evidencia=crecido.evidence)
                bitacora.registrar(conn, None, "arbol", quien, f"Un cambio del árbol no pasó el validador y se descartó: {describir(crecido.move)}", dia)
                continue
            id = insertar(conn, padre=arbol.version, origen="expansion", arbol=crecido.tree, base=grounds.base, dia=dia, agente=crecido.agent, movimiento=movimiento, evidencia=crecido.evidence)
            arbol = con_version(crecido.tree, id)
            bitacora.registrar(conn, None, "arbol", quien, f"Cambió el árbol de decisión: {describir(crecido.move)}. Lo sostienen {len(crecido.evidence)} alertas rechazadas.", dia)
    return arbol


def estados(filas: list[Version]) -> dict[int, str]:
    ultima = cabeza(filas)
    vivos = live(index(Tree.model_validate(ultima.arbol)), [ROOT]) if ultima else set()
    caidas, retiradas = descartadas(filas), retiros(filas)
    return {
        fila.id: "retired" if fila.id in retiradas else "inactiva" if fila.id in caidas or entry_of(MOVE.validate_python(fila.movimiento)) not in vivos else "active"
        for fila in filas
        if fila.origen == "expansion"
    }


def expansion(fila: Version, estado: str, retiro: Version | None, titulos: Mapping[str, Sentence]) -> TreeExpansion:
    return TreeExpansion(
        id=str(fila.id),
        agent=fila.agente,
        simulated_date=fila.dia_simulado.isoformat() if fila.dia_simulado else None,
        created_at=fila.creado_en.isoformat(),
        description=describir(MOVE.validate_python(fila.movimiento)),
        evidence=[ExpansionEvidence(alert_id=id, title=titulos.get(id) or Sentence(text=id, figures=[])) for id in fila.evidencia],
        status=estado,
        retired_by=retiro.autor["name"] if retiro and retiro.autor else None,
        retire_reason=MOVE.validate_python(retiro.movimiento).motivo if retiro else None,
    )


def expansiones(filas: list[Version], titulos: Mapping[str, Sentence]) -> list[TreeExpansion]:
    estado, retirada = estados(filas), retiros(filas)
    return [
        expansion(fila, estado[fila.id], retirada.get(fila.id) if estado[fila.id] == "retired" else None, titulos)
        for fila in reversed(filas)
        if fila.origen == "expansion"
    ]


def retirar(conn: psycopg.Connection, id: int, motivo: str, persona: Persona, dia: datetime.date, titulos: Mapping[str, Sentence]) -> TreeExpansion:
    grounds, growth = agentes.get_grounds(), agentes.get_growth()
    with conn.transaction():
        conn.execute(CERROJO)
        filas = versiones(conn)
        fila = next((fila for fila in filas if fila.id == id and fila.origen == "expansion"), None)
        if fila is None:
            raise ExpansionDesconocida(id)
        if estados(filas)[id] == "retired":
            raise YaRetirada(id)
        arbol = vigente(conn, grounds, growth, dia)
        if estados(versiones(conn))[id] != "active":
            raise RetiroRechazado([f"version {id} no longer holds in the tree"])
        cambio = MOVE.validate_python(fila.movimiento)
        movimiento = Retire(nodo=entry_of(cambio), motivo=motivo.strip())
        problemas = expansion_problems(arbol, movimiento, grounds, growth.caps)
        if problemas:
            raise RetiroRechazado(problemas)
        autor = {"name": persona.name, "role": persona.role}
        insertar(conn, padre=arbol.version, origen="retiro", arbol=apply_move(arbol, movimiento), base=grounds.base, dia=dia, autor=autor, movimiento=movimiento.model_dump(mode="json"), retira=id)
        bitacora.registrar(conn, None, "arbol", ActorPerson(**autor), f"Retiró el cambio del árbol «{describir(cambio)}»: {motivo.strip()}", dia)
    return next(expansion for expansion in expansiones(versiones(conn), titulos) if expansion.id == str(id))
