from fastapi import APIRouter, HTTPException, Query
from database import supabase_client
from core.config import settings

router = APIRouter(prefix="/api/mapas", tags=["Inteligencia Geográfica Google"])

@router.get("/ruta-optima")
async def obtener_ruta_optimizada(courier_id: str = Query(...)):
    """Calcula el ruteo de última milla considerando prioridades y simulación de tráfico."""
    try:
        # 💡 CONSULTA LIMPIA: Jala solo los datos necesarios y los datos anidados de clientes
        response = (
            supabase_client.supabase.table("pedidos")
            .select("id, codigo_barra, estado, prioridad, clientes(nombre, direccion, distrito, latitud, longitud)")
            .eq("courier_id", courier_id)
            .execute()
        )
        
        pedidos_activos = [p for p in response.data if p["estado"] in ["Asignado", "En Ruta"]]
        if not pedidos_activos:
            return {"motor_georreferenciacion": "Simulador", "total_paradas": 0, "hoja_ruta_optima": []}

        # Ordenamiento inteligente: Prioridad Alta va primero
        pedidos_ordenados = sorted(pedidos_activos, key=lambda x: (0 if x["prioridad"] == "Alta" else 1, x["id"]))

        ruta_final = []
        for index, item in enumerate(pedidos_ordenados, start=1):
            cli = item["clientes"]
            ruta_final.append({
                "parada_numero": index,
                "pedido_id": item["id"],
                "codigo_barra": item["codigo_barra"],
                "prioridad": item["prioridad"],
                "destinatario": cli["nombre"],
                "direccion_completa": f"{cli['direccion']}, {cli['distrito']}",
                "geolocalizacion": {"lat": float(cli["latitud"]), "lng": float(cli["longitud"])},
                "trafico_estimado_minutos": 12 + (index * 5)
            })

        return {
            "courier_id": courier_id,
            "motor_georreferenciacion": "Simulador Autónomo de Tráfico Logístico",
            "total_paradas": len(ruta_final),
            "hoja_ruta_optima": ruta_final
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))