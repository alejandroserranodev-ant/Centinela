# Tareas pendientes para completar Centinela

## 📊 Resumen
- **Completado**: API, data layer, web (conexión básica)
- **En desarrollo**: packages/agents, packages/tools
- **Plazo**: Hackathon 3 días

---

## 🎯 FASE 1: packages/agents (Orquestador + 4 agentes)

### Orquestador (LangGraph)
- [ ] Crear `packages/agents/src/centinela_agents/main.py` con grafo LangGraph
- [ ] Estado de alerta: tracking id, status, paso actual
- [ ] Nodos del grafo:
  - [ ] vigia_node → call Vigía
  - [ ] analista_node → call Analista  
  - [ ] estratega_node → call Estratega
  - [ ] human_node → pause for decision (interrupt)
  - [ ] ejecutor_node → call Ejecutor
- [ ] Edges: validar transiciones, routing condicional
- [ ] Error handling: timeout (30s), retry (3x), fallback ("sin evidencia")
- [ ] Cost tracking: acumular tokens + latencia por step
- [ ] Test fixtures: 5 escenarios anunciados + oculto

### Vigía (Detector de anomalías)
**Archivo**: `packages/agents/src/centinela_agents/vigia.py`

- [ ] Leer `data/metricas.yaml` → umbrales + dimensiones
- [ ] Para cada métrica:
  - [ ] Llamar tools/SQL: `GET v_{metrica} WHERE fecha <= {dia_simulado}`
  - [ ] Implementar z-score: detectar desviación > 2σ de media
  - [ ] Implementar tendencia: comparar semana/mes actual vs. histórico
  - [ ] Comparar con `ref_*` tables (márgenes mínimos, topes descuento)
  - [ ] Generar alerta si umbral violado
- [ ] Agrupar alertas por causa compartida (no 10 alertas de 1 problema)
- [ ] Calcular `pesosAtRisk` (COP en juego)
- [ ] Calcular `recoverablePerMonth` (impacto potencial)
- [ ] Ordena por pesos (descendente)
- [ ] Buscar señales del escenario oculto (cliente_id, patrones raros)
- [ ] POST `/interno/alertas` con AgentAlertInput
- [ ] Tests: 5 escenarios anunciados deben detectarse

**Escenarios a detectar**:
1. ✅ Margen bajo: v_margen_semanal_linea, caída > 3 puntos
2. ✅ Mora (overdue debt): v_cartera_cliente, días_vencido > 15
3. ✅ Quiebre de stock: v_cobertura_inventario, cobertura < 10 días (clase A)
4. ✅ Descuentos fuera política: v_descuentos_fuera_politica, sin aprobación especial
5. ✅ Cliente que se va: v_actividad_cliente, inactividad > 3x intervalo habitual
6. ❓ Escenario oculto: descubrir en los datos (dataset tiene 6 anomalías)

### Analista (Explicador de causas)
**Archivo**: `packages/agents/src/centinela_agents/analista.py`

- [ ] Input: Alert (status=new) con métrica y umbrales
- [ ] Llamar tools/SQL: queries relacionadas a la métrica
  - [ ] Buscar causa raíz en datos históricos
  - [ ] Comparar cliente/línea/vendedor contra promedio
- [ ] Llamar tools/policies: buscar política relevante en PDFs
  - [ ] Términos de crédito, políticas de descuento, etc.
  - [ ] Usar RAG (pgvector) para similitud
- [ ] Generar Evidence: cada claim con figures (números SQL) + queries
- [ ] Si no hay evidencia → CauseNoEvidence + razón
- [ ] PUT `/interno/alertas/{id}/causa` con AgentCauseInput
- [ ] Confidencia: "high" si datos claros, "medium" si parcial

### Estratega (Propositor de acciones)
**Archivo**: `packages/agents/src/centinela_agents/estratega.py`

- [ ] Input: Alert (status=analyzing) con causa
- [ ] Generar 1-3 acciones según causa:
  - [ ] email_draft → notificar a vendedor/cliente
  - [ ] task → crear tarea en sistema (simulado)
  - [ ] purchase_order_draft → orden de compra (p.ej., stock)
  - [ ] price_change_draft → ajuste de precio
