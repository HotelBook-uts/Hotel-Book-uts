from fastapi import FastAPI
from app.api.hotel_router import router as hotel_router
from app.api.usuario_router import router as usuario_router
from app.api.habitacion_router import router as habitacion_router
from app.api.reserva_router import router as reserva_router

app = FastAPI(
    title="Hotel-Book",
    description="Web Service para la gestión de reservas de hotel",
    version="1.0.0"
)
app.include_router(hotel_router)
app.include_router(usuario_router)
app.include_router(habitacion_router)
app.include_router(reserva_router)


@app.get("/")
def inicio():
    return {"mensaje": "Web Service funcionando correctamente"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
