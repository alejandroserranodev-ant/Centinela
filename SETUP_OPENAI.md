# OpenAI Setup Guide 🔐

**SECURITY-FIRST approach** para usar OpenAI API con Centinela.

---

## ⚠️ IMPORTANTE: Seguridad de API Keys

**NUNCA**:
- ❌ Compartir API keys en chat, emails, o commits
- ❌ Guardar API keys en archivos de código
- ❌ Usar API keys en URLs o logs
- ❌ Reuscar API keys - siempre rotar después de exposición

**SIEMPRE**:
- ✅ Usar variables de entorno (`.env` files)
- ✅ Mantener `.env` en `.gitignore`
- ✅ Rotar keys después de cualquier exposición
- ✅ Usar scope mínimo en OpenAI API keys

---

## Setup Paso a Paso

### 1. Obtener API Key de OpenAI

1. Ve a https://platform.openai.com/account/api-keys
2. Click en "Create new secret key"
3. Copia la key (solo aparece una vez)
4. Guárdala en un lugar seguro

### 2. Crear archivo `.env` local

```bash
# En la raíz del proyecto
cp .env.example .env
```

Edita `.env` y agrega tu API key:

```env
OPENAI_API_KEY=sk-proj-tu-api-key-aqui
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=INFO
```

**IMPORTANTE**: `.env` está en `.gitignore` - NUNCA se commitea

### 3. Cargar .env en Python

**Opción A: Automático (recomendado)**

```bash
pip install python-dotenv
```

En tu script principal (antes de importar centinela_agents):

```python
from dotenv import load_dotenv
load_dotenv()  # Lee .env automáticamente

from centinela_agents.provider_factory import ProviderFactory

provider = ProviderFactory.create()  # Usa OPENAI_API_KEY del .env
```

**Opción B: Manual**

```python
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print(f"API Key loaded: {api_key[:10]}...")  # Solo muestra primeros 10 chars
```

**Opción C: Variable de Entorno (sin .env)**

```bash
# Linux/Mac
export OPENAI_API_KEY="sk-proj-..."

# Windows PowerShell
$env:OPENAI_API_KEY="sk-proj-..."

# Windows CMD
set OPENAI_API_KEY=sk-proj-...
```

### 4. Verificar que Funciona

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()

from centinela_agents.provider_factory import ProviderFactory
from centinela_agents.llm_provider import ModelConfig

config = ModelConfig(model='gpt-4o-mini')
provider = ProviderFactory.create(config)
print('✅ OpenAI provider initialized successfully')
print(f'   Model: {config.model}')
print(f'   Provider: {type(provider).__name__}')
"
```

Expected output:
```
✅ OpenAI provider initialized successfully
   Model: gpt-4o-mini
   Provider: OpenAIProvider
```

---

## Troubleshooting

### Error: "OPENAI_API_KEY environment variable not set"

**Causa**: El archivo `.env` no se está cargando

**Solución**:
```python
# Asegúrate de esto ANTES de importar centinela_agents
from dotenv import load_dotenv
load_dotenv()  # Esto carga .env

import os
print(f"DEBUG: OPENAI_API_KEY = {os.getenv('OPENAI_API_KEY')}")
```

### Error: "OpenAI API health check failed"

**Posibles causas**:
1. API key es inválida o expirada
2. API key fue revocada
3. No hay conexión a internet
4. Límite de requests alcanzado

**Soluciones**:
1. Verifica la API key en https://platform.openai.com/account/api-keys
2. Si está roja o marcada para revoke, genera una nueva
3. Verifica tu conexión: `ping api.openai.com`
4. Chequea tu usage en https://platform.openai.com/account/usage/overview

### Error: "API key does not start with 'sk-'"

**Causa**: Copiaste mal la API key

**Solución**: Vuelve a copiar de https://platform.openai.com/account/api-keys

---

## Seguridad en CI/CD

### GitHub Actions

```yaml
# .github/workflows/test.yml
env:
  OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -r requirements.txt
      - run: pytest packages/agents/tests/
```

**Configura el secret**:
1. Repo → Settings → Secrets and variables → Actions
2. "New repository secret"
3. Name: `OPENAI_API_KEY`
4. Value: Tu API key
5. Add secret

### Ollama (Local - Sin API Key)

Si prefieres no usar OpenAI (sin costo), usa Ollama:

```bash
# Instala Ollama
curl https://ollama.ai/install.sh | sh

# Descarga modelo
ollama pull llama2

# Inicia servidor (localhost:11434)
ollama serve
```

Luego configura en `.env`:
```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama2
```

---

## Mejores Prácticas

### 1. Rotación de Keys

Rota tu API key mensualmente o después de:
- Cualquier exposición
- Cambios de personal
- Auditoría de seguridad

```bash
# Revoca old key en https://platform.openai.com/account/api-keys
# Genera nueva key
# Actualiza .env local
# Actualiza secrets en CI/CD
```

### 2. Logging Seguro

**❌ MAL - Expone secrets**:
```python
print(f"API Key: {os.getenv('OPENAI_API_KEY')}")  # NUNCA!
logger.info(f"Using key: {api_key}")  # NUNCA!
```

**✅ BIEN - Solo muestra sufijo**:
```python
key = os.getenv('OPENAI_API_KEY')
masked_key = f"{key[:10]}...{key[-4:]}"  # sk-proj-... ...1234
logger.info(f"Using API key: {masked_key}")
```

### 3. Testing sin API Real

```python
# test_openai_provider.py
from centinela_agents.openai_provider import OpenAIProvider
from centinela_agents.llm_provider import ModelConfig

def test_openai_provider_init():
    # Skip health check en tests
    config = ModelConfig(model='gpt-4o-mini')
    provider = OpenAIProvider(config, skip_health_check=True)
    assert provider.config.model == 'gpt-4o-mini'
```

---

## Contacto & Soporte

Si tienes problemas:
1. Revisa logs: `LOG_LEVEL=DEBUG python script.py`
2. Verifica API key en https://platform.openai.com/account/api-keys
3. Chequea status de OpenAI: https://status.openai.com

---

**Created**: 2026-10-03  
**Last Updated**: 2026-10-03  
**Security Level**: 🔒 Production Ready
