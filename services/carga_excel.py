"""
services/carga_excel.py
Capa de Servicio (Lógica de Ingesta de Datos)

Lee los archivos Excel de insumos ('Maestro_Estudiantes.xlsx' y 'Registro_Evaluaciones.xlsx'),
valida su estructura de columnas, normaliza las identificaciones como texto sin espacios,
y persiste los datos en la base de datos a través de 'models/datos.py'.
"""

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd

from models.datos import (
    crear_tablas,
    limpiar_tablas,
    insertar_estudiantes,
    insertar_evaluaciones,
    contar_estudiantes,
    contar_evaluaciones,
)

COLUMNAS_ESTUDIANTES = [
    "Identificacion",
    "Nombre_Completo",
    "Correo",
    "Programa",
    "Cohorte",
]

COLUMNAS_EVALUACIONES = [
    "Identificacion",
    "Programa",
    "Modulo",
    "Nota",
    "Asistencia_Pct",
    "Fecha_Cierre",
]


def normalizar_identificacion(val: Any) -> str:
    """
    Normaliza una identificación asegurando que sea tratada como texto sin espacios.
    Elimina cualquier sufijo decimal (.0) que pueda generarse si Excel lo leyó como numérico.
    """
    if val is None or pd.isna(val):
        return ""
    if isinstance(val, float) and val.is_integer():
        return str(int(val)).strip()
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2].strip()
    return s


def normalizar_fecha(val: Any) -> Optional[str]:
    """
    Convierte una fecha a formato estándar YYYY-MM-DD o None si está vacía.
    """
    if val is None or pd.isna(val):
        return None
    if isinstance(val, (pd.Timestamp, datetime.date, datetime.datetime)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    if not s:
        return None
    # Si viene con hora '2026-10-01 00:00:00', tomar solo la fecha
    if " " in s:
        s = s.split(" ")[0]
    return s


def resolver_directorio_insumos() -> Path:
    """
    Localiza la carpeta de insumos, aceptando tanto 'insumos' como 'Insumos'.
    """
    base_dir = Path(__file__).resolve().parent.parent
    candidatos = [base_dir / "insumos", base_dir / "Insumos"]
    for dir_candidato in candidatos:
        if dir_candidato.is_dir():
            return dir_candidato
    return base_dir / "insumos"


def resolver_ruta_archivo(nombre_archivo: str) -> Path:
    """
    Busca un archivo dentro de la carpeta de insumos encontrada.
    """
    dir_insumos = resolver_directorio_insumos()
    archivo = dir_insumos / nombre_archivo
    if not archivo.exists():
        # Probar alternativas de mayúsculas/minúsculas comunes
        for alternativo in dir_insumos.glob("*"):
            if alternativo.name.lower() == nombre_archivo.lower():
                return alternativo
    return archivo


def procesar_excel_estudiantes(
    origen_estudiantes: Union[str, Path, Any]
) -> List[Dict[str, Any]]:
    """
    Lee y valida la hoja 'Estudiantes' de Maestro_Estudiantes.xlsx.
    Retorna una lista de diccionarios listos para inserción en base de datos.
    """
    df = pd.read_excel(
        origen_estudiantes,
        sheet_name="Estudiantes",
        dtype=str,  # Leer inicialmente como texto para evitar pérdida de formato
    )

    # Validar que contenga las columnas requeridas
    columnas_faltantes = [
        col for col in COLUMNAS_ESTUDIANTES if col not in df.columns
    ]
    if columnas_faltantes:
        raise ValueError(
            f"El archivo de Estudiantes no contiene las columnas requeridas: {columnas_faltantes}"
        )

    # Limpiar y transformar registros
    registros: List[Dict[str, Any]] = []
    for _, fila in df.iterrows():
        identificacion = normalizar_identificacion(fila["Identificacion"])
        if not identificacion:
            continue  # Omitir filas vacías

        registros.append(
            {
                "identificacion": identificacion,
                "nombre_completo": str(fila["Nombre_Completo"]).strip()
                if pd.notna(fila["Nombre_Completo"])
                else "",
                "correo": str(fila["Correo"]).strip()
                if pd.notna(fila["Correo"])
                else "",
                "programa": str(fila["Programa"]).strip()
                if pd.notna(fila["Programa"])
                else "",
                "cohorte": str(fila["Cohorte"]).strip()
                if pd.notna(fila["Cohorte"])
                else "",
            }
        )

    return registros


def procesar_excel_evaluaciones(
    origen_evaluaciones: Union[str, Path, Any]
) -> List[Dict[str, Any]]:
    """
    Lee y valida la hoja 'Evaluaciones' de Registro_Evaluaciones.xlsx.
    Retorna una lista de diccionarios listos para inserción en base de datos.
    """
    df = pd.read_excel(
        origen_evaluaciones,
        sheet_name="Evaluaciones",
    )

    columnas_faltantes = [
        col for col in COLUMNAS_EVALUACIONES if col not in df.columns
    ]
    if columnas_faltantes:
        raise ValueError(
            f"El archivo de Evaluaciones no contiene las columnas requeridas: {columnas_faltantes}"
        )

    registros: List[Dict[str, Any]] = []
    for _, fila in df.iterrows():
        identificacion = normalizar_identificacion(fila["Identificacion"])
        if not identificacion:
            continue

        nota_val = fila["Nota"]
        asistencia_val = fila["Asistencia_Pct"]
        fecha_val = fila["Fecha_Cierre"]

        registros.append(
            {
                "identificacion": identificacion,
                "programa": str(fila["Programa"]).strip()
                if pd.notna(fila["Programa"])
                else "",
                "modulo": str(fila["Modulo"]).strip()
                if pd.notna(fila["Modulo"])
                else "",
                "nota": float(nota_val) if pd.notna(nota_val) else 0.0,
                "asistencia_pct": float(asistencia_val)
                if pd.notna(asistencia_val)
                else 0.0,
                "fecha_cierre": normalizar_fecha(fecha_val),
            }
        )

    return registros


def cargar_datos_desde_excel(
    origen_estudiantes: Optional[Union[str, Path, Any]] = None,
    origen_evaluaciones: Optional[Union[str, Path, Any]] = None,
) -> Tuple[int, int]:
    """
    Carga completa de datos desde Excel hacia Supabase:
    1. Resuelve rutas si no se proporcionan orígenes específicos.
    2. Procesa y valida ambos archivos en memoria.
    3. Limpia las tablas existentes para garantizar idempotencia.
    4. Inserta los nuevos registros en 'estudiantes' y 'evaluaciones'.
    5. Retorna una tupla (estudiantes_insertados, evaluaciones_insertadas).
    """
    if origen_estudiantes is None:
        origen_estudiantes = resolver_ruta_archivo("Maestro_Estudiantes.xlsx")
    if origen_evaluaciones is None:
        origen_evaluaciones = resolver_ruta_archivo("Registro_Evaluaciones.xlsx")

    # Procesar archivos primero para no borrar la BD si algún archivo es inválido
    registros_estudiantes = procesar_excel_estudiantes(origen_estudiantes)
    registros_evaluaciones = procesar_excel_evaluaciones(origen_evaluaciones)

    # Asegurar que existan las tablas
    crear_tablas()

    # Reemplazar lo que haya en las tablas (idempotencia)
    limpiar_tablas()

    # Insertar en base de datos
    cant_estudiantes = insertar_estudiantes(registros_estudiantes)
    cant_evaluaciones = insertar_evaluaciones(registros_evaluaciones)

    return cant_estudiantes, cant_evaluaciones
