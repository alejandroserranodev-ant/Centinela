import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parents[4]

load_dotenv(RAIZ / ".env")
load_dotenv(RAIZ / ".env.local", override=True)

DSN_ADMIN = os.environ.get("DSN_ADMIN")
AGENT_SECRET_KEY = os.environ.get("AGENT_SECRET_KEY", "insecure-dev-key")

ROLES_CON_DECISION = frozenset({"gerente", "lider_proceso"})
