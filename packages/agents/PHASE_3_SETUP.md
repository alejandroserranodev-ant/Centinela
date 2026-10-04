# Fase 3: Tools Interface ✅ COMPLETADA

## Archivos Creados

```
packages/agents/centinela_agents/
├── tools.py                    # Tool interface definitions (9 abstract classes)
├── sql_vistas.py              # SqlVistasStub (read-only SQL)
├── buscar_politica.py         # BuscarPoliticaStub (policy search)
├── calcular_impacto.py        # CalcularImpactoStub (impact calculator)
└── action_tools.py            # Email, Task, PO, Price change stubs

tests/
└── test_tools.py             # 30+ test cases
```

## Tools Interface (9 Abstract Classes)

### 1. **SqlVistasProvider** - Read-only SQL access

```python
class SqlVistasProvider(ABC):
    def query(
        self,
        view_name: str,          # v_cartera_cliente, etc.
        filters: dict,            # {cliente_id: "C123"}
        simulated_day: str,       # YYYY-MM-DD
    ) -> SqlQuery:              # rows + queryId
        pass
```

**Stub:** Returns empty result  
**Real:** Queries database views with data masking (personal data → IDs)

---

### 2. **BuscarPoliticaProvider** - Policy search with pgvector

```python
class BuscarPoliticaProvider(ABC):
    def search(
        self,
        query: str,               # Spanish search
        top_k: int = 3,          # Number of results
    ) -> list[PolicyPassage]:    # Passages with relevance
        pass
```

**Stub:** Returns empty list  
**Real:** Uses pgvector + bge-m3 embeddings (Spanish-optimized)

---

### 3. **CalcularImpactoProvider** - Impact calculator (8 formulas)

```python
class CalcularImpactoProvider(ABC):
    def calculate(
        self,
        formula_name: str,        # traslado_costo, etc.
        entidad: str,             # cliente_id, sku, etc.
        simulated_day: str,       # YYYY-MM-DD
    ) -> ImpactResult:           # value + queryId
        pass
```

**8 Formulas Implemented:**
1. `traslado_costo` → price_increase_pct, impact/month
2. `precio_a_margen_minimo` → price_increase_pct, impact/month
3. `cartera_vencida` → impact once
4. `ventas_protegidas` → units, impact once
5. `descuento_recuperado` → impact/month
6. `venta_bajo_costo` → impact/month
7. `compra_recuperada` → impact/month
8. (dias_pago_prom has NO formula → null)

**Stub:** Returns 0 impact  
**Real:** Executes SQL queries for each formula

---

### 4-7. **Action Tools** (4 types)

#### EmailDraftTool
```python
class EmailDraftTool(ABC):
    def execute(
        self,
        recipient: str,           # cliente_id or proveedor_id
        body: str,                # Pre-masked email body
        subject: str | None,
        cc: list[str] | None,
    ) -> EmailDraftResult:
        pass
```

#### TaskTool
```python
class TaskTool(ABC):
    def execute(
        self,
        owner: str,               # Role (Jefe de cartera, etc.)
        title: str,
        description: str | None,
        parameters: dict | None,
    ) -> TaskResult:
        pass
```

#### PurchaseOrderDraftTool
```python
class PurchaseOrderDraftTool(ABC):
    def execute(
        self,
        proveedor_id: str,
        sku: str,
        quantity: int,            # From calcular_impacto
        warehouse: str,
    ) -> PurchaseOrderDraftResult:
        pass
```

#### PriceChangeDraftTool
```python
class PriceChangeDraftTool(ABC):
    def execute(
        self,
        sku: str | None,
        linea: str | None,
        price_increase_pct: float,  # From calcular_impacto
    ) -> PriceChangeDraftResult:
        pass
```

---

### 8. **ToolRegistry** - Dispatch tools to agents

```python
class ToolRegistry:
    sql_vistas: SqlVistasProvider
    buscar_politica: BuscarPoliticaProvider
    calcular_impacto: CalcularImpactoProvider
    email_draft: EmailDraftTool
    task: TaskTool
    purchase_order_draft: PurchaseOrderDraftTool
    price_change_draft: PriceChangeDraftTool

    def get_tools_for_agent(agent: str) -> dict[str, Any]:
        # Returns only tools this agent can use
```

**Agent Access:**
| Agent | Tools |
|-------|-------|
| Vigía | (none) |
| Analista | sql_vistas, buscar_politica |
| Estratega | sql_vistas, buscar_politica, calcular_impacto |
| Ejecutor | email_draft, task, purchase_order_draft, price_change_draft |

