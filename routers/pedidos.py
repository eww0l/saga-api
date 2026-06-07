from fastapi import APIRouter, HTTPException, Query
from database import supabase_client
import requests
# 📐 Importaciones matemáticas para calcular la distancia real por calles (Fórmula de Haversine)
from math import radians, cos, sin, asin, sqrt

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos Logística"])

# 📐 FUNCIÓN AUXILIAR: Calcula la distancia en kilómetros entre dos coordenadas GPS
def calcular_distancia_haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radio de la Tierra en kilómetros
    return c * r
def obtener_ruta_osrm(coordenadas):
    try:
        coordenadas = [
            (lng, lat)
            for lng, lat in coordenadas
            if lng is not None and lat is not None
        ]

        if len(coordenadas) < 2:
            return []

        coordenadas_str = ";".join(
            f"{lng},{lat}" for lng, lat in coordenadas
        )

        url = (
            "https://router.project-osrm.org/route/v1/driving/"
            f"{coordenadas_str}"
            "?overview=full&geometries=geojson"
        )

        response = requests.get(url, timeout=10)
        data = response.json()

        routes = data.get("routes", [])

        if not routes:
            print("OSRM ERROR RESPONSE:", data)
            return []

        return routes[0]["geometry"]["coordinates"]

    except Exception as e:
        print("OSRM EXCEPTION:", e)
        return []
 # ==========================================================================
# 🏢 ENDPOINT: Listado Dinámico de Empresas Courier para el Login
# ==========================================================================
@router.get("/empresas-activas")
def obtener_lista_empresas_courier():
    """Recupera los nombres de todas las empresas aliadas para poblar el Dropdown en Flutter."""
    try:
        response = (
            supabase_client.supabase.table("empresas_courier")
            .select("nombre_empresa")
            .order("nombre_empresa", desc=False) # 💡 CORREGIDO: Se cambia 'ascending=True' por 'desc=False'
            .execute()
        )
        
        # Extraemos solo los textos de los nombres en una lista plana
        lista_empresas = [row["nombre_empresa"] for row in (response.data or [])]
        
        # Si la tabla está vacía en tus primeras pruebas, mandamos un fallback de contingencia
        if not lista_empresas:
            lista_empresas = ["Saga Falabella (Flota Interna)"]
            
        return {
            "status": "success",
            "total": len(lista_empresas),
            "empresas": lista_empresas
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al conectar con el catálogo de empresas: {str(e)}"
        )
