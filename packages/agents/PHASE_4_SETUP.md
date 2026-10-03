# Fase 4: Agentes ✅ COMPLETADA

## Archivos Creados

```
packages/agents/centinela_agents/agents/
├── __init__.py              # Package definition
├── vigia.py                 # Redacción de título
├── analista.py              # Explicar causas
├── estratega.py             # Proponer acciones
├── ejecutor.py              # Ejecutar acciones aprobadas
└── orquestador.py           # Clasificar rechazos

tests/
└── test_agents.py          # 14 test cases
```

## 5 Agentes Implementados

### 1. **Vigía: redact_title()**

Redacta título de alerta detectada (una frase en español).

```python
def redact_title(provider, detection) -> {title: Sentence, error}
```

**Input:** detection (metric, entity, cifra, severity)  
**Output:** Sentence with text + figures  
**Model:** LLM thinking OFF (simple redaction)  
**Fallback:** metric.descripcion + entity

---

### 2. **Analista: explain_cause()**

Explica por qué ocurrió la alerta usando datos y políticas.

```python
def explain_cause(provider, alert, tools) -> {cause: Cause, error}
```

**Input:** alert + cause_rejections + earlier_alerts  
**Output:** CauseIdentified (sentence + evidence) OR CauseNoEvidence  
**Model:** LLM thinking ON (reasoning required)  
**Tools:** sql_vistas, buscar_politica  
**Fallback:** no_evidence con reason de error

---

### 3. **Estratega: propose_actions()**

Propone 1-3 acciones para la alerta.

```python
def propose_actions(provider, alert, cause, tools) -> {actions, insufficient_cause, error}
```

**Input:** alert + cause + proposal_rejections  
**Output:** list[Action] (1-3) OR insufficient_cause=True  
**Model:** LLM thinking ON (reasoning required)  
**Tools:** sql_vistas, buscar_politica, calcular_impacto  
**Fallback:** insufficient_cause → manual review

---

### 4. **Ejecutor: execute_action()**

Ejecuta una acción aprobada.

```python
def execute_action(provider, action, decision, tools) -> {executed_action, error}
```

**Input:** approved action + decision (approve/edit)  
**Output:** ExecutedAction (draft o task)  
**Model:** LLM thinking OFF (solo para email body)  
**Tools:** action tools (email_draft, task, po, price_change)  
**Code:** Crea drafts/tasks, no ejecuta realmente

---

### 5. **Orquestador: classify_rejection()**

Clasifica a dónde va un rechazo.

```python
def classify_rejection(provider, reason, cause, actions) -> {destino, error}
```

**Input:** rejection reason (string) + cause + actions  
**Output:** destino ("causa" | "propuesta" | "ambos" | "ninguno")  
**Model:** LLM thinking OFF (simple classification)  
**Fallback:** ninguno (queda en log)

---

## Uso en Orquestador

```python
from centinela_agents.agents.vigia import redact_title
from centinela_agents.agents.analista import explain_cause
from centinela_agents.agents.estratega import propose_actions
from centinela_agents.agents.ejecutor import execute_action
from centinela_agents.agents.orquestador import classify_rejection
from centinela_agents.provider_factory import get_provider
from centinela_agents.tools import ToolRegistry

provider = get_provider()  # Lee env
tools = ToolRegistry(...)  # Con providers reales

# Flujo completo
detection = {...}
result_title = redact_title(provider, detection)

alert = {**detection, **result_title}
result_cause = explain_cause(provider, alert, tools)

result_actions = propose_actions(
    provider, 
    alert, 
    result_cause["cause"],
    tools
)

# Si aprobado:
decision = {kind: "approve", actionId: "a1"}
result_execution = execute_action(
    provider,
    result_actions["actions"][0],
    decision,
    tools
)

# Si rechazado:
reject_reason = "No me parece bien"
result_classify = classify_rejection(
    provider,
    reject_reason,
    result_cause["cause"],
    result_actions["actions"]
)
```

---

## Testing (14 test cases)

```bash
cd packages/agents
uv run pytest tests/test_agents.py -v
```

- **Vigía:** 2 tests (success, fallback)
- **Analista:** 3 tests (identified, no_evidence, fallback)
- **Estratega:** 3 tests (success, no_evidence, fallback)
- **Ejecutor:** 2 tests (task, email_draft)
- **Orquestador:** 4 tests (causa, propuesta, ninguno, fallback)

**Total:** 14 test cases ✅

---

## Design Decisions

### 1. Agents as Pure Functions
- No state (stateless)
- Provider + tools injected
- Testable without orchestrator
- Easy to mock for testing

### 2. Error Handling
- Try/catch all LLM calls
- Fallback to safe defaults (no_evidence, ninguno, manual review)
- Errors logged but not fatal

### 3. LLM Thinking Mode
- **Thinking ON:** Analista, Estratega (reasoning required)
- **Thinking OFF:** Vigía, Ejecutor, Orquestador (deterministic)

### 4. Schema-Constrained Output
- All LLM outputs validated with Pydantic
- Invalid schema → fallback (no_evidence, insufficient_cause, ninguno)

### 5. Data Pre-Masking
- Ejecutor gets pre-masked data for email body
- No sensitive data in LLM calls
- IDs only (cliente_123, not "Juan García")

---

## Real Implementation Notes

### Vigía
- Stub returns text as-is
- Real: integra con walk.py para obtener detection completo

### Analista
- Stub: no queries ejecutadas
- Real: sql_tool.query() ejecuta queries de skill/analista/<metric>.md
- Real: policy_tool.search() busca en políticas

### Estratega
- Stub: no impact calculated
- Real: impact_tool.calculate() usa 8 fórmulas
- Real: Valida acciones contra acciones.md (cerrada)

### Ejecutor
- Stub: crea drafts sin herramientas
- Real: tools.email_draft, task, etc. interactúan con backend
- Real: idempotencia por alert_id + action_id + decision_id

### Orquestador
- Stub: siempre llama LLM
- Real: podría tener lógica heurística (sin LLM)
- Real: output es determinista (4 destinos únicos)

---

## Próximo Paso: Fase 5 (Orquestador LangGraph)

Agentes están listos como funciones puras.
Ahora compilamos el árbol de decisiones a un **grafo LangGraph** que:

1. Camina el árbol (base.yaml)
2. Llama agentes en los nodos correctos
3. Pausa en `aprobar.decision` para decisión humana
4. Resume con decisión de API
5. Maneja loops (análisis retorna, recargas de propuesta)

**Archivos a crear:**
- `graph.py` - Compilador de árbol a LangGraph (extensión)
- Tests de routing

Estimado: 3-4 horas (grafo + tests)
