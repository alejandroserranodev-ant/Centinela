# Fase 2: Schemas y Validación ✅ COMPLETADA

## Archivos Creados

```
packages/agents/centinela_agents/
└── schema.py                   # Extendido con 8 nuevos schemas

tests/
└── test_schemas.py            # 40+ test cases para validación
```

## Nuevos Schemas (Pydantic)

### 1. **Figure** - Dato numérico o de texto con trazabilidad

```python
class Figure:
    value: int | float | str      # El valor (45, 2.5, "SKU-123")
    unit: str | None              # Unidad (COP, %, days, units, etc.)
    queryId: str                  # ID único de la query que la produjo
```

**Uso:** Toda cifra en Cause, Action, ExecutedAction viene envuelta en Figure.

```python
Figure(value=45, unit="days", queryId="q_dias_retraso_001")
```

---

### 2. **Evidence** - Pieza de evidencia que sostiene una causa

```python
class Evidence:
    claim: str                    # Texto en español (p.ej. "El cliente tiene {0} de retraso")
    figures: list[Figure]         # Figuras referenciadas por {0}, {1}, etc.
```

**Uso:** Una Evidence = un párrafo con datos que lo apoyan.

```python
evidence = Evidence(
    claim="El cliente tiene {0} sin realizar pagos",
    figures=[Figure(value=45, unit="days", queryId="q_dias")]
)
```

---

### 3. **Confidence** - Confianza en un resultado

```python
class Confidence:
    level: Literal["high", "medium", "low"]
    assumptions: list[str]        # Limitaciones, restricciones, datos parciales
```

**Reglas:**
- **high:** La causa pasa 3 tests en DOS vistas diferentes
- **medium:** Pasa 3 tests en UNA vista
- **low:** Pasa tests pero faltan datos o no hay fórmula

**Uso:**
```python
Confidence(
    level="high",
    assumptions=["Datos de últimos 6 meses"]
)
```

---

### 4. **Cause** - Explicación de por qué ocurrió la alerta

#### 4a. CauseIdentified
```python
class CauseIdentified:
    kind: Literal["identified"]
    sentence: str                 # "El cliente acumula retraso en pagos"
    evidence: list[Evidence]      # 1+ evidencias
    same_cause_as: str | None     # alert_id de otra alerta con misma causa
```

#### 4b. CauseNoEvidence
```python
class CauseNoEvidence:
    kind: Literal["no_evidence"]
    reason: str                   # "No se encontraron cambios que expliquen..."
    queriesReviewed: list[str]    # queryIds examinadas
```

#### Union Type
```python
Cause = CauseIdentified | CauseNoEvidence

# Analista devuelve una u otra:
output = CauseIdentified(...)  # o
output = CauseNoEvidence(...)
```

**Uso en LLM:**
```python
from centinela_agents.provider_factory import get_provider
from centinela_agents.llm_provider import LLMStructuredRequest
from centinela_agents.schema import Cause, CauseIdentified

provider = get_provider()

schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": ["identified", "no_evidence"]},
        "sentence": {"type": "string"},
        "evidence": {...},
        "reason": {...},
        ...
    }
}

request = LLMStructuredRequest(
    system_prompt="Eres Analista...",
    user_prompt="¿Por qué tiene 30 días de retraso el cliente?",
    schema=schema,
)

response = provider.generate_structured(request)
cause = CauseIdentified.model_validate(response.parsed)  # Validated!
```

---

### 5. **Action** - Acción propuesta por Estratega

```python
class Action:
    id: str                       # Unique within proposal (action_001, etc.)
    title: str                    # Título en español
    description: str              # Descripción + sección de política
    type: Literal[...]            # email_draft, task, purchase_order_draft, price_change_draft
    parameters: dict              # {cliente_id: "C123", vendedor_id: "V45", ...}
    impact: Figure | None         # Null si la métrica no tiene fórmula
    confidence: Confidence
```

**Tipos de acción:**
- `email_draft`: Borrador de email (Ejecutor redacta cuerpo)
- `task`: Tarea manual (Ejecutor crea nota)
- `purchase_order_draft`: Borrador de orden de compra
- `price_change_draft`: Borrador de cambio de precio

**Ejemplo:**
```python
action = Action(
    id="action_001",
    title="Recordatorio de pago",
    description="Email según FIN-POL-004 §4",
    type="email_draft",
    parameters={"recipient": "cliente_123", "vendedor_id": "vendedor_45"},
    impact=Figure(value=100000, unit="COP", queryId="q_saldo"),
    confidence=Confidence(level="high")
)
```

---

### 6. **ExecutedAction** - Resultado de ejecutar una acción aprobada

```python
class ExecutedAction:
    actionId: str                 # Links to Action.id
    type: str                     # Mismo tipo que Action
    result: str | dict            # Draft text o task details
    parameters: dict              # Exactly as approved (immutable)
```

**Ejemplo:**
```python
executed = ExecutedAction(
    actionId="action_001",
    type="email_draft",
    result="Estimado cliente,\n\nSu factura tiene 30 días de vencida...",
    parameters={"recipient": "cliente_123"}
)
```

---

### 7. **Decision** - Decisión humana (grabada por API)

