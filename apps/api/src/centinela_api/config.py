import os

from dotenv import load_dotenv

load_dotenv()

DSN_ADMIN = os.environ.get("DSN_ADMIN")
<<<<<<< HEAD
AGENT_SECRET_KEY = os.environ.get("AGENT_SECRET_KEY", "insecure-dev-key")
=======
>>>>>>> 237624b (apps/api now owns a Postgres schema, the alert lifecycle and the bitácora, so the six minimal endpoints run for real while Vigía, Analista, Estratega and Ejecutor are still unbuilt.)

ROLES_CON_DECISION = frozenset({"gerente", "lider_proceso"})