- [ ] Para cada acción:
  - [ ] id único
  - [ ] title + description (Sentence con figures)
  - [ ] type (ActionType)
  - [ ] impact: pesos + período (mes/once)
  - [ ] confidence level
  - [ ] parameters: campo editable por usuario (precios, cantidades, etc.)
- [ ] Llamar tools para calcular impacto:
  - [ ] Si precio sube 3%, cuánto recupera (herramienta SQL)
  - [ ] Si compra stock, cuánto cuesta (herramienta SQL)
- [ ] PUT `/interno/alertas/{id}/propuesta` con AgentProposalInput
- [ ] Ordenar acciones por impact (descendente)

### Ejecutor (Ejecutor de acciones aprobadas)
**Archivo**: `packages/agents/src/centinela_agents/ejecutor.py`

- [ ] Input: Alert (status=approved) con action_id elegido
- [ ] Llamar tools/actions para ejecutar:
  - [ ] email_draft: generar HTML, simular envío
  - [ ] task: crear en sistema (simulado)
  - [ ] purchase_order_draft: generar PDF, simular creación
  - [ ] price_change_draft: actualizar lista precios (simulado)
- [ ] Todas las acciones IDEMPOTENTES (ejecutar 2x = mismo efecto)
- [ ] Todas las acciones en DRAFT o SANDBOX (no producción)
- [ ] Registrar resultado
- [ ] POST `/interno/alertas/{id}/ejecutar` con AgentExecutionInput
- [ ] Status: success, failed, partial

### Testing & Integration
- [ ] Test suite en `packages/agents/tests/`:
  - [ ] test_vigia.py: detectar 5 escenarios
  - [ ] test_analista.py: explicar causas
  - [ ] test_estratega.py: proponer acciones
  - [ ] test_ejecutor.py: ejecutar sin errores
  - [ ] test_orquestador.py: flujo completo
- [ ] Fixtures: alertas de ejemplo para cada escenario
- [ ] Probar con SEMILLA=1, SEMILLA=2 (datasets generados)
  - Detectores NO deben estar hardcodeados al dataset oficial

---

## 🔧 FASE 2: packages/tools (3 MCP servers)

### MCP SQL (Lectura de vistas)
**Archivo**: `packages/tools/src/centinela_tools/sql_tool.py`

- [ ] Conectar como `tools_reader` (read-only user)
- [ ] Herramientas MCP:
  - [ ] `query_view(view, filters, fecha_maxima)` → ResultSet + SQL usado
  - [ ] `get_schema(view)` → columnas, tipos, descripción
  - [ ] Validar vista es en `v_*` (solo lectura semántica)
- [ ] Manejo de fecha simulada:
  - [ ] Parámetro `fecha_maxima` en cada llamada
  - [ ] Filtrar WHERE fecha <= fecha_maxima en vistas que lo requieren
  - [ ] Para vistas con fecha_corte(), usar fecha_maxima como hoy
- [ ] Retornar:
  - [ ] results: filas como dicts
  - [ ] query: SQL exacto ejecutado (para bitácora)
  - [ ] row_count: cuántas filas
- [ ] Logging: cada query en api.bitacora con query_id
- [ ] Tests:
  - [ ] Conecta sin write access
  - [ ] Filtra por fecha correctamente
  - [ ] Retorna datos de las 6 vistas principales

### MCP Policies (Búsqueda de políticas)
**Archivo**: `packages/tools/src/centinela_tools/policies_tool.py`

- [ ] Cargar PDFs de `data/policies/`:
  - [ ] credit_policy.pdf
  - [ ] discount_policy.pdf
  - [ ] inventory_policy.pdf
- [ ] Embeddings con pgvector:
  - [ ] Chunking: párrafos por política
  - [ ] Embedding: Claude (openai ada compatible)
  - [ ] Store en `centinela.policy_embeddings` (tabla nueva)
- [ ] Herramienta MCP:
  - [ ] `search_policies(query, similarity_threshold=0.7)` → passages
  - [ ] Retornar: texto exacto (quoted), página, confianza
- [ ] Validar que políticas SON DATA, NO INSTRUCCIONES
  - [ ] Si alerta dice "rebajar precio", Estratega decide, no obedece
- [ ] Tests: búsquedas devuelven pasajes correctos

### MCP Actions (Ejecución de acciones)
**Archivo**: `packages/tools/src/centinela_tools/actions_tool.py`