```python
class Decision:
    kind: Literal["approve", "edit", "reject", "request_changes"]
    actionId: str | None          # Qué acción (para approve/edit)
    parameters: dict | None       # Nuevos valores (solo para edit)
    reason: str | None            # Por qué (para reject/request_changes)
```

**Flujos:**
- `approve`: Ejecuta acción tal cual
- `edit`: Ejecuta con parámetros modificados
- `reject`: Cierra alerta, rechaza la propuesta
- `request_changes`: Vuelve a Estratega (con razón)

**Ejemplo:**
```python
# Aprobar
Decision(kind="approve", actionId="action_001")

# Editar
Decision(
    kind="edit",
    actionId="action_001",
    parameters={"price_increase_pct": 3.0}
)

# Rechazar
Decision(
    kind="reject",
    reason="Los datos no son confiables"
)
```

---

### 8. **RejectionClassifierOutput** - Destino de un rechazo

```python
class RejectionClassifierOutput:
    destino: Literal["causa", "propuesta", "ambos", "ninguno"]
```

**Destinos:**
- `causa`: Analista lee el rechazo (error en explicación)
- `propuesta`: Estratega lee el rechazo (acción no apropiada)
- `ambos`: Ambos leen el rechazo
- `ninguno`: Queda en bitácora, sin acción

---

## Validación y Testing

### Run all schema tests
```bash
cd packages/agents
uv run pytest tests/test_schemas.py -v
```

### Run specific test class
```bash
uv run pytest tests/test_schemas.py::TestFigure -v
uv run pytest tests/test_schemas.py::TestSchemaIntegration -v
```

### Test count
- **Figure:** 6 tests
- **Evidence:** 4 tests
- **Cause (identified/no_evidence):** 10 tests
- **Confidence:** 2 tests
- **Action:** 4 tests
- **ExecutedAction:** 3 tests
- **Decision:** 4 tests
- **RejectionClassifier:** 5 tests
- **InsufficientCause:** 1 test
- **Integration:** 2 tests

**Total:** 41 test cases ✅

---

## Integración Provider + Schema

### Full Workflow: Analista produce Cause

```python
from centinela_agents.provider_factory import get_provider
from centinela_agents.llm_provider import LLMStructuredRequest
from centinela_agents.schema import CauseIdentified

provider = get_provider()  # Lee env

# Pydantic schema as JSON
schema = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "const": "identified"},
        "sentence": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "figures": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "value": {"type": ["number", "string"]},
                                "unit": {"type": ["string", "null"]},
                                "queryId": {"type": "string"}
                            },
                            "required": ["value", "queryId"]
                        }
                    }
                },
                "required": ["claim"]
            }
        },
        "same_cause_as": {"type": ["string", "null"]}
    },
    "required": ["kind", "sentence", "evidence"]
}

request = LLMStructuredRequest(
    system_prompt="""Eres Analista de Centinela. Explica por qué ocurrió la alerta.
    
Debes responder con JSON válido que cumpla el schema.""",
    user_prompt="""La alerta: cliente_123 tiene 45 días de retraso.
    
Analiza por qué sucede esto.""",
    schema=schema,
    thinking=True  # Extended thinking para reasoning
)

# LLM genera JSON estructurado
response = provider.generate_structured(request)

# Validate with Pydantic
cause = CauseIdentified.model_validate(response.parsed)

# Ahora es un objeto tipado, seguro
print(f"Causa: {cause.sentence}")
for evidence in cause.evidence:
    print(f"  - {evidence.claim}")
    for fig in evidence.figures:
        print(f"    Figure: {fig.value} {fig.unit} (query: {fig.queryId})")
```

---

## Decisiones de Diseño

### 1. Unión de tipos (Cause)
```python
Cause = CauseIdentified | CauseNoEvidence
```
- Pydantic 2.x soporta union discriminada (discriminator: "kind")
- Desambigua automáticamente según el campo `kind`

### 2. Figure con queryId
- **Trazabilidad:** Cada número apunta a su query
- **Auditoría:** Se puede reproducir el número corriendo la query
- **Seguridad:** No hay números inventados

### 3. Confidence no es Score
- No es 0-100 (opaco)
- Es nivel cualitativo + suposiciones (transparente)
- Expresa incertidumbre claramente

### 4. Action.impact = None válido
- No todas las acciones tienen fórmula (p.ej. `dias_pago_prom`)
- `null` es mejor que `0` (indica "no aplica", no "impacto cero")

### 5. Parameters como dict genérico
- Cada action type puede tener parámetros diferentes
- El schema es flexible (cliente_id, sku, owner, etc.)
- Validación ocurre en el nivel de ejecución (Ejecutor)

---

## Próximo Paso: Fase 3 (Tools Interface)

Schemas están listos. Ahora necesitamos **Tools** que Analista, Estratega y Ejecutor usen:

**Tools a implementar:**
- `sql_vistas()` - SQL read-only sobre vistas
- `buscar_politica()` - Búsqueda en políticas
- `calcular_impacto()` - Las 8 fórmulas
- Action tools: email_draft, task, purchase_order, price_change

Estimado: 3-4 horas (tools)
