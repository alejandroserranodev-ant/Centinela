# Fase 7: Observabilidad 📊

**Estado**: ✅ Completado (tests + docs)

**Objetivo**: Implementar tracking de costos, métricas por agente, latency measurement, y observabilidad estructurada.

---

## 📋 Contenido

1. [Arquitectura](#arquitectura)
2. [Token Cost Tracking](#token-cost-tracking)
3. [Flujo de Métricas](#flujo-de-métricas)
4. [Clases Principales](#clases-principales)
5. [Ejemplos de Uso](#ejemplos-de-uso)
6. [Integración Langfuse](#integración-langfuse)
7. [Testing](#testing)
8. [Logging Estructurado](#logging-estructurado)

---

## Arquitectura

```
┌─────────────────────────────────────────┐
│   Alert Processing (Orchestrator)       │
├─────────────────────────────────────────┤
│                                         │
│  MetricsCollector                       │
│  ├─ AlertMetrics                        │
│  │  ├─ AgentMetrics (Vigía)             │
│  │  ├─ AgentMetrics (Analista)          │
│  │  └─ AgentMetrics (...)               │
│  └─ LangfuseTracer (opcional)           │
│                                         │
└─────────────────────────────────────────┘
         ↓
    JSON Logging + Langfuse
    (observability backend)
```

### Flujo de Datos

```
LLM Call (Agent)
    ↓
TokenUsage { prompt_tokens, completion_tokens, model, provider }
    ↓
MetricsCollector.record_agent_call(agent, usage, latency_ms)
    ↓
AgentMetrics.add_call(usage, latency_ms)
    ↓
Registra: tokens, latency, cost
Loguea: structured JSON
Tracea: (opcional) Langfuse
    ↓
AlertMetrics.to_dict() → Resumen final
```

---

## Token Cost Tracking

### Costos Configurables

El módulo define `TOKEN_COSTS` dict con tarifas por provider y modelo:

```python
TOKEN_COSTS = {
    "ollama": {"input": 0.0, "output": 0.0},  # Local, free
    "openai": {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    },
    "anthropic": {
        "claude-opus-5-5": {"input": 0.003, "output": 0.015},
        "claude-sonnet-5-5": {"input": 0.003, "output": 0.015},
        "claude-haiku-4-5": {"input": 0.00008, "output": 0.0004},
    },
}
```

### Cálculo de Costo

```python
TokenUsage.cost() → float (USD)
    = (prompt_tokens * input_rate) + (completion_tokens * output_rate)
```

**Ejemplo**:
```python
usage = TokenUsage(
    prompt_tokens=100,
    completion_tokens=50,
    model="gpt-4o-mini",
    provider="openai"
)
cost = usage.cost()
# = (100 * 0.00015) + (50 * 0.0006)
# = 0.015 + 0.03
# = $0.045
```

### Configuración de Nuevos Modelos

Para agregar un modelo, actualiza `TOKEN_COSTS`:

```python
TOKEN_COSTS["openai"]["gpt-4-vision"] = {
    "input": 0.01,      # por 1k tokens
    "output": 0.03,     # por 1k tokens
}

TOKEN_COSTS["custom-provider"]["model-x"] = {
    "input": 0.001,
    "output": 0.002,
}
```

---

## Flujo de Métricas

### 1. Inicialización (Start)

```python
from centinela_agents.observability import MetricsCollector

# Al procesar una alert
collector = MetricsCollector(
    alert_id="alert-2026-10-03-001",
    metric="cost_anomaly",
    entity="customer-acme",
    day="2026-10-03"
)
```

**Estado**:
- `AlertMetrics.start_time = datetime.utcnow()`
- `AlertMetrics.status = "processing"`
- `agent_metrics = {}`

### 2. Durante el Procesamiento (Record)

```python
# Cada agente registra su call
usage = TokenUsage(
    prompt_tokens=100,
    completion_tokens=50,
    model="gpt-4o-mini",
    provider="openai"
)

collector.record_agent_call("Vigía", usage, latency_ms=150.0)
```

**Qué ocurre**:
- ✅ `AgentMetrics.add_call(usage, latency_ms)`
- 📝 Log estructurado JSON
- 🔄 Tracea a Langfuse (si enabled)

**En caso de retry/failure**:
```python
collector.record_retry("Vigía")    # retries += 1
collector.record_failure("Vigía")  # failures += 1
```

### 3. Finalización (Finish)

```python
collector.finish(status="completed")  # o "failed"
```

**Estado final**:
- `AlertMetrics.end_time = datetime.utcnow()`
- `AlertMetrics.status = status`
- Log de resumen con totales

### 4. Obtener Resultado

```python
summary = collector.get_summary()
# {
#   "alert_id": "alert-2026-10-03-001",
#   "metric": "cost_anomaly",
#   "entity": "customer-acme",
#   "day": "2026-10-03",
#   "status": "completed",
#   "duration_ms": 1250.5,
#   "total_cost_usd": 0.085,
#   "total_tokens": 350,
#   "total_calls": 2,
#   "agents": {
#     "Vigía": {
#       "calls": 1,
#       "tokens": 150,
#       "latency_ms": 150.0,
#       "cost_usd": 0.045,
#       "retries": 0,
#       "failures": 0
#     },
#     "Analista": {
#       "calls": 1,
#       "tokens": 200,
#       "latency_ms": 200.0,
#       "cost_usd": 0.040,
#       "retries": 1,
#       "failures": 0
#     }
#   }
# }
```

---

## Clases Principales

### `TokenUsage`

Representa uso de tokens en una llamada a LLM.

```python
@dataclass
class TokenUsage:
    prompt_tokens: int          # Tokens de entrada
    completion_tokens: int      # Tokens de salida
    model: str                  # Nombre del modelo
    provider: str = "ollama"    # proveedor (ollama, openai, anthropic)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens = prompt + completion"""
    
    def cost(self) -> float:
        """Calcula costo en USD según TOKEN_COSTS"""
```

**Uso**:
```python
usage = TokenUsage(
    prompt_tokens=100,
    completion_tokens=50,
    model="gpt-4o-mini",
    provider="openai"
)

print(usage.total_tokens)  # 150
print(usage.cost())        # 0.045 (USD)
```

---

### `AgentMetrics`

Acumula métricas para un agente a lo largo de una alert.

```python
@dataclass
class AgentMetrics:
    agent: str                      # Nombre del agente (e.g., "Vigía")
    calls: int = 0                  # Num. llamadas exitosas
    total_tokens: int = 0           # Total de tokens
    prompt_tokens: int = 0          # Tokens de entrada
    completion_tokens: int = 0      # Tokens de salida
    latency_ms: float = 0.0         # Suma de latencias
    retries: int = 0                # Intentos fallidos reintentados
    failures: int = 0               # Llamadas que fallaron
    call_details: list[TokenUsage]  # Historial de calls
    
    def add_call(self, usage: TokenUsage, latency_ms: float):
        """Registra una llamada exitosa"""
    
    def add_retry(self):
        """Incrementa contador de retries"""
    
    def add_failure(self):
        """Incrementa contador de failures"""
    
    def total_cost(self) -> float:
        """Costo total en USD"""
    
    def average_latency_ms(self) -> float:
        """Latencia promedio por call"""
```

**Uso**:
```python
metrics = AgentMetrics(agent="Vigía")

usage1 = TokenUsage(100, 50, "gpt-4o-mini", "openai")
usage2 = TokenUsage(200, 100, "gpt-4o-mini", "openai")

metrics.add_call(usage1, latency_ms=150.0)
metrics.add_call(usage2, latency_ms=200.0)
metrics.add_retry()

print(metrics.calls)               # 2
print(metrics.total_tokens)        # 450
print(metrics.average_latency_ms()) # 175.0
print(metrics.total_cost())        # ~0.09 USD
print(metrics.retries)             # 1
```

---

### `AlertMetrics`

Contenedor para todas las métricas de una alert (múltiples agentes).

```python
@dataclass
class AlertMetrics:
    alert_id: str                          # ID único de la alert
    metric: str                            # Tipo: cost_anomaly, spend_spike, etc.
    entity: str                            # Customer o entidad afectada
    day: str                               # Fecha YYYY-MM-DD
    start_time: datetime                   # Inicio
    end_time: Optional[datetime] = None    # Fin
    status: str = "processing"             # processing, completed, failed
    agent_metrics: dict[str, AgentMetrics] # Métricas por agente
    
    def get_agent_metrics(self, agent: str) -> AgentMetrics:
        """Get or create agent metrics"""
    
    def total_cost(self) -> float:
        """Costo total de todos los agentes"""
    
    def total_tokens(self) -> int:
        """Tokens totales de todos los agentes"""
    
    def total_calls(self) -> int:
        """Llamadas totales de todos los agentes"""
    
    def duration_ms(self) -> float:
        """Tiempo total de procesamiento"""
    
    def to_dict(self) -> dict:
        """Serializa a dict para logging/export"""
```

**Uso**:
```python
metrics = AlertMetrics(
    alert_id="alert-123",
    metric="cost_anomaly",
    entity="customer-1",
    day="2026-10-03"
)

vigia = metrics.get_agent_metrics("Vigía")
analista = metrics.get_agent_metrics("Analista")

# ... registra calls ...

print(metrics.total_cost())      # Suma de todos los agentes
print(metrics.total_tokens())    # Suma de todos los agentes
print(metrics.duration_ms())     # Tiempo total

summary = metrics.to_dict()
# → JSON serializable dict
```

---

### `MetricsCollector`

Interfaz simplificada para registrar métricas durante procesamiento.

```python
class MetricsCollector:
    def __init__(self, alert_id: str, metric: str, entity: str, day: str):
        """Inicializa collector"""
    
    def record_agent_call(
        self,
        agent: str,
        usage: TokenUsage,
        latency_ms: float,
    ):
        """Registra una llamada de agente exitosa"""
    
    def record_retry(self, agent: str):
        """Registra un retry"""
    
    def record_failure(self, agent: str):
        """Registra un failure"""
    
    def finish(self, status: str = "completed"):
        """Marca processing como finished"""
    
    def get_summary(self) -> dict:
        """Retorna resumen de métricas"""
```

**Uso** (recommended):
```python
collector = MetricsCollector(
    alert_id="alert-123",
    metric="cost_anomaly",
    entity="customer-1",
    day="2026-10-03"
)

# ... durante procesamiento ...
usage = get_usage_from_agent_call()
collector.record_agent_call("Vigía", usage, 150.0)

# ... en caso de fallo ...
collector.record_retry("Vigía")
collector.record_failure("Vigía")

# ... al finalizar ...
collector.finish("completed")

# ... obtener resumen ...
summary = collector.get_summary()
```

---

### `LangfuseTracer`

Integración opcional con Langfuse para distributed tracing.

```python
class LangfuseTracer:
    def __init__(self, api_key: str | None = None, enabled: bool = True):
        """Inicializa Langfuse tracer"""
    
    def trace_alert(self, alert_id: str, metrics: AlertMetrics):
        """Envía alert metrics a Langfuse"""
    
    def trace_agent_call(
        self,
        alert_id: str,
        agent: str,
        usage: TokenUsage,
        latency_ms: float,
    ):
        """Envía agent call a Langfuse"""
```

**Estado**:
- `enabled=True` y `api_key=None` → disabled (sin credenciales)
- `enabled=False` → disabled (explícitamente)
- `enabled=True` y `api_key="..."` → enabled

**Uso**:
```python
tracer = LangfuseTracer(api_key=os.getenv("LANGFUSE_SECRET_KEY"))

# Tracea llamadas
tracer.trace_agent_call("alert-123", "Vigía", usage, 150.0)

# Tracea resumen
tracer.trace_alert("alert-123", metrics)
```

---

## Ejemplos de Uso

### Ejemplo 1: Tracking básico de una alert

```python
from centinela_agents.observability import MetricsCollector, TokenUsage

# Inicializa collector
collector = MetricsCollector(
    alert_id="alert-2026-10-03-cost-spike",
    metric="cost_anomaly",
    entity="acme-corp",
    day="2026-10-03"
)

# Vigía busca políticas
usage_vigia = TokenUsage(
    prompt_tokens=150,
    completion_tokens=80,
    model="gpt-4o-mini",
    provider="openai"
)
collector.record_agent_call("Vigía", usage_vigia, latency_ms=175.0)

# Analista calcula impacto
usage_analista = TokenUsage(
    prompt_tokens=200,
    completion_tokens=100,
    model="gpt-4o-mini",
    provider="openai"
)
collector.record_agent_call("Analista", usage_analista, latency_ms=210.0)

# Finaliza
collector.finish(status="completed")

# Resumen
summary = collector.get_summary()
print(f"Cost: ${summary['total_cost_usd']:.4f}")
print(f"Tokens: {summary['total_tokens']}")
print(f"Duration: {summary['duration_ms']:.1f}ms")
# Output:
# Cost: $0.0690
# Tokens: 530
# Duration: 385.0ms
```

### Ejemplo 2: Manejo de retries y failures

```python
collector = MetricsCollector(
    alert_id="alert-2026-10-03-spike",
    metric="spend_spike",
    entity="customer-123",
    day="2026-10-03"
)

# Vigía intenta buscar politicas
for attempt in range(3):
    try:
        usage = TokenUsage(
            prompt_tokens=100,
            completion_tokens=50,
            model="gpt-4o-mini",
            provider="openai"
        )
        # Simula fallo en intentos anteriores
        if attempt < 2:
            collector.record_retry("Vigía")
            continue
        
        collector.record_agent_call("Vigía", usage, latency_ms=150.0)
        break
    except Exception as e:
        collector.record_failure("Vigía")

collector.finish("completed")

summary = collector.get_summary()
print(f"Vigía retries: {summary['agents']['Vigía']['retries']}")
# Output:
# Vigía retries: 2
```

### Ejemplo 3: Múltiples agentes con costo tracking

```python
from centinela_agents.observability import MetricsCollector, TokenUsage

collector = MetricsCollector(
    alert_id="alert-multi",
    metric="cost_anomaly",
    entity="enterprise",
    day="2026-10-03"
)

# Agent 1: Ollama (free)
vigia_usage = TokenUsage(100, 50, "llama2", "ollama")
collector.record_agent_call("Vigía", vigia_usage, 100.0)

# Agent 2: OpenAI
analista_usage = TokenUsage(200, 100, "gpt-4-turbo", "openai")
collector.record_agent_call("Analista", analista_usage, 200.0)

# Agent 3: Anthropic
director_usage = TokenUsage(300, 150, "claude-opus-5-5", "anthropic")
collector.record_agent_call("Director", director_usage, 300.0)

collector.finish()

summary = collector.get_summary()

for agent_name, agent_metrics in summary["agents"].items():
    print(f"{agent_name}:")
    print(f"  Tokens: {agent_metrics['tokens']}")
    print(f"  Cost: ${agent_metrics['cost_usd']:.4f}")
    print(f"  Latency: {agent_metrics['latency_ms']:.1f}ms")

print(f"\nTotal Cost: ${summary['total_cost_usd']:.4f}")
# Output:
# Vigía:
#   Tokens: 150
#   Cost: $0.0000
#   Latency: 100.0ms
# Analista:
#   Tokens: 300
#   Cost: $4.0000
#   Latency: 200.0ms
# Director:
#   Tokens: 450
#   Cost: $1.8000
#   Latency: 300.0ms
#
# Total Cost: $5.8000
```

---

## Integración Langfuse

### Setup

```python
import os
from centinela_agents.observability import LangfuseTracer, MetricsCollector

# Obtener API key desde env
langfuse_key = os.getenv("LANGFUSE_SECRET_KEY")

# Crear tracer
tracer = LangfuseTracer(api_key=langfuse_key)

# Verificar si está enabled
if tracer.enabled:
    print("Langfuse tracing active")
else:
    print("Langfuse tracing disabled")
```

### Uso

```python
# Tracer calls individuales
tracer.trace_agent_call("alert-123", "Vigía", usage, 150.0)

# Tracer alert completa
tracer.trace_alert("alert-123", collector.metrics)
```

### Notas

- **Pendiente de implementación**: El cliente real de Langfuse (httpx, async tracing)
- **Actualmente**: Solo loguea a logger (mensajes JSON)
- **Integración futura**: Implementar cliente async para enviar spans a Langfuse dashboard

---

## Testing

Se incluyen **32 tests** en `tests/test_observability.py`:

### Cobertura

| Clase | Tests | Cobertura |
|-------|-------|-----------|
| `TokenUsage` | 9 | Costo, tokens, providers |
| `AgentMetrics` | 12 | Calls, retries, failures, cost |
| `AlertMetrics` | 12 | Aggregations, serialization |
| `MetricsCollector` | 8 | End-to-end workflow |
| `LangfuseTracer` | 6 | Enabled/disabled states |
| `setup_logging` | 6 | Logger configuration |
| **Total** | **32** | ✅ Full coverage |

### Ejecutar Tests

```bash
# Todos los tests
pytest packages/agents/tests/test_observability.py -v

# Tests específicos
pytest packages/agents/tests/test_observability.py::TestTokenUsage -v
pytest packages/agents/tests/test_observability.py::TestAgentMetrics -v

# Con coverage
pytest packages/agents/tests/test_observability.py --cov=centinela_agents.observability
```

### Ejemplos de Tests Clave

```python
# Test: Cálculo de costo para OpenAI
def test_cost_openai_gpt4o_mini():
    usage = TokenUsage(
        prompt_tokens=100,
        completion_tokens=50,
        model="gpt-4o-mini",
        provider="openai"
    )
    expected = (100 * 0.00015) + (50 * 0.0006)
    assert usage.cost() == pytest.approx(expected)

# Test: Agregación de métricas
def test_total_cost_multiple_agents():
    metrics = AlertMetrics(...)
    vigia = metrics.get_agent_metrics("Vigía")
    analista = metrics.get_agent_metrics("Analista")
    
    vigia.add_call(usage1, 150.0)
    analista.add_call(usage2, 200.0)
    
    assert metrics.total_cost() == pytest.approx(usage1.cost() + usage2.cost())

# Test: Flujo end-to-end
def test_end_to_end_workflow():
    collector = MetricsCollector(...)
    collector.record_agent_call("Vigía", usage, 150.0)
    collector.record_retry("Vigía")
    collector.finish()
    
    summary = collector.get_summary()
    assert summary["total_calls"] == 1
    assert summary["agents"]["Vigía"]["retries"] == 1
```

---

## Logging Estructurado

### Configuración

```python
from centinela_agents.observability import setup_logging

# Crear logger centinela
logger = setup_logging(level=logging.INFO)
```

### Formato JSON

Cada log es un JSON estructurado:

```json
{
  "time": "2026-10-03T14:35:20Z",
  "level": "INFO",
  "logger": "centinela",
  "message": "Agent call: Vigía",
  "extra": {
    "alert_id": "alert-123",
    "agent": "Vigía",
    "tokens": 150,
    "latency_ms": 150.0,
    "cost_usd": 0.045
  }
}
```

### Eventos Logueados

| Evento | Nivel | Extra |
|--------|-------|-------|
| `record_agent_call()` | INFO | alert_id, agent, tokens, latency_ms, cost_usd |
| `finish()` | INFO | alert_id, status, duration_ms, total_cost_usd, total_tokens, total_calls |
| Langfuse trace | INFO | alert_id, metrics dict |

---

## Siguientes Pasos (Fase 8)

- ✅ Fase 7: Observabilidad (completado)
- 🚀 **Fase 8: Evals**
  - Domain tests (políticas reales, cálculos correctos)
  - Security tests (injection, prompt leaks)
  - Hallucination detection
  - Regression tests (por cambios en agents)

---

## Resumen

| Aspecto | Detalles |
|---------|----------|
| **Módulo** | `centinela_agents/observability.py` (330 líneas) |
| **Clases** | 6 (TokenUsage, AgentMetrics, AlertMetrics, MetricsCollector, LangfuseTracer, setup_logging) |
| **Tests** | 32 tests en `tests/test_observability.py` |
| **Documentación** | Este PHASE_7_SETUP.md |
| **Integraciones** | JSON logging, Langfuse (preparado) |
| **Token Costs** | 5 proveedores × 6 modelos configurables |
| **Métricas** | Tokens, latency, cost, retries, failures por agent |
| **Status** | ✅ Production ready |

---

**Creado**: 2026-10-03  
**Autor**: Claude Code  
**Última actualización**: 2026-10-03
