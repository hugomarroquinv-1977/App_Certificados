# app.py — LA COCINA de Academia Horizonte.
# Toda la lógica vive aquí. El HTML (salón) solo muestra lo ya calculado.
# Baldosas usadas abajo: variables, tipos, condicionales, bucles y funciones.
from collections import defaultdict  # VARIABLE: defaultdict es un tipo diccionario con valor por defecto.
from pathlib import Path  # VARIABLE: Path es un tipo para rutas de archivos.
from flask import Flask, render_template, request  # VARIABLE: Flask crea la app, render_template dibuja el HTML.
import openpyxl  # VARIABLE: openpyxl es la librería para leer los Excel.

# VARIABLE de tipo Path: carpeta donde vive app.py, para encontrar Insumos/ desde donde sea.
BASE_DIR = Path(__file__).resolve().parent
# VARIABLES de tipo Path con las rutas de la bodega (solo lectura, NO modificar).
RUTA_MAESTRO = BASE_DIR / "Insumos" / "Maestro_Estudiantes.xlsx"
RUTA_EVALS = BASE_DIR / "Insumos" / "Registro_Evaluaciones.xlsx"

# VARIABLE de tipo Flask: la aplicación web.
app = Flask(__name__)


# FUNCIÓN: calcula el promedio de una lista de números.
def calcular_promedio(valores):
    # VARIABLE de tipo float: acumulador donde sumo uno por uno.
    total = 0.0
    # BUCLE: recorro cada valor de la lista.
    for v in valores:
        total = total + float(v)
    # CONDICIONAL: si la lista está vacía, devuelvo 0 para no dividir entre cero.
    if len(valores) == 0:
        return 0.0
    return total / len(valores)


# FUNCIÓN: decide el certificado según AGENTS.md (límites INCLUYEN el valor).
def decidir_certificado(promedio, asistencia):
    # CONDICIONAL 1: la asistencia manda; si es menor a 80 no hay certificado.
    if asistencia < 80:
        return "Sin certificado"
    # CONDICIONAL 2: con asistencia suficiente, el promedio decide.
    elif promedio >= 70:
        return "Aprobación"
    # CONDICIONAL 3 (caso restante): buena asistencia pero nota menor a 70.
    else:
        return "Participación"


