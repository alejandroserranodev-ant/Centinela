import json
from collections.abc import AsyncIterator

from pydantic import BaseModel


async def flujo(eventos: AsyncIterator[tuple[str, BaseModel | dict]]) -> AsyncIterator[bytes]:
    async for nombre, dato in eventos:
        cuerpo = dato.model_dump(by_alias=True) if isinstance(dato, BaseModel) else dato
        yield f"event: {nombre}\ndata: {json.dumps(cuerpo, ensure_ascii=False)}\n\n".encode()
