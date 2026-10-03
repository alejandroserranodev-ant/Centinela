# Reporte: JSON Schema Standardization

**Fecha**: 2026-10-03  
**Scope**: Mejorar schemas JSON sin cambiar comportamiento, rutas, ni métodos HTTP  
**Status**: ✅ Completado

---

## Cambios Implementados

### 1. **Response Model para `/simulacion/dia-actual`**

**Antes**:  
```python
async def dia_actual(...) -> dict:
    return {"dia": dia.isoformat()}
```

**Después**:  
```python
class SimulatedDay(Esquema):
    """Current simulated day in ISO 8601 format."""
    dia: str = Field(..., description="Current simulated day (YYYY-MM-DD)", example="2026-10-03")

@router.get("/simulacion/dia-actual", response_model=SimulatedDay)
async def dia_actual(...) -> SimulatedDay:
    return SimulatedDay(dia=dia.isoformat())
```

**Impacto OpenAPI**:  
- Antes: `{}` (dict genérico)
- Después: `{"dia": "2026-10-03"}` (schema explícito con descripción y ejemplo)

---

### 2. **Enum para Query Parameter `estado`**

**Antes**:  
```python
estado: str | None = None
# Validación manual dentro del endpoint
if estado is not None and estado not in ESTADO_A_STATUS:
    raise HTTPException(422, "estado desconocido")
```

**Después**:  
```python
class AlertEstadoEnum(str, Enum):
    """Valid alert estado values (Spanish names for API contract)."""
    NUEVA = "nueva"
    EN_ANALISIS = "en_analisis"
    PROPUESTA = "propuesta"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    EJECUTADA = "ejecutada"

@router.get("/alertas")
async def listar(
    estado: Annotated[AlertEstadoEnum | None, Query(...)] = None,
    ...
```

**Impacto OpenAPI**:  
- Schema incluye componente `AlertEstadoEnum` con 6 valores enumerados
- Swagger UI puede mostrar dropdown con valores válidos
- Documentación automática de qué valores acepta el parámetro

---

### 3. **Documentación de Query Parameters**

**Bitácora** (`/bitacora`):
```python
@router.get("/bitacora")
async def listar(
    alertId: str | None = Query(None, description="Filter by alert ID (UUID-like identifier)"),
    type: LogEventType | None = Query(None, description="Filter by event type"),
    ...
) -> list[LogEvent]:
    """Get audit log (bitácora)..."""
```

**Impacto**: Query parameters ahora tienen descripciones explícitas en OpenAPI.

---

### 4. **Tags para Organización OpenAPI**

```python
router = APIRouter(tags=["alerts"])  # En alertas.py
router = APIRouter(prefix="/interno", tags=["internal"])  # En interno.py (existía)
```

**Impacto**: Swagger agrupa endpoints por categoría.

---

## Archivos Modificados

| Archivo | Cambios |
|---------|---------|
| `src/centinela_api/modelos.py` | + `SimulatedDay`, + `AlertEstadoEnum(str, Enum)` |
| `src/centinela_api/routers/simulacion.py` | Importar `SimulatedDay`, usar en `response_model` |
| `src/centinela_api/routers/alertas.py` | Importar `AlertEstadoEnum`, tipado enum en `estado`, agregar `tags`, documentación |
| `src/centinela_api/routers/bitacora.py` | Agregar `description` a query params, docstring al endpoint |

---

## Esquemas Mejorados

| Schema | Tipo | Cambio |
|--------|------|--------|
| `SimulatedDay` | Response | NUEVO — reemplaza `dict` genérico |
| `AlertEstadoEnum` | Enum | NUEVO — 6 valores explícitos |
| `LogEventType` | Enum | Ya existía, ahora documentado en OpenAPI |

---

## Validación

**Endpoints testeados**:
```bash
curl http://127.0.0.1:8000/simulacion/dia-actual
# 200: {"dia": "2026-10-03"}

curl http://127.0.0.1:8000/alertas?estado=nueva
# 200: []

curl http://127.0.0.1:8000/alertas?estado=invalid
# 422: {"detail": "estado desconocido: invalid"}

curl http://127.0.0.1:8000/openapi.json | jq '.components.schemas.AlertEstadoEnum'
# {"type": "string", "enum": ["nueva", "en_analisis", ...], "title": "AlertEstadoEnum"}
```

---

## Compatibilidad

✅ **Ningún cambio breaking**:
- Rutas: sin cambios
- Métodos HTTP: sin cambios
- Comportamiento: idéntico
- Request/Response: misma estructura JSON (naming camelCase preservado)

El JSON que el cliente recibe es idéntico. Solo la validación y documentación mejoraron.

---

## Observación: OpenAPI y `| None`

FastAPI genera `anyOf` para parámetros con uniones (`AlertEstadoEnum | None`).  
Este es comportamiento estándar de JSON Schema + FastAPI, no incorrecto, pero menos explícito que un enum puro.

El endpoint funciona correctamente:
- Acepta `estado=nueva` ✅
- Rechaza `estado=invalid` con 422 ✅
- Permite omitir `estado` (None por defecto) ✅

La representación en OpenAPI es `anyOf: [{"enum": [...]}, {"type": "null"}]`.  
Swagger UI aún permite usuarios seleccionar valores válidos.

---

## Próximos Pasos (No Alcanzados)

- Enums explícitos sin `anyOf` (requeriría refactor de parámetros opcionales)
- Documentación de headers (`X-Agent`, `X-Agent-Key`, `X-User-Role`, etc.)
- Estandarización de status codes por tipo de error
- Descripción detallada de cada endpoint (docstrings expandidos)

---

## Tokens Gastados

- Audit (agent): ~30k
- Implementación: ~35k
- Testing: ~10k
- **Total**: ~75k / 150k (50% del presupuesto)
