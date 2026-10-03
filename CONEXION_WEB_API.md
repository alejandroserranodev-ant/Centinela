# Conexión web ↔ API

## Flujo HTTP: apps/web llamando al apps/api

```
┌──────────────────┐                    ┌──────────────────┐
│   apps/web       │                    │    apps/api      │
│  (React/Vite)    │                    │   (FastAPI)      │
└──────────────────┘                    └──────────────────┘
        │                                       │
        │ GET /simulacion/dia-actual            │
        ├──────────────────────────────────────→│
        │                                       │
        │  {"dia": "2026-01-15"}                │
        │←──────────────────────────────────────┤
        │                                       │
        │ GET /alertas?estado=propuesta         │
        ├──────────────────────────────────────→│
        │                                       │
        │  Alert[]                              │
        │←──────────────────────────────────────┤
        │                                       │
        │ POST /simulacion/avanzar (SSE)        │
        ├──────────────────────────────────────→│
        │                                       │
        │ event: step (Vigía)                   │
        │ event: alert (nueva)                  │
        │ event: end (newAlerts: [...])         │
        │←──────────────────────────────────────┤
        │ (mientras los agentes trabajan)       │
        │                                       │
        │ POST /alertas/{id}/decision           │
        ├──────────────────────────────────────→│
        │ Headers: X-User-Name, X-User-Role     │
        │                                       │
        │  Alert (status=approved)              │
        │←──────────────────────────────────────┤
        │                                       │
        │ POST /chat (SSE)                      │
        ├──────────────────────────────────────→│
        │                                       │
        │ event: step (Analista)                │
        │ event: chunk (respuesta...)           │
        │ event: end (ChatMessage)              │
        │←──────────────────────────────────────┤
        │                                       │
        │ GET /bitacora?alertId=...             │
        ├──────────────────────────────────────→│
        │                                       │
        │  LogEvent[]                           │
        │←──────────────────────────────────────┤
```

## Archivos de configuración

### apps/web/.env
```bash
VITE_API_URL=http://localhost:8000
```

(Production: `https://api.centinela.example.com`)

### apps/web/src/api/
- `config.ts` — URL base, headers, usuario por defecto
- `http-client.ts` — Implementación fetch real (reemplaza fixtures)
- `types.ts` — Tipos TypeScript (sincronizados con apps/api/modelos.py)
- `client.ts` — Reexporta http-client

## Setup: Levantar todo

### 1. Base de datos y API
```bash
# Terminal 1: Base de datos
cd data
docker-compose up -d

# Terminal 2: API
cd apps/api
pip install -e .
uvicorn centinela_api.main:app --reload
# http://localhost:8000
# Swagger: http://localhost:8000/docs
```

### 2. Web
```bash
# Terminal 3: Web
cd apps/web
npm install
VITE_API_URL=http://localhost:8000 npm run dev
# http://localhost:5173
```

## Flujo del usuario en la web

1. **Load**: Web hace GET `/simulacion/dia-actual` → obtiene día simulado
2. **Inbox**: GET `/alertas?estado=propuesta` → lista alertas (vacía hasta que Vigía cree)
3. **Clock**: Click "Siguiente día" → POST `/simulacion/avanzar` (SSE)
   - Ve a Vigía revisando indicadores
   - Ver alertas nuevas llegar (cuando Vigía esté implementado)
4. **Alert detail**: GET `/alertas/{id}` → muestra causa, evidencia, acciones
5. **Decision**: POST `/alertas/{id}/decision` (gerente/lider_proceso)
   - Aprobada → se pone en verde
   - Ejecutada → muestra resultado (cuando Ejecutor esté implementado)
6. **Chat**: POST `/chat` (SSE) → responde "sin evidencia suficiente" por ahora
7. **Audit**: GET `/bitacora?alertId=...` → historial completo

## Estado actual (sin agentes)

✅ La web conecta al API
✅ GET endpoints funcionan (lista alertas, obtiene detalle, bitácora)
✅ POST /alertas/{id}/decision funciona (cambios de estado)
❌ POST /simulacion/avanzar devuelve `newAlerts: []` (Vigía no existe)
❌ POST /chat devuelve "sin evidencia suficiente" (Analista no existe)
❌ POST /alertas/{id}/decision nunca llama a Ejecutor (no existe)

## Próximos pasos

Cuando packages/agents esté lista:
1. POST /simulacion/avanzar llamará a Vigía → creará alertas
2. POST /chat llamará a Analista → responderá preguntas
3. POST /alertas/{id}/decision llamará a Ejecutor → ejecutará acciones

La web no cambia; el API la conecta con los agentes.

## Testing con Swagger UI

Abre http://localhost:8000/docs y prueba:

1. `GET /simulacion/dia-actual` → `{"dia": "2026-01-15"}`
2. `GET /alertas` → `[]` (vacío, sin alertas creadas aún)
3. `POST /simulacion/avanzar?dias=1` → mira la respuesta SSE (sin alertas por ahora)
4. Copia una alerta desde fixtures y `POST /interno/alertas` (si la necess) para probar decisiones

Una vez Vigía esté implementada, `/simulacion/avanzar` creará alertas automáticamente.
