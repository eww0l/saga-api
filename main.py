from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from database import supabase

app = FastAPI(title="Saga Falabella Logistics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def inicio():
    return {"estado": "online", "mensaje": "API de Logística Saga Falabella"}


@app.get("/api/pedido-abierto")
def obtener_pedido():
    """Endpoint legado — mantiene compatibilidad con el prototipo anterior."""
    try:
        response = supabase.table("pedidos").select("*").execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="No hay pedidos registrados.")
        return {"pedido": response.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pedidos-courier")
def obtener_pedidos_por_courier(
    courier_id: str = Query(..., min_length=1, description="ID del courier asignado")
):
    """
    Devuelve todos los pedidos asignados a un courier específico.
    Parámetro: ?courier_id=C-001
    """
    try:
        response = (
            supabase.table("pedidos")
            .select("id, cliente_direccion, courier_id, created_at")
            .eq("courier_id", courier_id)
            .order("created_at", desc=False)   # orden cronológico = hoja de ruta natural
            .execute()
        )

        return {
            "courier_id": courier_id,
            "total_pedidos": len(response.data),
            "pedidos": response.data,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))