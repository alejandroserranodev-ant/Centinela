import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import alertas, arbol, auth, bandeja, bitacora, chat, configuracion, consultas, interno, simulacion

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
for ruidoso in ("httpx", "httpx2", "httpcore", "openai"):
    logging.getLogger(ruidoso).setLevel(logging.WARNING)

app = FastAPI(title="Centinela API")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(auth.router)
app.include_router(simulacion.router)
app.include_router(alertas.router)
app.include_router(bandeja.router)
app.include_router(chat.router)
app.include_router(bitacora.router)
app.include_router(consultas.router)
app.include_router(configuracion.router)
app.include_router(arbol.router)
app.include_router(interno.router)