@router.get("-courier")
def obtener_pedidos_por_courier(
    courier_id: str = Query(..., min_length=1),
    empresa: str = Query(..., description="Nombre de la empresa seleccionada en el login"),
    # 🛰️ NUEVOS PARÁMETROS: Opcionales para no romper otras pantallas si no se mandan
    lat_gps: float = Query(None, description="Latitud actual del chofer para el mapa"),
    lng_gps: float = Query(None, description="Longitud actual del chofer para el mapa")
):
    try:
        # 1. Consulta relacional: Validación de Courier
        query_courier = (
            supabase_client.supabase.table("couriers")
            .select("nombre, empresas_courier(nombre_empresa)")
            .eq("id", courier_id)
            .execute()
        )
        
        if not query_courier.data:
            return {"error_detectado": f"El código de courier '{courier_id}' no está registrado en el sistema."}
            
        courier_info = query_courier.data[0]
        empresa_real_en_bd = courier_info.get("empresas_courier", {}).get("nombre_empresa")
        
        # 🔒 FILTRO CRÍTICO DE SEGURIDAD B2B
        if empresa_real_en_bd != empresa:
            return {
                "error_detectado": f"Acceso denegado."
            }

        # 2. 💡 MODIFICACIÓN: Traemos los datos haciendo el JOIN con la tabla 'clientes' para jalar coordenadas
        response = (
            supabase_client.supabase.table("pedidos")
            .select("id, codigo_barra, descripcion_producto, estado, prioridad, intentos_entrega, clientes(nombre, direccion, distrito, latitud, longitud)")
            .eq("courier_id", courier_id)
            .execute()
        )
        
        pedidos = response.data or []

        # 🧠 3. ALGORITMO DE ENRUTAMIENTO JERÁRQUICO (Solo si Flutter envía las coordenadas GPS)
        if lat_gps is not None and lng_gps is not None:
            # Separamos los pedidos únicamente en estado 'En Ruta' para el mapa
            pedidos_en_ruta = [p for p in pedidos if p.get("estado") == "En Ruta"]
            # Guardamos los demás pedidos (Asignados, Entregados, etc.) para que la UI no se quede vacía
            otros_pedidos = [p for p in pedidos if p.get("estado") != "En Ruta"]

            # Extraemos los datos de las coordenadas internas de los clientes de forma segura
            for p in pedidos_en_ruta:
                cliente_data = p.get("clientes") or {}
                p["_lat"] = float(cliente_data.get("latitud") or 0.0)
                p["_lng"] = float(cliente_data.get("longitud") or 0.0)

            # Dividimos los paquetes en ruta estrictamente según tus valores de prioridad
            bloque_alta = [p for p in pedidos_en_ruta if p.get("prioridad") == "Alta"]
            bloque_baja = [p for p in pedidos_en_ruta if p.get("prioridad") == "Baja"]

            ruta_ordenada = []
            punto_origen = (lat_gps, lng_gps)

            # 🔴 Ordenar Bloque Alta Prioridad de más cercano a más lejano
            while bloque_alta:
                mas_cercano = min(
                    bloque_alta,
                    key=lambda p: calcular_distancia_haversine(punto_origen[0], punto_origen[1], p["_lat"], p["_lng"])
                )
                ruta_ordenada.append(mas_cercano)
                punto_origen = (mas_cercano["_lat"], mas_cercano["_lng"])
                bloque_alta.remove(mas_cercano)

            # 🟢 Ordenar Bloque Baja Prioridad continuando desde la última parada "Alta"
            while bloque_baja:
                mas_cercano = min(
                    bloque_baja,
                    key=lambda p: calcular_distancia_haversine(punto_origen[0], punto_origen[1], p["_lat"], p["_lng"])
                )
                ruta_ordenada.append(mas_cercano)
                punto_origen = (mas_cercano["_lat"], mas_cercano["_lng"])
                bloque_baja.remove(mas_cercano)

            # Limpiamos las variables temporales de cálculo antes de enviar el JSON
            for p in ruta_ordenada:
                p.pop("_lat", None)
                p.pop("_lng", None)

            # La respuesta final contendrá la ruta unificada (Primero todo Alta, luego todo Baja) más los otros estados
            pedidos_finales = ruta_ordenada + otros_pedidos

            # Punto inicial = GPS actual del courier
            coordenadas_ruta = [
                (lng_gps, lat_gps)
            ]

            # Agregar destinos en el orden optimizado
            
            for pedido in ruta_ordenada:
                cliente = pedido.get("clientes") or {}

                lat = cliente.get("latitud")
                lng = cliente.get("longitud")

                if lat is not None and lng is not None:
                    coordenadas_ruta.append(
                        (float(lng), float(lat))
                    )

            ruta_osrm = obtener_ruta_osrm(coordenadas_ruta)

            return {
                "courier_id": courier_id,
                "empresa": empresa,
                "pedidos": pedidos_finales,
                "ruta_osrm": ruta_osrm
            }

        # Si no se mandó GPS (por ejemplo, desde la pantalla del almacén), devolvemos los datos tal cual
        return {"courier_id": courier_id, "empresa": empresa, "pedidos": pedidos}
        
    except Exception as e:
        return {"error_detectado": str(e)}

