"""
tests/test_app.py
Pruebas automáticas de la app con el cliente de pruebas de Flask.

El cliente de Flask simula un navegador: hace peticiones a las rutas sin abrir
la aplicación ni levantar un servidor de verdad.

Las credenciales se definen aquí, ANTES de importar la app, para que las pruebas
no dependan del archivo .env de cada máquina.
"""

import io
import os
import re
import sys
from pathlib import Path

# --- Variables de entorno de prueba (antes de crear la app) ---
# VARIABLES de tipo str: usuarios ficticios solo para las pruebas.
os.environ["ADMIN_CORREO"] = "admin@prueba.cr"
os.environ["ADMIN_CLAVE"] = "clave-admin-prueba"
os.environ["USUARIO_CORREO"] = "usuario@prueba.cr"
os.environ["USUARIO_CLAVE"] = "clave-usuario-prueba"
os.environ["SECRET_KEY"] = "clave-de-sesion-para-pruebas"

# VARIABLE de tipo Path: raíz del proyecto, para encontrar app.py e Insumos/.
RAIZ = Path(__file__).resolve().parent.parent
# FUNCIÓN: agrego la raíz al camino de búsqueda para poder importar app.
sys.path.insert(0, str(RAIZ))

import openpyxl  # VARIABLE: openpyxl lee y escribe los Excel de prueba.
import app as aplicacion  # VARIABLE: la app que voy a probar.

# VARIABLES de tipo Path: los Excel originales de la bodega (solo se leen).
RUTA_MAESTRO = RAIZ / "Insumos" / "Maestro_Estudiantes.xlsx"
RUTA_EVALUACIONES = RAIZ / "Insumos" / "Registro_Evaluaciones.xlsx"


# FUNCIÓN: inicia sesión con las credenciales indicadas y devuelve el cliente.
def entrar_como(correo, clave):
    cliente = aplicacion.app.test_client()
    cliente.post("/login", data={"correo": correo, "clave": clave})
    return cliente


# FUNCIÓN: busca en el HTML el número de una tarjeta de contador.
def leer_contador(texto, clase_tarjeta):
    # VARIABLE de tipo str: patrón de la tarjeta, por ejemplo "tarjeta verde".
    patron = r'<div class="tarjeta ' + clase_tarjeta + r'"><span class="numero">(\d+)</span>'
    encontrado = re.search(patron, texto)
    return int(encontrado.group(1)) if encontrado else None


# FUNCIÓN: arma en memoria un Registro_Evaluaciones con Camila en 40.
def evaluaciones_con_camila_en_40():
    # FUNCIÓN: abro el Excel original, pero en memoria (el archivo del disco no se toca).
    libro = openpyxl.load_workbook(RUTA_EVALUACIONES)
    hoja = libro["Evaluaciones"]
    # BUCLE: recorro cada fila y cambio solo las notas de la identificación 101230456.
    for fila in hoja.iter_rows(min_row=2):
        if str(fila[0].value).strip() == "101230456":
            fila[3].value = 40  # COLUMNA D: Nota.
    # BytesIO es como una caja de cartón en la memoria: guardo el Excel ahí
    # como si fuera una memoria USB, pero sin escribir en el disco.
    memoria = io.BytesIO()
    libro.save(memoria)
    memoria.seek(0)
    return memoria


def test_sin_sesion_redirige_a_login():
    """Simula a alguien que abre la raíz sin haber entrado: debe ir a /login."""
    cliente = aplicacion.app.test_client()
    respuesta = cliente.get("/")
    # CONDICIONAL esperado: la app responde con una redirección.
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_clave_incorrecta_no_entra():
    """Simula un intento de entrada con clave equivocada: sigue en la pantalla de entrada."""
    cliente = aplicacion.app.test_client()
    respuesta = cliente.post(
        "/login",
        data={"correo": "admin@prueba.cr", "clave": "esta-clave-es-mala"},
    )
    texto = respuesta.get_data(as_text=True)
    # CONDICIONAL esperado: se queda en la misma pantalla, con el mensaje rojo.
    assert respuesta.status_code == 200
    assert "Correo o contraseña incorrectos." in texto
    # Y no quedó sesión: la raíz vuelve a mandar al login.
    assert cliente.get("/").status_code == 302


def test_usuario_no_puede_cargar():
    """Simula a un usuario normal pidiendo la ruta de carga: debe recibir 403."""
    cliente = entrar_como("usuario@prueba.cr", "clave-usuario-prueba")
    respuesta = cliente.post(
        "/cargar",
        data={"accion": "ver"},
        content_type="multipart/form-data",
    )
    # CONDICIONAL esperado: prohibido, aunque conozca la dirección.
    assert respuesta.status_code == 403


def test_excel_modificado_cambia_contadores():
    """Simula al admin subiendo evaluaciones con Camila en 40: cambian los contadores."""
    cliente = entrar_como("admin@prueba.cr", "clave-admin-prueba")

    # VARIABLE: el maestro de estudiantes tal cual, leído como bytes.
    datos_maestro = RUTA_MAESTRO.read_bytes()
    # VARIABLE: las evaluaciones modificadas, armadas en memoria.
    datos_evaluaciones = evaluaciones_con_camila_en_40()

    respuesta = cliente.post(
        "/cargar",
        data={
            "accion": "ver",
            "maestro": (io.BytesIO(datos_maestro), "Maestro_Estudiantes.xlsx"),
            "evaluaciones": (datos_evaluaciones, "Registro_Evaluaciones.xlsx"),
        },
        content_type="multipart/form-data",
    )
    texto = respuesta.get_data(as_text=True)

    # CONDICIONAL esperado: la app responde bien y muestra el aviso de datos subidos.
    assert respuesta.status_code == 200
    assert "viven solo en esta pantalla" in texto

    # CONDICIONAL esperado: Camila baja de Aprobación a Participación.
    assert leer_contador(texto, "verde") == 18
    assert leer_contador(texto, "azul") == 4
    assert leer_contador(texto, "roja") == 1
