# Fase 1: Provider Layer ✅ COMPLETADA

## Archivos Creados

```
packages/agents/centinela_agents/
├── llm_provider.py              # Base class (Protocol)
├── ollama_provider.py           # Ollama implementation (local HTTP)
├── openai_provider.py           # OpenAI implementation (remote API)
└── provider_factory.py          # Factory for provider selection

tests/
└── test_providers.py            # Unit tests for all providers
```

## Configuración

### Opción 1: Ollama (Recomendado para desarrollo local)

#### Instalación
```bash
# En Windows, descargar desde https://ollama.ai/download/windows
# O en Linux/Mac: curl -fsSL https://ollama.ai/install.sh | sh

# Iniciar servidor
ollama serve
# Default: http://localhost:11434
```

#### Descargar modelo
```bash
# Modelos disponibles (elige uno según RAM):
ollama pull qwen3:4b      # CPU-only, <16GB RAM (rápido, menos preciso)
ollama pull qwen3:8b      # 16GB+ RAM (recomendado)
ollama pull qwen3:14b     # GPU 24GB+ (más preciso)
```

#### Configurar en .env
```bash
# packages/agents/.env
LLM_PROVIDER=ollama
LLM_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434
```

#### Ejecutar
```bash
cd packages/agents
uv sync
uv run pytest tests/test_providers.py -v -k "Ollama"
```

### Opción 2: OpenAI (API remota)

#### Instalación
```bash
# Paquete openai ya en pyproject.toml
uv sync
```

#### API Key
1. Ve a https://platform.openai.com/account/api-keys
2. Crea una nueva API key
3. Copia el valor

#### Configurar en .env
```bash
# packages/agents/.env (NUNCA en Git)
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-proj-...
```

#### Ejecutar
```bash
cd packages/agents
uv run pytest tests/test_providers.py -v -k "OpenAI"
```

## Uso desde Código

### Ejemplo 1: Generar texto (sin schema)
```python
from centinela_agents.provider_factory import get_provider
from centinela_agents.llm_provider import LLMRequest

provider = get_provider()  # Lee LLM_PROVIDER, LLM_MODEL, OPENAI_API_KEY from env

request = LLMRequest(
    system_prompt="Eres un asistente útil en español.",
    user_prompt="¿Cuál es la capital de Colombia?",
    temperature=0.3,
)

response = provider.generate_text(request)
print(response.text)
print(f"Tokens: {response.usage}")
```

### Ejemplo 2: Generar JSON estructurado (con schema)
```python
from centinela_agents.provider_factory import get_provider
from centinela_agents.llm_provider import LLMStructuredRequest
import json

provider = get_provider()

schema = {
    "type": "object",
    "properties": {
        "causa": {
            "type": "string",
            "description": "Breve explicación"
        },
        "confianza": {
            "type": "string",
            "enum": ["alta", "media", "baja"]
        }
    },
    "required": ["causa", "confianza"]
}

request = LLMStructuredRequest(
    system_prompt="Analiza el siguiente dato.",
    user_prompt="El cliente tiene 45 días de retraso. ¿Por qué?",
    schema=schema,
    thinking=False,  # thinking=True para modelos que lo soportan (gpt-4o)
)

response = provider.generate_structured(request)
print(json.dumps(response.parsed, indent=2))
print(f"Tokens: {response.usage}")
```

### Ejemplo 3: Cambiar provider sin cambiar código
```python
import os

# Solo cambiar variable de entorno:
os.environ["LLM_PROVIDER"] = "openai"
os.environ["LLM_MODEL"] = "gpt-4o-mini"

provider = get_provider()  # Ahora usa OpenAI
# El resto del código es idéntico
```

## Cómo Validar Conectividad

### Script de prueba
```python
# packages/agents/test_connectivity.py
from centinela_agents.provider_factory import get_provider
from centinela_agents.llm_provider import LLMRequest, LLMStructuredRequest

try:
    provider = get_provider()
    print(f"✅ Provider listo: {provider.config.provider} ({provider.config.model})")
    
    # Test texto libre
    resp = provider.generate_text(LLMRequest(
        system_prompt="Responde breve.",
        user_prompt="Hola"
    ))
    print(f"✅ Texto: {resp.text[:50]}...")
    print(f"   Tokens: prompt={resp.usage['prompt_tokens']}, completion={resp.usage['completion_tokens']}")
    
    # Test JSON
    schema = {"type": "object", "properties": {"msg": {"type": "string"}}}
    resp = provider.generate_structured(LLMStructuredRequest(
        system_prompt="Devuelve JSON.",
        user_prompt="Test",
        schema=schema
    ))
    print(f"✅ JSON: {resp.parsed}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
```

Ejecutar:
```bash
cd packages/agents
uv run python test_connectivity.py
```

## Decisiones de Diseño

### 1. Abstracción vs. Especificidad
- **Base class + implementaciones** permite agregar proveedores sin cambiar agentes
- Cada implementación maneja detalles específicos (Ollama: `format`, OpenAI: `response_format`)

### 2. Timeouts y Errores
- **Timeouts:** `ModelConfig.timeout_seconds` (default 30s)
- **Retry:** Delegado a quien llama (graph.py), no en el provider
- **Errores claros:** ValueError, TimeoutError, ConnectionError son específicos

### 3. Structured Output
- **Ollama:** Usa `format` (JSON schema constraint)
- **OpenAI:** Usa `response_format: {"type": "json_object"}`
- **Ambos:** Validan JSON, pero Ollama fuerza schema; OpenAI solo fuerza JSON válido

### 4. Extended Thinking (thinking=True)
- **Ollama:** Parámetro soportado en qwen3+ con instrucción explícita
- **OpenAI:** Solo en gpt-4o+ (y después en modelos superiores)
- **Anthropic:** Ready but not yet implemented

## Testing

### Run all provider tests
```bash
cd packages/agents
uv run pytest tests/test_providers.py -v
```

### Run only Ollama tests
```bash
uv run pytest tests/test_providers.py -v -k "TestOllama"
```

### Run connectivity check (requires running server)
```bash
# Ensure ollama serve or OpenAI API is configured
uv run python -m pytest tests/test_providers.py::TestOllamaProvider::test_health_check_fails_without_server -v
```

## Siguiente: Fase 2 (Schemas)

Los providers están listos. El siguiente paso es **Fase 2: Schemas y Validación**, donde crearemos Pydantic schemas para:
- `Cause` (identified | no_evidence)
- `Action` (con title, description, type, parameters, impact, confidence)
- `ExecutedAction`
- `Decision` (approve, edit, reject, request_changes)

Estos schemas se usarán con `generate_structured()` para garantizar que las salidas de los agentes son siempre válidas.
