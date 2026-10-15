"""
controllers/rutas.py
Capa de Controlador

Define las rutas de Flask de la aplicación.
Los controladores solo coordinan: reciben solicitudes HTTP, llaman a los modelos
y servicios, y pasan los datos a las vistas (Jinja). Nunca realizan cálculos
de negocio directamente.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.certificados import obtener_resumen_certificados
from services.carga_excel import cargar_datos_desde_excel

rutas = Blueprint("rutas", __name__)


@rutas.route("/")
def tablero():
    """
    Ruta del tablero principal (/).
    Obtiene el resumen consolidado de certificaciones e inconsistencias
    y lo entrega a la plantilla 'tablero.html'.
    """
    resumen = obtener_resumen_certificados()
    return render_template(
        "tablero.html",
        metricas=resumen["metricas"],
        inconsistencias=resumen["alertas"],
        alertas=resumen["alertas"],
        estudiantes=resumen["estudiantes"],
    )


@rutas.route("/cargar", methods=["GET", "POST"])
def cargar():
    """
    Ruta para cargar archivos Excel (GET muestra el formulario, POST procesa la carga).
    El controlador solo coordina: recibe los archivos y llama al servicio de carga.
    """
    if request.method == "POST":
        try:
            archivo_maestro = request.files.get("maestro")
            archivo_evaluaciones = request.files.get("evaluaciones")

            if not archivo_maestro or not archivo_evaluaciones:
                flash("Debes subir ambos archivos Excel.", "error")
                return redirect(url_for("rutas.cargar"))

            import tempfile, os
            with tempfile.TemporaryDirectory() as tmpdir:
                ruta_maestro = os.path.join(tmpdir, "Maestro_Estudiantes.xlsx")
                ruta_evaluaciones = os.path.join(tmpdir, "Registro_Evaluaciones.xlsx")
                archivo_maestro.save(ruta_maestro)
                archivo_evaluaciones.save(ruta_evaluaciones)
                estudiantes, evaluaciones = cargar_datos_desde_excel(
                    ruta_maestro, ruta_evaluaciones
                )

            flash(
                f"Carga exitosa: {estudiantes} estudiantes y {evaluaciones} evaluaciones actualizadas.",
                "success",
            )
            return redirect(url_for("rutas.tablero"))
        except Exception as e:
            flash(f"Error al cargar los archivos: {str(e)}", "error")
            return redirect(url_for("rutas.cargar"))

    return render_template("cargar.html")
