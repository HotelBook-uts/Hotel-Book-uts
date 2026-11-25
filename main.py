from fastapi import FastAPI
from app.api.auth_router import router as auth_router
from app.api.hotel_router import router as hotel_router
from app.api.usuario_router import router as usuario_router
from app.api.habitacion_router import router as habitacion_router
from app.api.reserva_router import historial_router, router as reserva_router
from app.api.validacion import ErrorAPI, manejar_error_api

app = FastAPI(
    title="Hotel-Book",
    description="Web Service para la gestión de reservas de hotel",
    version="1.0.0"
)
# Errores de sesión y permisos con el formato {mensaje, data, success}
app.add_exception_handler(ErrorAPI, manejar_error_api)

app.include_router(auth_router)
app.include_router(hotel_router)
app.include_router(usuario_router)
app.include_router(habitacion_router)
app.include_router(reserva_router)
app.include_router(historial_router)


@app.get("/")
def inicio():
    return {"mensaje": "Web Service funcionando correctamente"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
