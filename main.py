from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers import pedidos, google_maps # 🆕 Agregado google_maps

# Importamos el enrutador modular que creamos
from routers import pedidos

app = FastAPI(
    title="Saga Falabella - E-Commerce Last Mile API",
    description="Sistema modular de optimización y trazabilidad para distribución de última milla.",
    version="1.0.0"
)

# Configuración obligatoria de CORS para permitir conexiones desde Flutter Web / Chrome
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registramos el módulo de pedidos en el servidor central


app.include_router(pedidos.router)
app.include_router(google_maps.router)

@app.get("/")
def check_health():
    """Ruta raíz para verificar que el backend responda en local o en Render."""
    return {
        "status": "online",
        "entidad": "Saga Falabella S.A.C.",
        "modulo": "Distribución Última Milla"
    }

# Arranque automático exclusivo para ejecución en tu PC local

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)