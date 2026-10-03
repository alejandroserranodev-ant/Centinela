import os

from dotenv import load_dotenv

load_dotenv()

DSN_ADMIN = os.environ.get("DSN_ADMIN")
AGENT_SECRET_KEY = os.environ.get("AGENT_SECRET_KEY", "insecure-dev-key")

ROLES_CON_DECISION = frozenset({"gerente", "lider_proceso"})
