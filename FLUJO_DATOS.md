# Flujo de datos: Cómo el API conecta todo

## Visión general

```
┌─────────────────────────────────────────────────────────────┐
│ apps/web ← HTTP REST ← apps/api ← PostgreSQL (centinela)    │
│ Usuarios    Public endpoints  schemas internos    data/sql/ │
└─────────────────────────────────────────────────────────────┘
                           ↓
              Vigía (packages/agents)
                           ↓
              tools/SQL (packages/tools/MCP)
                           ↓
              PostgreSQL: READ-ONLY user (tools_reader)
```

## El reloj simulado

**Dueño**: `apps/api` (tabla `api.simulacion.dia_actual`)

**Flujo**:

1. Usuario hace `POST /simulacion/avanzar?dias=1`
2. API avanza la fecha de `2026-01-14` a `2026-01-15`
3. API llama a Vigía (packages/agents) con el día actual
4. Vigía hace `GET /simulacion/dia-actual` → recibe `{"dia": "2026-01-15"}`
5. Vigía pasa `fecha_maxima=2026-01-15` a tools/SQL para cada consulta
6. tools/SQL conecta como `tools_reader` (READ-ONLY)
7. tools/SQL ejecuta: `SELECT * FROM centinela.v_margen_semanal_linea WHERE semana <= '2026-01-15'`

## Los 5 escenarios anunciados (en data/metricas.yaml)

| Escenario | Métrica | Vista SQL | Vigía detecta | Umbral |
|---|---|---|---|---|
| Margen bajo | `margen_pct` | `v_margen_semanal_linea` | Caída > 3 puntos / semana | ref_margen_minimo_linea |
| Mora (overdue debt) | `saldo_vencido` | `v_cartera_cliente` | Facturas vencidas por cliente | max_dias_vencido > 15 |
| Quiebre de stock | `cobertura_dias` | `v_cobertura_inventario` | Días de cobertura < 10 (clase A) | crítico < 5 con pedidos |
| Descuentos fuera política | `descuento_en_exceso` | `v_descuentos_fuera_politica` | Descuentos sin aprobación | vendedor + semana |
| Cliente que se va | `veces_intervalo_habitual` | `v_actividad_cliente` | Inactividad > 3x el intervalo | clientes con 10+ pedidos |

## Los usuarios de la BD

| Usuario | Rol | Conexión | Acceso | Quién usa |
|---|---|---|---|---|
| `centinela` (admin) | Propietario | DSN_ADMIN | TODAS las operaciones | API, setup, migraciones |
| `tools_reader` | Lector | DSN_READ_ONLY | SELECT solo en schema `centinela` | packages/tools (MCP SQL) |

**Creación** (en `data/sql/01_esquema.sql`):

```sql
CREATE ROLE tools_reader WITH LOGIN PASSWORD 'tools_reader_password';
GRANT USAGE ON SCHEMA centinela TO tools_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA centinela TO tools_reader;
```

## Ciclo de vida de una alerta

```
1. POST /simulacion/avanzar
   ↓
2. Vigía detecta anomalía en metricas
   POST /interno/alertas (Vigía, X-Agent-Key)
   Status: new
   ↓
3. Analista explica la causa
   PUT /interno/alertas/{id}/causa (Analista, X-Agent-Key)
   Status: new → analyzing
   ↓
4. Estratega propone acciones
   PUT /interno/alertas/{id}/propuesta (Estratega, X-Agent-Key)
   Status: analyzing → proposed
   ↓
5. [PAUSA] Humano decide
   POST /alertas/{id}/decision (gerente o lider_proceso)
   Status: proposed → approved OR rejected
   ↓
   (Si aprobada)
6. Ejecutor ejecuta la acción
   POST /interno/alertas/{id}/ejecutar (Ejecutor, X-Agent-Key)
   Status: approved → executed
   ↓
7. GET /bitacora?alertId=alerta_abc
   Muestra auditoría completa
```

## Dónde vive cada cosa

| Concepto | Dónde | Dueño |
|---|---|---|
| Reloj simulado | `api.simulacion.dia_actual` | `apps/api` |
| Alertas | `api.alertas` | `apps/api` |
| Auditoría | `api.bitacora` | `apps/api` |
| Datos transaccionales | `centinela.{clientes,pedidos,facturas,...}` | `data/sql/01_esquema.sql` |
| Métricas (vistas) | `centinela.v_*` | `data/sql/03_capa_semantica.sql` |
| Definición de umbrales | `data/metricas.yaml` | `data/` |
| Detectores | `packages/agents/Vigía` | Equipo de agents |
| Herramientas de consulta | `packages/tools/SQL` | Equipo de tools |

## Cómo los otros equipos usan esto

### packages/agents (Vigía, Analista, Estratega, Ejecutor)

```python
# 1. Obtener día simulado actual
dia_actual = requests.get(
    "http://api:8000/simulacion/dia-actual"
).json()["dia"]  # "2026-01-15"

# 2. Vigía: Llamar a tools/SQL para cada métrica
# (no se implementa en el API, está en packages/tools)
# tools_sql.query(
#   view="v_margen_semanal_linea",
#   filters={"semana <= '2026-01-15'"}
# )

# 3. Comparar con umbral (metricas.yaml)
if resultado["margen_pct"] < umbral:
    # Crear alerta
    requests.post(
        "http://api:8000/interno/alertas",
        json=AgentAlertInput(...),
        headers={
            "X-Agent": "vigia",
            "X-Agent-Key": "<secret>"
        }
    )
```

### packages/tools (MCP SQL server)

```python
# tools_reader conecta aquí:
import psycopg
conn = psycopg.connect(
    "postgresql://tools_reader:tools_reader_password@db:5432/centinela"
)

# Las consultas SIEMPRE incluyen el filtro de fecha simulada
# (recibido como parámetro de Vigía)
query = """
    SELECT * FROM centinela.v_margen_semanal_linea
    WHERE semana <= %s
"""
conn.execute(query, (fecha_maxima,))
```

### apps/web

```typescript
// Obtener alertas para mostrar en bandeja
GET /alertas?estado=propuesta
→ Alert[]

// Usuario decide
POST /alertas/{id}/decision
→ Alert (status=approved)

// Ver auditoría
GET /bitacora?alertId=...
→ LogEvent[]

// Avanzar el reloj (botón "Siguiente día")
POST /simulacion/avanzar?dias=1
→ {simulatedDay: "2026-01-15", newAlerts: [...]}
```

## Setup checklist

- [ ] `data/docker-compose.yml`: `docker compose up -d`
- [ ] `data/sql/01_esquema.sql`: crea `centinela` schema + `tools_reader` user
- [ ] `data/sql/02_carga.sql`: carga CSVs
- [ ] `data/sql/03_capa_semantica.sql`: crea vistas `v_*`
- [ ] `apps/api/.env`: `DSN_ADMIN=postgresql://centinela:centinela@db/centinela`
- [ ] `apps/api/.env`: `AGENT_SECRET_KEY=<secret>`
- [ ] `packages/tools/.env`: `DSN_READ_ONLY=postgresql://tools_reader:tools_reader_password@db/centinela`
- [ ] `apps/api`: `pip install -e .` + `uvicorn centinela_api.main:app`
- [ ] Swagger UI: http://localhost:8000/docs
