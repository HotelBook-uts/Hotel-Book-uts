"""Pruebas de HU-008, HU-009, HU-010 y HU-012 (módulo Habitación)."""
import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

HOTEL_INEXISTENTE = 999999
HABITACION_INEXISTENTE = 999999


def _datos(resp):
    """Devuelve el contenido útil, con o sin envoltorio {"data": ...}."""
    cuerpo = resp.json()
    if isinstance(cuerpo, dict) and "data" in cuerpo:
        return cuerpo["data"]
    return cuerpo


def _crear_hotel():
    """Crea un hotel con nombre único para que las pruebas no se pisen."""
    r = client.post("/hoteles/", json={
        "nombre": f"Hotel Prueba {uuid.uuid4().hex[:8]}",
        "ciudad": "Bucaramanga",
        "direccion": "Calle 47 # 28-02",
        "estrellas": 4,
        "precio_noche": 300000,
    })
    assert r.status_code == 201, f"No se pudo crear el hotel: {r.status_code} {r.text}"
    return _datos(r)["id"]


def _habitacion(hotel_id, numero="101", **cambios):
    cuerpo = {"hotel_id": hotel_id, "numero": numero, "tipo": "doble",
              "capacidad": 2, "precio_noche": 180000, "disponible": True}
    cuerpo.update(cambios)
    return cuerpo


# ------------------------- HU-008: registro de habitación -------------------------

def test_hu008_crear_habitacion_201():
    hotel_id = _crear_hotel()
    r = client.post("/habitaciones/", json=_habitacion(hotel_id, "10a"))
    assert r.status_code == 201
    datos = _datos(r)
    assert datos["id"] > 0
    assert datos["numero"] == "10A"  # el número se normaliza a mayúscula


def test_hu008_numero_repetido_en_el_hotel_409():
    hotel_id = _crear_hotel()
    assert client.post("/habitaciones/", json=_habitacion(hotel_id)).status_code == 201
    assert client.post("/habitaciones/", json=_habitacion(hotel_id)).status_code == 409


def test_hu008_mismo_numero_en_otro_hotel_201():
    h1, h2 = _crear_hotel(), _crear_hotel()
    assert client.post("/habitaciones/", json=_habitacion(h1)).status_code == 201
    assert client.post("/habitaciones/", json=_habitacion(h2)).status_code == 201


def test_hu008_hotel_inexistente_404():
    r = client.post("/habitaciones/", json=_habitacion(HOTEL_INEXISTENTE))
    assert r.status_code == 404


def test_hu008_tipo_invalido_422():
    hotel_id = _crear_hotel()
    r = client.post("/habitaciones/", json=_habitacion(hotel_id, "102", tipo="familiar"))
    assert r.status_code == 422


def test_hu008_capacidad_fuera_de_rango_422():
    hotel_id = _crear_hotel()
    r = client.post("/habitaciones/", json=_habitacion(hotel_id, "103", capacidad=0))
    assert r.status_code == 422


# ------------------------- HU-009: consulta de habitaciones -------------------------

def test_hu009_listar_por_hotel():
    hotel_id = _crear_hotel()
    client.post("/habitaciones/", json=_habitacion(hotel_id, "201"))
    client.post("/habitaciones/", json=_habitacion(hotel_id, "202"))
    r = client.get("/habitaciones/", params={"hotel_id": hotel_id})
    assert r.status_code == 200
    assert len(_datos(r)) == 2


def test_hu009_hotel_sin_habitaciones_lista_vacia():
    hotel_id = _crear_hotel()
    r = client.get("/habitaciones/", params={"hotel_id": hotel_id})
    assert r.status_code == 200
    assert _datos(r) == []


def test_hu009_filtrar_por_disponibilidad():
    hotel_id = _crear_hotel()
    client.post("/habitaciones/", json=_habitacion(hotel_id, "301", disponible=True))
    client.post("/habitaciones/", json=_habitacion(hotel_id, "302", disponible=False))
    r = client.get("/habitaciones/", params={"hotel_id": hotel_id, "disponible": True})
    assert r.status_code == 200
    habitaciones = _datos(r)
    assert len(habitaciones) == 1
    assert habitaciones[0]["numero"] == "301"


# ------------------------- HU-010: consulta de una habitación -------------------------

def test_hu010_consultar_por_id_200():
    hotel_id = _crear_hotel()
    creada = _datos(client.post("/habitaciones/", json=_habitacion(hotel_id, "401")))
    r = client.get(f"/habitaciones/{creada['id']}")
    assert r.status_code == 200
    assert _datos(r)["numero"] == "401"


def test_hu010_id_inexistente_404():
    assert client.get(f"/habitaciones/{HABITACION_INEXISTENTE}").status_code == 404


# ------------------------- HU-012: administración de habitaciones -------------------------

def test_hu012_actualizar_200():
    hotel_id = _crear_hotel()
    creada = _datos(client.post("/habitaciones/", json=_habitacion(hotel_id, "501")))
    r = client.put(f"/habitaciones/{creada['id']}",
                   json=_habitacion(hotel_id, "501", precio_noche=200000))
    assert r.status_code == 200
    assert _datos(r)["precio_noche"] == 200000
    # el cambio quedó guardado
    assert _datos(client.get(f"/habitaciones/{creada['id']}"))["precio_noche"] == 200000


def test_hu012_actualizar_inexistente_404():
    hotel_id = _crear_hotel()
    r = client.put(f"/habitaciones/{HABITACION_INEXISTENTE}", json=_habitacion(hotel_id))
    assert r.status_code == 404


def test_hu012_actualizar_con_hotel_inexistente_404():
    hotel_id = _crear_hotel()
    creada = _datos(client.post("/habitaciones/", json=_habitacion(hotel_id, "502")))
    r = client.put(f"/habitaciones/{creada['id']}", json=_habitacion(HOTEL_INEXISTENTE, "502"))
    assert r.status_code == 404


def test_hu012_eliminar_200_y_luego_404():
    hotel_id = _crear_hotel()
    creada = _datos(client.post("/habitaciones/", json=_habitacion(hotel_id, "503")))
    assert client.delete(f"/habitaciones/{creada['id']}").status_code == 200
    assert client.get(f"/habitaciones/{creada['id']}").status_code == 404
    assert client.delete(f"/habitaciones/{creada['id']}").status_code == 404


# ------------------------- Ejecución directa (sin pytest) -------------------------

if __name__ == "__main__":
    import sys

    pruebas = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_")]
    fallas = 0
    for nombre, prueba in pruebas:
        try:
            prueba()
            print(f"[OK]    {nombre}")
        except AssertionError as error:
            fallas += 1
            print(f"[FALLA] {nombre}: {error}")
    print(f"\n{len(pruebas) - fallas} de {len(pruebas)} pruebas correctas")
    sys.exit(1 if fallas else 0)