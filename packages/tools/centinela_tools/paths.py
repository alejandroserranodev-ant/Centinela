from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data"
FUENTES = DATA / "kernel" / "fuentes.yaml"
LENGUAJE = DATA / "kernel" / "lenguaje.schema.json"
METRICAS = DATA / "metricas.yaml"
SQL_DIR = DATA / "sql"
GENERATED = SQL_DIR / "05_kpis.generated.sql"