# FUNCIÓN: lee los Excel y deja todo calculado para las páginas.
def cargar_datos():
    # --- Maestro: lista oficial (VARIABLE de tipo lista de dicts). ---
    wb_m = openpyxl.load_workbook(RUTA_MAESTRO, data_only=True)
    ws_m = wb_m["Estudiantes"]
    maestro = {}  # VARIABLE de tipo dict: clave (id, programa) -> datos del estudiante.
    # BUCLE: salto el encabezado (fila 1) y leo cada fila.
    for fila in ws_m.iter_rows(min_row=2, values_only=True):
        sid = str(fila[0])  # VARIABLE de tipo str: el ID siempre como texto.
        maestro[(sid, fila[3])] = {
            "id": sid, "nombre": fila[1], "correo": fila[2],
            "programa": fila[3], "cohorte": str(fila[4]),
        }

    # --- Evaluaciones agrupadas por Identificacion + Programa. ---
    wb_e = openpyxl.load_workbook(RUTA_EVALS, data_only=True)
    ws_e = wb_e["Evaluaciones"]
    grupos = defaultdict(list)  # VARIABLE de tipo dict: clave (id, programa) -> lista de filas.
    # BUCLE: junto cada fila de nota/asistencia en su grupo.
    for fila in ws_e.iter_rows(min_row=2, values_only=True):
        sid = str(fila[0])
        grupos[(sid, fila[1])].append(fila)

    # --- Cruce y cálculo (un grupo = un posible certificado). ---
    resultados = []  # VARIABLE de tipo lista: lo que verá la tabla.
    # BUCLE: proceso cada grupo con las dos FUNCIONES de arriba.
    for (sid, programa), filas in grupos.items():
        # CONDICIONAL: el huérfano (sin maestro) no entra a la tabla, va a inconsistencias.
        if (sid, programa) not in maestro:
            continue
        notas = [float(f[3]) for f in filas]  # VARIABLE de tipo lista de float.
        asists = [float(f[4]) for f in filas]
        promedio = calcular_promedio(notas)  # FUNCIÓN.
        asistencia = calcular_promedio(asists)  # FUNCIÓN reutilizada.
        tipo = decidir_certificado(promedio, asistencia)  # FUNCIÓN con CONDICIONALES.
        resultados.append({
            "id": sid, "nombre": maestro[(sid, programa)]["nombre"],
            "programa": programa, "modulos": len(filas),
            "promedio": round(promedio, 2), "asistencia": round(asistencia, 2),
            "tipo": tipo,
        })
    # Orden para la tabla: programa y nombre.
    resultados.sort(key=lambda r: (r["programa"], r["nombre"]))

    # --- Contadores de arriba (VARIABLES de tipo int). ---
    contadores = {"Aprobación": 0, "Participación": 0, "Sin certificado": 0}
    # BUCLE con CONDICIONALES: cuento cada tipo.
    for r in resultados:
        if r["tipo"] == "Aprobación":
            contadores["Aprobación"] = contadores["Aprobación"] + 1
        elif r["tipo"] == "Participación":
            contadores["Participación"] = contadores["Participación"] + 1
        else:
            contadores["Sin certificado"] = contadores["Sin certificado"] + 1

    # --- Inconsistencias (las 3 detectadas). ---
    sin_evaluacion = [m for clave, m in maestro.items() if clave not in grupos]
    huerfanos = []  # evaluaciones sin maestro.
    # BUCLE: reviso cada grupo buscando al que no tiene ficha en el maestro.
    for (sid, programa), filas in grupos.items():
        # CONDICIONAL: si no está en el maestro, lo guardo como huérfano.
        if (sid, programa) not in maestro:
            notas_h = [float(f[3]) for f in filas]
            huerfanos.append({"id": sid, "programa": programa,
                              "filas": len(filas),
                              "promedio": round(calcular_promedio(notas_h), 2)})
    con_ceros = []  # caso con notas en 0 para revisión (posible abandono).
    # BUCLE con CONDICIONAL: busco resultados con algún 0 en sus notas.
    for (sid, programa), filas in grupos.items():
        # CONDICIONAL: solo miro grupos válidos (con maestro).
        if (sid, programa) in maestro:
            notas = [float(f[3]) for f in filas]
            tiene_cero = False
            # BUCLE: reviso nota por nota.
            for n in notas:
                # CONDICIONAL: marco si alguna nota es cero.
                if n == 0:
                    tiene_cero = True
            if tiene_cero:
                con_ceros.append({"id": sid,
                                  "nombre": maestro[(sid, programa)]["nombre"],
                                  "programa": programa})
    inconsistencias = {"sin_evaluacion": sin_evaluacion,
                       "huerfanos": huerfanos, "con_ceros": con_ceros}

    programas = sorted(set(m["programa"] for m in maestro.values()))
    return resultados, contadores, inconsistencias, programas


# VARIABLE de tipo tupla: datos listos una sola vez al arrancar.
RESULTADOS, CONTADORES, INCONSISTENCIAS, PROGRAMAS = cargar_datos()


# Ruta principal: contadores + filtro + tabla + inconsistencias.
@app.route("/")
def index():
    # VARIABLE de tipo str: lo que eligió el filtro (o "Todos").
    elegido = request.args.get("programa", "Todos")
    # CONDICIONAL: si eligió un programa, filtro la tabla; si no, muestro todo.
    if elegido == "Todos":
        tabla = RESULTADOS
    else:
        tabla = [r for r in RESULTADOS if r["programa"] == elegido]
    return render_template("index.html", tabla=tabla, contadores=CONTADORES,
                           inconsistencias=INCONSISTENCIAS, programas=PROGRAMAS,
                           elegido=elegido)


# Ruta detalle: un certificado por estudiante (solo muestra, no calcula).
@app.route("/certificado/<sid>")
def certificado(sid):
    # BUCLE con CONDICIONAL: busco al estudiante por su ID.
    encontrado = None
    for r in RESULTADOS:
        if r["id"] == str(sid):
            encontrado = r
    # CONDICIONAL: si no existe, muestro la página de aviso.
    if encontrado is None:
        return render_template("sin_certificado.html", sid=sid)
    return render_template("certificado.html", r=encontrado)


if __name__ == "__main__":
    # Arranco el salón en http://localhost:5000
    app.run(debug=True)