- [ ] Herramientas MCP (idempotentes, draft/sandbox):
  - [ ] `draft_email(to, subject, body)` → email_id, draft URL
  - [ ] `create_task(title, description, assignee)` → task_id
  - [ ] `draft_purchase_order(supplier_id, items)` → po_id, draft PDF
  - [ ] `draft_price_change(sku, new_price)` → change_id, effective_date
- [ ] Idempotencia:
  - [ ] Guardar acciones con id
  - [ ] Si `draft_email` con mismo id 2x → retorna existente, no nuevo
- [ ] Simulación (no tocar producción):
  - [ ] Emails: guardar en archivo, mostrar URL
  - [ ] Tasks: crear en tabla `tasks` (simulada)
  - [ ] POs: generar PDF en `/tmp`, retornar ruta
  - [ ] Precios: actualizar tabla local, no DB real
- [ ] Tests: crear 4 tipos de acciones, verificar idempotencia

---

## 🔗 FASE 3: Integraciones

### API ajustes finales
- [ ] Endpoint `/interno/alertas/{id}/causa` → PUT (Analista)
  - Validar que viene de X-Agent: analista
  - Transición: new → analyzing
- [ ] Endpoint `/interno/alertas/{id}/propuesta` → PUT (Estratega)
  - Validar que viene de X-Agent: estratega
  - Transición: analyzing → proposed
- [ ] Endpoint `/interno/alertas/{id}/ejecutar` → POST (Ejecutor)
  - Validar que alert.status == approved
  - Transición: approved → executed
- [ ] Endpoint POST `/chat` → conectar a Analista
  - No es dummy, llama real a Analista
  - SSE events: step (thinking), chunk (respuesta), end (message)
- [ ] POST `/simulacion/avanzar` → llamar Vigía
  - No es dummy, newAlerts son reales

### Web ajustes finales
- [ ] POST /chat: mostrar progreso de Analista en tiempo real
- [ ] POST /simulacion/avanzar: mostrar progreso de Vigía + alertas nuevas
- [ ] Animar aprobación → ejecución de Ejecutor
- [ ] Mostrar costos/latencia en UI (si disponible)

### Data ajustes finales
- [ ] Crear tabla `centinela.policy_embeddings` (para RAG)
  - Columnas: policy_id, chunk_id, text, embedding (pgvector)
- [ ] Crear tabla `centinela.tasks_simulada` (para MCP)
  - Columnas: task_id, title, assignee, status, created_at
- [ ] Verificar que usuario `tools_reader` tiene SELECT en todas las vistas
- [ ] Seed inicial: datos base día 2026-10-01 (ya cargados)

---

## ✅ FASE 4: Testing & Validación

### Tests unitarios
- [ ] packages/agents: 20+ tests (detectores, explicadores, etc.)
- [ ] packages/tools: 10+ tests (SQL, policies, actions)
- [ ] apps/api: 15+ tests (endpoints, ciclo de vida, masking)

### Tests de integración (E2E)
- [ ] Flujo completo: reloj → Vigía → Analista → Estratega → Decisión → Ejecutor
- [ ] 5 escenarios anunciados deben completar el ciclo
- [ ] Escenario oculto debe ser detectado
- [ ] Bitácora registra cada paso con actores correctos

### Tests con generador
- [ ] `SEMILLA=1 python generator/generar_dataset.py`
- [ ] Detectores funcionan en nuevo dataset (no ajustados al oficial)
- [ ] Umbrales en metricas.yaml se aplican correctamente

### Manual testing (Jury perspective)
- [ ] Abrir web, avanzar día, ver alertas nuevas
- [ ] Abrir alerta, leer causa + evidencia
- [ ] Hablar con Analista por chat: "¿por qué crecieron los días de pago?"
- [ ] Revisar acciones, editar parámetros
- [ ] Aprobar acción → ver Ejecutor crear draft
- [ ] Ver auditoría completa en bitácora

---

## 🚀 FASE 5: Deployment & Demo (3 min)

### Docker setup
- [ ] Crear `docker-compose.yml` a nivel raíz que levante:
  - [ ] PostgreSQL + pgAdmin
  - [ ] API (apps/api)
  - [ ] Web (apps/web, servida desde nginx o node)
  - [ ] MCP servers (en contenedores separados)
