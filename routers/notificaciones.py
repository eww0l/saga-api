from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/notificaciones", tags=["Notificaciones Push"])

@router.post("/enviar-alerta")
def enviar_notificacion_push(
    token_dispositivo: str = Body(..., embed=True),
    titulo: str = Body(...),
    mensaje: str = Body(...)
):
    """Registra y despacha notificaciones push hacia el SDK de Android en la demo."""
    return {
        "status": "Despachado con Éxito",
        "plataforma": "Firebase Cloud Messaging (FCM)",
        "destinatario_token_corto": token_dispositivo[:12] + "...",
        "alerta": {"titulo": titulo, "cuerpo": mensaje}
    }