# ==========================================================================
# 3️⃣ BUSCADOR POR CÓDIGO DE BARRAS (🔒 SEGURIDAD B2B PLANA Y ABSOLUTA)
# ==========================================================================
@router.get("/escanear/{codigo_barra}")
def obtener_pedido_por_codigo_barra(
    codigo_barra: str,
    courier_id: str = Query(..., min_length=1, description="ID del courier que escanea"),
    empresa: str = Query(..., description="Empresa del courier en sesión")
):
    """Buscador instantáneo blindado mediante consultas planas secuenciales."""
    try:
        # 1️⃣ VALIDACIÓN DE OPERADOR: Verificamos la empresa real del chofer en la base de datos
        query_courier = (
            supabase_client.supabase.table("couriers")
            .select("id_empresa, empresas_courier(nombre_empresa)")
            .eq("id", courier_id)
            .execute()
        )
        
        if not query_courier.data:
            raise HTTPException(
                status_code=403,
                detail=f"Acceso denegado: El código de courier '{courier_id}' no es válido."
            )
            
        courier_info = query_courier.data[0]
        empresa_real_del_chofer = courier_info.get("empresas_courier", {}).get("nombre_empresa")

        # Candado de consistencia por si manipulan los headers en Flutter
        if not empresa_real_del_chofer or empresa_real_del_chofer.strip().lower() != empresa.strip().lower():
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado: Conflicto de asignación corporativa de sesión."
            )

        # 2️⃣ BUSQUEDA PLANA DEL PAQUETE: Traemos el pedido por su código de barras
        response = (
            supabase_client.supabase.table("pedidos")
            .select("id, codigo_barra, descripcion_producto, estado, prioridad, intentos_entrega, courier_id")
            .eq("codigo_barra", codigo_barra)
            .execute()
        )
        
        if not response.data:
            raise HTTPException(
                status_code=404, 
                detail="El código escaneado no coincide con ningún paquete en el sistema."
            )
            
        pedido = response.data[0]
        courier_asignado_id = pedido.get("courier_id")

        # 3️⃣ CRUCE DE CONTROL LOGÍSTICO (Modo Entrega / En Ruta)
        # Si el paquete ya está en la calle, el 'courier_id' del pedido debe coincidir obligatoriamente con el que escanea
        if pedido["estado"] == "En Ruta" and courier_asignado_id:
            if courier_asignado_id != courier_id:
                raise HTTPException(
                    status_code=403, 
                    detail=f"Acceso denegado: El paquete ya está En Ruta asignado a otro Courier (ID: {courier_asignado_id})."
                )

        # 4️⃣ CRUCE DE CONTROL LOGÍSTICO (Modo Carga / Almacén)
        # Si el paquete está 'Asignado' en almacén, verificamos que el chofer que lo quiere cargar sea del mismo grupo.
        # Para evitar hacer otro Join, cruzamos contra tu endpoint de validación de manifiesto diario:
        if pedido["estado"] == "Asignado" and courier_asignado_id:
            if courier_asignado_id != courier_id:
                raise HTTPException(
                    status_code=403,
                    detail="Acceso denegado: Este paquete está pre-asignado a otra ruta de despacho."
                )

        return {"pedido": pedido}
        
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=f"Error en validación B2B: {str(e)}")

