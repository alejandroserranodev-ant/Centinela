GUARDS = ("lenguaje", "fuente", "reloj", "costo", "tiempo", "cardinalidad", "hash", "catalogo")


class Refused(Exception):
    def __init__(self, guard: str, detail: str):
        if guard not in GUARDS:
            raise ValueError(f"{guard} is not a guard of the kernel")
        super().__init__(f"{guard}: {detail}")
        self.guard = guard
        self.detail = detail