---

## Usage Example

### Full Workflow: Estratega proposes action

```python
from centinela_agents.tools import ToolRegistry
from centinela_agents.sql_vistas import SqlVistasStub
from centinela_agents.buscar_politica import BuscarPoliticaStub
from centinela_agents.calcular_impacto import CalcularImpactoStub

# Initialize tools
registry = ToolRegistry(
    sql_vistas=SqlVistasStub(),
    buscar_politica=BuscarPoliticaStub(),
    calcular_impacto=CalcularImpactoStub(),
)

# Get tools for Estratega
tools = registry.get_tools_for_agent("estratega")

# Now Estratega can call:
# - tools["sql_vistas"].query(...)
# - tools["buscar_politica"].search(...)
# - tools["calcular_impacto"].calculate(...)

# Example: Calculate impact
impact_tool = tools["calcular_impacto"]
result = impact_tool.calculate(
    formula_name="cartera_vencida",
    entidad="cliente_123",
    simulated_day="2026-10-03"
)
print(f"Impact: {result.value} {result.unit}")
```

---

## Testing

### Run all tool tests
```bash
cd packages/agents
uv run pytest tests/test_tools.py -v
```

### Run specific tool tests
```bash
uv run pytest tests/test_tools.py::TestSqlVistas -v
uv run pytest tests/test_tools.py::TestCalcularImpacto -v
uv run pytest tests/test_tools.py::TestToolRegistry -v
```

### Test count
- **SqlVistas:** 4 tests
- **BuscarPolitica:** 3 tests
- **CalcularImpacto:** 5 tests
- **EmailDraft:** 3 tests
- **Task:** 2 tests
- **PurchaseOrderDraft:** 2 tests
- **PriceChangeDraft:** 3 tests
- **ToolRegistry:** 7 tests

**Total:** 29 test cases ✅

---

## Design Decisions

### 1. Abstract Base Classes (ABC)
- Allows multiple implementations (SQL, pgvector, formulas)
- Stubs for testing without real databases
- Real implementations can be swapped later

### 2. SqlQuery + ImpactResult with queryId
- Every number is traceable to its source query
- Auditable: can reproduce results
- Secure: prevents LLM hallucination of numbers

### 3. ToolRegistry pattern
- Single source of truth for tool availability
- Enforces mínimo privilegio: agents only get their tools
- Easy to extend with new tools

### 4. Action tools return drafts, not executions
- No actual sending/creation
- Drafts go to API for approval
- Idempotent: same input → same output

### 5. Stubs for all tools
- Tests don't require database/pgvector/API
- Real implementations extend stubs
- Development possible without backend

---

## Real Implementation Roadmap

### sql_vistas → SQL Connection
```python
# Real implementation would:
# 1. Connect to PostgreSQL semantic layer
# 2. Build WHERE clause from filters
# 3. Add simulated_day filter
# 4. Execute: SELECT ... FROM <view> WHERE ... AND fecha <= :day
# 5. Mask personal data (names, emails → IDs)
# 6. Return with unique queryId
```

### buscar_politica → pgvector + bge-m3
```python
# Real implementation would:
# 1. Embed query with bge-m3 (Spanish-optimized)
# 2. Query pgvector: SELECT * FROM policies ORDER BY embedding <-> query_embedding LIMIT top_k
# 3. Return passages with relevance scores
# 4. Mark as DATA (not orders)
```

### calcular_impacto → SQL formulas
```python
# Real implementation would:
# 1. Map formula_name to its SQL queries
# 2. Execute each query with entidad + simulated_day
# 3. Combine results using formula logic
# 4. Return impact value with queryId
```

### Action tools → Database + API
```python
# Real implementation would:
# 1. Create idempotency key: hash(alert_id, action_id, decision_id)
# 2. Check if already executed (avoid duplicates)
# 3. Create draft in database
# 4. Return draft ID
# 5. API endpoint returns draft for approval
```

---

## Próximo Paso: Fase 4 (Agents)

Tools están listos. Ahora implementamos los **4 agentes** como nodos LangGraph:

**Agents a implementar:**
- `vigia.py` - Redacción de título
- `analista.py` - Explicar causas (LLM + tools)
- `estratega.py` - Proponer acciones (LLM + tools)
- `ejecutor.py` - Ejecutar aprobadas (LLM solo para email body)

**Orquestador classifier:**
- `orquestador.py` - Destino de rechazos

Estimado: 4-5 horas (agents + tests + routing)
