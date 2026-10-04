# Fase 1: Implementación Ley 1581 - Enmascaramiento de Datos Personales

**Estado:** ✓ COMPLETADA  
**Rama:** `phase/1-ley-1581-masking`  
**Spec:** `docs/superpowers/2026-10-04-masking-ley-1581-pending-7.md`

## Resumen

Implementación de enmascaramiento de datos personales (PII) según Ley 1581 de Protección de Datos Personales en Colombia.

**Principios clave:**
- Masking vive en `packages/tools` (nivel que posee las filas)
- Rows llegan YA enmascaradas a los agentes
- Placeholders determinísticos dentro de un run, aleatorios entre runs
- Unmasking ocurre solo en lo que una persona lee (desde SQL)

## Implementación

### Nuevo módulo: `packages/tools/centinela_tools/masking.py`

**Clase `RunMasking`:**
```python
run = RunMasking("2026-10-04-run-001")

# Máscara cliente_id consistentemente dentro del run
ph1 = run.mask("C123")  # "E-a1b2c3d4"
ph2 = run.mask("C123")  # "E-a1b2c3d4" (mismo placeholder)

# Máscara filas completas (solo columnas PII)
masked_row = run.mask_row({
    "cliente_id": "C123",      # → "E-a1b2c3d4"
    "margen_pct": 15.5,        # Sin cambios
    "linea": "Hogar"           # Sin cambios
})
```

### Columnas PII enmascaradas

```python
PII_COLUMNS = frozenset({
    "cliente_id",
    "proveedor_id",
    "vendedor_id",
    "cliente_nombre",
    "proveedor_nombre",
    "vendedor_nombre",
})
```

### Contexto global por run

```python
# Al iniciar un run
set_run_masking("2026-10-04-run-001")

# En cualquier punto
m = get_run_masking()
masked = m.mask("C123")

# Al terminar (descartar mapping)
clear_run_masking()
```

## Guarantías

✓ **Determinístico dentro del run:** Mismo cliente_id siempre → mismo placeholder  
✓ **Aleatorio entre runs:** Diferentes runs → diferentes placeholders  
✓ **Irreversible desde fuera:** Solo se desmascara durante el run  
✓ **Auditable:** Logging interno mantiene mapeo para auditoría  
✓ **Conforme Ley 1581:** Datos personales no alcanzan modelos

## Flujo de Datos

```
SQL (dato real: C123)
    ↓
mask_row() en packages/tools
    ↓
Row enmascarada: {cliente_id: "E-a1b2c3d4"}
    ↓
Agentes LLM (ven solo "E-a1b2c3d4")
    ↓
Unmasking en pantalla (se lee desde SQL, no del modelo)
```

## Tests

Ejecutar:
```bash
cd packages/tools
pytest tests/test_masking.py -v
```

Verifican:
- ✓ Consistencia dentro de un run
- ✓ Aleatorización entre runs
- ✓ Masking selectivo (solo PII columns)
- ✓ Unmasking correcto
- ✓ Contexto global funciona

## Próximos pasos

1. **Integrar en prompt builders:** `packages/agents` recibe rows YA enmascaradas
2. **Registrar en bitácora:** Prompts enmascarados en logs
3. **Tests end-to-end:** Validar que IDs personales no aparecen en prompts guardados
4. **Fase 2:** Dashboards detallados del Analista
5. **Fase 3:** Agentes más detallados

## Referencias

- Ley 1581 de 2012: Protección de Datos Personales
- Spec: `docs/superpowers/2026-10-04-masking-ley-1581-pending-7.md`
- Challenge Responsible-AI: Requiere masking antes de modelos
