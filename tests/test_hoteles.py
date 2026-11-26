"""Pruebas de HU-006, HU-007, HU-011 y HU-015 (módulo Hotel)."""
import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

HOTEL_INEXISTENTE = 999999


def _datos(resp):
    """Devuelve el contenido útil, con o sin envoltorio {"data": ...}."""
    cuerpo = resp.json()
    if isinstance(cuerpo, dict) and "data" in cuerpo:
        return cuerpo["data"]
    return cuerpo


def _hotel(**cambios):
    """Cuerpo de un hotel válido, con nombre único para que las pruebas no se pisen."""
    cuerpo = {
        "nombre": f"Hotel Prueba {uuid.uuid4().hex[:8]}",
        "ciudad": "Bucaramanga",
        "direccion": "Calle 47 # 28-02",
        "estrellas": 4,
        "precio_noche": 300000,
    }
    cuerpo.update(cambios)
    return cuerpo


# ------------------------- HU-006: registro de hotel -------------------------

def test_hu006_crear_hotel_201():
    r = client.post("/hoteles/", json=_hotel())
    assert r.status_code == 201
    assert _datos(r)["id"] > 0


def test_hu006_normaliza_nombre_y_ciudad():
    uid = uuid.uuid4().hex[:8]
    r = client.post("/hoteles/", json=_hotel(nombre=f"  hotel {uid}  ", ciudad="  bucaramanga "))
    assert r.status_code == 201
    datos = _datos(r)
    assert datos["nombre"] == datos["nombre"].strip()
    assert datos["nombre"].startswith("Hotel ")
    assert datos["ciudad"] == "Bucaramanga"


def test_hu006_redondea_precio_a_dos_decimales():
    r = client.post("/hoteles/", json=_hotel(precio_noche=350000.456))
    assert r.status_code == 201
    assert _datos(r)["precio_noche"] == 350000.46


def test_hu006_hotel_repetido_en_la_ciudad_409():
    cuerpo = _hotel()
    assert client.post("/hoteles/", json=cuerpo).status_code == 201
    assert client.post("/hoteles/", json=cuerpo).status_code == 409


def test_hu006_mismo_nombre_en_otra_ciudad_201():
    cuerpo = _hotel()
    assert client.post("/hoteles/", json=cuerpo).status_code == 201
    assert client.post("/hoteles/", json={**cuerpo, "ciudad": "Cartagena"}).status_code == 201


def test_hu006_estrellas_fuera_de_rango_422():
    assert client.post("/hoteles/", json=_hotel(estrellas=6)).status_code == 422
    assert client.post("/hoteles/", json=_hotel(estrellas=0)).status_code == 422


def test_hu006_precio_invalido_422():
    assert client.post("/hoteles/", json=_hotel(precio_noche=0)).status_code == 422


def test_hu006_faltan_campos_422():
    assert client.post("/hoteles/", json={"nombre": "Hotel Incompleto"}).status_code == 422


# ------------------------- HU-007: consulta de hotel -------------------------

def test_hu007_consultar_por_id_200():
    creado = _datos(client.post("/hoteles/", json=_hotel()))
    r = client.get(f"/hoteles/{creado['id']}")
    assert r.status_code == 200
    assert _datos(r)["nombre"] == creado["nombre"]


def test_hu007_id_inexistente_404():
    assert client.get(f"/hoteles/{HOTEL_INEXISTENTE}").status_code == 404


# ------------------------- HU-011: registro y actualización -------------------------

def test_hu011_actualizar_200():
    cuerpo = _hotel()
    creado = _datos(client.post("/hoteles/", json=cuerpo))
    r = client.put(f"/hoteles/{creado['id']}", json={**cuerpo, "precio_noche": 400000, "estrellas": 5})
    assert r.status_code == 200
    assert _datos(r)["precio_noche"] == 400000
    # el cambio quedó guardado
    guardado = _datos(client.get(f"/hoteles/{creado['id']}"))
    assert guardado["precio_noche"] == 400000
    assert guardado["estrellas"] == 5


def test_hu011_actualizar_inexistente_404():
    assert client.put(f"/hoteles/{HOTEL_INEXISTENTE}", json=_hotel()).status_code == 404


def test_hu011_actualizar_con_datos_invalidos_422():
    creado = _datos(client.post("/hoteles/", json=_hotel()))
    r = client.put(f"/hoteles/{creado['id']}", json=_hotel(estrellas=9))
    assert r.status_code == 422


def test_hu011_eliminar_200_y_luego_404():
    creado = _datos(client.post("/hoteles/", json=_hotel()))
    assert client.delete(f"/hoteles/{creado['id']}").status_code == 200
    assert client.get(f"/hoteles/{creado['id']}").status_code == 404
    assert client.delete(f"/hoteles/{creado['id']}").status_code == 404


# ------------------------- HU-015: catálogo y ficha de hoteles -------------------------

def test_hu015_listar_catalogo_200():
    client.post("/hoteles/", json=_hotel())
    r = client.get("/hoteles/")
    assert r.status_code == 200
    assert len(_datos(r)) >= 1


def test_hu015_filtrar_por_ciudad():
    ciudad = f"Ciudad{uuid.uuid4().hex[:6]}"
    client.post("/hoteles/", json=_hotel(ciudad=ciudad))
    client.post("/hoteles/", json=_hotel(ciudad=ciudad))
    client.post("/hoteles/", json=_hotel(ciudad="Cartagena"))
    r = client.get("/hoteles/", params={"ciudad": ciudad})
    assert r.status_code == 200
    hoteles = _datos(r)
    assert len(hoteles) == 2
    assert all(h["ciudad"].lower() == ciudad.lower() for h in hoteles)


def test_hu015_ciudad_sin_hoteles_lista_vacia():
    r = client.get("/hoteles/", params={"ciudad": "CiudadQueNoExiste"})
    assert r.status_code == 200
    assert _datos(r) == []


def test_hu015_ficha_incluye_los_datos_del_hotel():
    cuerpo = _hotel()
    creado = _datos(client.post("/hoteles/", json=cuerpo))
    ficha = _datos(client.get(f"/hoteles/{creado['id']}"))
    for campo in ("id", "nombre", "ciudad", "direccion", "estrellas", "precio_noche"):
        assert campo in ficha


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