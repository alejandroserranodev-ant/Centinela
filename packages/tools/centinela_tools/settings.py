import os
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    max_cost: float = 1_000_000.0
    timeout_ms: int = 5_000
    max_groups: int = 20_000
    sample_rows: int = 20

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "Settings":
        default = cls()
        return cls(
            float(env.get("CENTINELA_KERNEL_COSTO_MAX", default.max_cost)),
            int(env.get("CENTINELA_KERNEL_TIMEOUT_MS", default.timeout_ms)),
            int(env.get("CENTINELA_KERNEL_GRUPOS_MAX", default.max_groups)),
            int(env.get("CENTINELA_KERNEL_MUESTRA", default.sample_rows)),
        )
