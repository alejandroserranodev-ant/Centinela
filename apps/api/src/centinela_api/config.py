import os

from dotenv import load_dotenv

load_dotenv()

DSN_ADMIN = os.environ.get("DSN_ADMIN")

ROLES_CON_DECISION = frozenset({"gerente", "lider_proceso"})
