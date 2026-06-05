from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import supabase

app = FastAPI(title="Saga Falabella Public API")

# Permiso CORS obligatorio para conexiones de celulares reales
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def inicio():
    return {"estado": "online", "mensaje": "API Pública de Saga Falabella"}

@app.get("/api/pedido-abierto")
def obtener_pedido():
    try:
        response = supabase.table("pedidos").select("*").execute()
        return {"pedido": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))