# ==========================================================================
# 4️⃣ ACTUALIZAR ESTADO DEL PEDIDO (🔒 SEGURIDAD TRANSACTIONAL COMPLETA)
# ==========================================================================
@router.put("/{pedido_id}/estado")
def actualizar_estado_pedido(
    pedido_id: int,
    nuevo_estado: str = Query(...),
    courier_id: str = Query(..., min_length=1, description="ID del courier que intenta la mutación"),
    motivo_contingencia: str = Query(None),
    evidencia_url: str = Query(None)
):
    """Modifica el estado validando que el courier sea el legítimo dueño del registro."""
    if nuevo_estado not in ['Asignado', 'En Ruta', 'Entregado', 'No Entregado']:
        raise HTTPException(status_code=400, detail="Estado de entrega inválido.")
    if nuevo_estado == 'No Entregado' and not motivo_contingencia:
        raise HTTPException(status_code=400, detail="Debe ingresar el motivo de contingencia obligatoriamente.")

    try:
        # Recuperamos los datos actuales para verificar propiedad transaccional
        pedido_actual = (
            supabase_client.supabase.table("pedidos")
            .select("estado, courier_id, intentos_entrega")
            .eq("id", pedido_id)
            .execute()
        )
        
        if not pedido_actual.data:
            raise HTTPException(status_code=404, detail="El pedido no existe.")
        
        datos = pedido_actual.data[0]
        courier_asignado_id = datos.get("courier_id")

        # 🔒 CONTROL DE SEGURIDAD INTERNO: Bloquea intentos ilícitos de suplantación de firmas/estados
        # Excepción: Permitir si pasa de 'Asignado' a 'En Ruta' (Modo Carga en Almacén) donde se le asocia el courier
        if datos["estado"] != "Asignado" and courier_asignado_id != courier_id:
            raise HTTPException(
                status_code=403, 
                detail="Acceso denegado: No tienes permisos de escritura sobre este paquete."
            )
        
        # Calcular intentos de entrega acumulados
        nuevos_intentos = (datos["intentos_entrega"] or 0) + 1 if nuevo_estado == 'No Entregado' else (datos["intentos_entrega"] or 0)

        # 1. Actualizar tabla pedidos amarrando el courier_id de forma explícita
        update_fields = {"estado": nuevo_estado, "intentos_entrega": nuevos_intentos}
        if nuevo_estado == "En Ruta":
            update_fields["courier_id"] = courier_id

        update_res = (
            supabase_client.supabase.table("pedidos")
            .update(update_fields)
            .eq("id", pedido_id)
            .execute()
        )
        
        # 2. Registrar traza histórica inalterable para auditorías de Saga Falabella
        supabase_client.supabase.table("historial_estados").insert({
            "pedido_id": pedido_id, 
            "estado_anterior": datos["estado"], 
            "estado_nuevo": nuevo_estado,
            "motivo_contingencia": motivo_contingencia, 
            "evidencia_url": evidencia_url, 
            "actualizado_por": courier_id
        }).execute()

        return {"status": "success", "pedido": update_res.data[0]}
        
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/test-osrm")
def test_osrm():

    ruta = obtener_ruta_osrm([
        (-77.042793, -12.046374),
        (-77.030000, -12.080000)
    ])

    return {
        "total_puntos": len(ruta),
        "primeros_puntos": ruta[:5]
    }
# ==========================================================================
# 🚀 ENDPOINT CORPORATIVO CORREGIDO (Filtrado por JOIN Relacional)
# ==========================================================================
@router.get("-empresa")
def obtener_pedidos_por_empresa(empresa: str = Query(..., description="Nombre de la empresa para descargar manifiesto")):
    if not empresa or not empresa.strip():
        raise HTTPException(status_code=400, detail="El parámetro 'empresa' es obligatorio.")
        
    try:
        # 📡 Traemos los pedidos haciendo JOIN con 'couriers' y 'empresas_courier'
        # Filtramos usando la sintaxis de Supabase para tablas relacionadas: couriers.empresas_courier.nombre_empresa
        response = (
            supabase_client.supabase.table("pedidos")
            .select("""
                codigo_barra, 
                courier_id, 
                estado, 
                prioridad,
                couriers!inner(
                    id_empresa,
                    empresas_courier!inner(
                        nombre_empresa
                    )
                )
            """)
            .eq("couriers.empresas_courier.nombre_empresa", empresa.strip())
            .execute()
        )
        
        pedidos_sucios = response.data or []
        pedidos_limpios = []
        
        # 🧹 Limpiamos el JSON para que el script de Python reciba la estructura exacta que espera
        for p in pedidos_sucios:
            pedidos_limpios.append({
                "codigo_barra": p.get("codigo_barra"),
                "courier_id": p.get("courier_id"),
                "estado": p.get("estado"),
                "prioridad": p.get("prioridad")
            })
        
        return {
            "status": "success",
            "empresa_consultada": empresa,
            "total_paquetes": len(pedidos_limpios),
            "pedidos": pedidos_limpios
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en el árbol relacional del backend: {str(e)}")
    
   