- [ ] Un comando: `docker-compose up` → todo funciona
- [ ] Volúmenes persistentes para BD

### Demo script (5 minutos)
- [ ] Mostrar web vacía
- [ ] Click "Siguiente día" → Vigía detecta 2-3 alertas
- [ ] Click en una → muestra causa, evidencia, acciones
- [ ] Ask chat: "¿qué pasó con el margen?" → Analista responde
- [ ] Aprobar acción → muestra draft (email/PO)
- [ ] Ver bitácora: Vigía → Analista → Estratega → Decisión → Ejecutor
- [ ] Mostrar SQL usado + costos de tokens

### Pitch (3 minutos)
- [ ] Problema: Distribuidora pierde dinero por ineficiencias
- [ ] Solución: Centinela ve problemas antes que causen daño
- [ ] ROI: $42M/mes recuperables en margen
- [ ] Cómo: 4 agentes + datos + decisión humana = sin riesgo

---

## 📋 Checklist por equipo

### Equipo Agents (2 personas)
- [ ] Vigía con detectores para 5 escenarios
- [ ] Analista con búsqueda de causas
- [ ] Estratega con generación de acciones
- [ ] Ejecutor con creación de drafts
- [ ] Orquestador LangGraph
- [ ] 20+ tests

**Entregable**: `packages/agents/` completo, todas las funciones POST `/interno/*` respondidas

### Equipo Tools (1 persona)
- [ ] MCP SQL (query_view, get_schema)
- [ ] MCP Policies (search_policies con pgvector)
- [ ] MCP Actions (draft_*, idempotente)
- [ ] 10+ tests

**Entregable**: `packages/tools/` con 3 MCP servers funcionando

### Equipo Data (si es necesario)
- [ ] Tabla `policy_embeddings` en PostgreSQL
- [ ] Tabla `tasks_simulada`
- [ ] Verificar permisos de `tools_reader`
- [ ] Script de setup completo en AGENTS.md

**Entregable**: BD lista con todos los datos y user read-only

### Equipo API (completado)
- ✅ Endpoints públicos
- ✅ Endpoints internos
- ✅ Ciclo de vida
- ✅ Bitácora
- ✅ Masking
- ⏳ Ajustes menores (POST /chat, POST /simulacion/avanzar con Vigía)

---

## 📅 Timeline sugerido (Hackathon 3 días)

### Día 1
- [ ] Setup git + branches
- [ ] Agents: Vigía básico (z-score + 2 escenarios)
- [ ] Tools: MCP SQL funcional
- [ ] Data: tablas nuevas creadas

### Día 2
- [ ] Agents: Analista + Estratega funcionales
- [ ] Tools: MCP Policies + Actions
- [ ] API: ajustes para POST /chat, /simulacion/avanzar
- [ ] Web: testing con API real

### Día 3
- [ ] Agents: Ejecutor + Orquestador + tests completos
- [ ] Tests E2E: flujo completo funcionando
- [ ] Docker setup para demostración
- [ ] Demo & pitch

---

## 🎯 Criterios de éxito

✅ **MVP (Mínimo viable)**:
1. Web conectada al API → ver alertas
2. Vigía detecta al menos 3 escenarios anunciados
3. Decisión aprobada → Ejecutor crea draft (email o tarea)
4. Bitácora registra todo
5. Demo en vivo sin crashes

✅ **Bonus (Si hay tiempo)**:
- Escenario oculto detectado
- Chat responde preguntas inteligentes
- Costos de tokens mostrados
- Tests E2E pasando
- Detector funciona en dataset generado (SEMILLA=N)

---

## 📞 Puntos de contacto

- **API ↔ Agents**: `/interno/alertas`, `/interno/alertas/{id}/*`
- **Agents ↔ Tools**: Llamadas MCP (dentro del orquestador)
- **Tools ↔ Data**: Conexión `tools_reader` a PostgreSQL
- **API ↔ Web**: HTTP + SSE
- **API ↔ Bitácora**: Registra cada paso automáticamente

Todos los contratos están documentados en AGENTS.md de cada carpeta.

---

**Status actual**: API lista, data lista, web conectada.
**Próximo**: Comenzar packages/agents (Vigía es crítico para demo).
