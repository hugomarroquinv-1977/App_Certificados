"""
models/datos.py
Capa de Modelo (Acceso a Datos)

Único archivo autorizado para conectarse y comunicarse con la base de datos.
Soporta de forma automática:
  1. PostgreSQL (Supabase) cuando la variable DATABASE_URL está configurada en .env,
     utilizando psycopg con prepare_threshold=None (compatible con PgBouncer).
  2. SQLite local ('academia.db' en la raíz) cuando DATABASE_URL no está definida o está vacía.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Intentar importar psycopg si está disponible
try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_DISPONIBLE = True
except ImportError:
    PSYCOPG_DISPONIBLE = False


def obtener_database_url() -> Optional[str]:
    """
    Retorna el valor de DATABASE_URL si está definido y no vacío.
    De lo contrario, retorna None.
    """
    url = os.getenv("DATABASE_URL")
    if url and url.strip():
        return url.strip()
    return None


def usar_sqlite() -> bool:
    """
    Determina si se debe utilizar SQLite (DATABASE_URL vacía o no configurada).
    """
    return obtener_database_url() is None


def obtener_ruta_sqlite() -> Path:
    """
    Retorna la ruta absoluta hacia el archivo 'academia.db' en la raíz del proyecto.
    """
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "academia.db"


@contextmanager
def gestionar_conexion() -> Generator[Any, None, None]:
    """
    Context manager que provee una conexión abierta y configurada,
    asegurando commit al finalizar y cierre adecuado.
    """
    if usar_sqlite():
        ruta_db = obtener_ruta_sqlite()
        conn = sqlite3.connect(str(ruta_db))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    else:
        if not PSYCOPG_DISPONIBLE:
            raise ImportError(
                "La librería psycopg no está instalada para conectar con PostgreSQL."
            )
        url = obtener_database_url()
        # Conexión con prepare_threshold=None para compatibilidad con el pooler de Supabase
        conn = psycopg.connect(url, prepare_threshold=None)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def obtener_conexion() -> Any:
    """
    Retorna una conexión directa (para compatibilidad de interfaz).
    """
    if usar_sqlite():
        conn = sqlite3.connect(str(obtener_ruta_sqlite()))
        conn.row_factory = sqlite3.Row
        return conn
    else:
        if not PSYCOPG_DISPONIBLE:
            raise ImportError("psycopg no disponible.")
        return psycopg.connect(obtener_database_url(), prepare_threshold=None)


def crear_tablas() -> None:
    """
    Crea las tablas 'estudiantes' y 'evaluaciones' si no existen,
    adaptando la sintaxis según el motor de base de datos en uso.
    """
    es_local = usar_sqlite()

    if es_local:
        sql_estudiantes = """
        CREATE TABLE IF NOT EXISTS estudiantes (
            identificacion TEXT PRIMARY KEY,
            nombre_completo TEXT,
            correo TEXT,
            programa TEXT,
            cohorte TEXT
        );
        """
        sql_evaluaciones = """
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identificacion TEXT,
            programa TEXT,
            modulo TEXT,
            nota REAL,
            asistencia_pct REAL,
            fecha_cierre TEXT
        );
        """
    else:
        sql_estudiantes = """
        CREATE TABLE IF NOT EXISTS estudiantes (
            identificacion TEXT PRIMARY KEY,
            nombre_completo TEXT,
            correo TEXT,
            programa TEXT,
            cohorte TEXT
        );
        """
        sql_evaluaciones = """
        CREATE TABLE IF NOT EXISTS evaluaciones (
            id SERIAL PRIMARY KEY,
            identificacion TEXT,
            programa TEXT,
            modulo TEXT,
            nota NUMERIC,
            asistencia_pct NUMERIC,
            fecha_cierre DATE
        );
        """

    with gestionar_conexion() as conn:
        cur = conn.cursor()
        cur.execute(sql_estudiantes)
        cur.execute(sql_evaluaciones)


def limpiar_tablas() -> None:
    """
    Elimina todos los registros de 'evaluaciones' y 'estudiantes'
    para garantizar la idempotencia de las cargas.
    """
    with gestionar_conexion() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM evaluaciones;")
        cur.execute("DELETE FROM estudiantes;")


def insertar_estudiantes(lista_estudiantes: List[Dict[str, Any]]) -> int:
    """
    Inserta una lista de diccionarios de estudiantes en la base de datos.
    Actualiza los registros si la identificación ya existe.
    """
    if not lista_estudiantes:
        return 0

    es_local = usar_sqlite()

    if es_local:
        sql = """
        INSERT INTO estudiantes (identificacion, nombre_completo, correo, programa, cohorte)
        VALUES (:identificacion, :nombre_completo, :correo, :programa, :cohorte)
        ON CONFLICT(identificacion) DO UPDATE SET
            nombre_completo = excluded.nombre_completo,
            correo = excluded.correo,
            programa = excluded.programa,
            cohorte = excluded.cohorte;
        """
    else:
        sql = """
        INSERT INTO estudiantes (identificacion, nombre_completo, correo, programa, cohorte)
        VALUES (%(identificacion)s, %(nombre_completo)s, %(correo)s, %(programa)s, %(cohorte)s)
        ON CONFLICT (identificacion) DO UPDATE SET
            nombre_completo = EXCLUDED.nombre_completo,
            correo = EXCLUDED.correo,
            programa = EXCLUDED.programa,
            cohorte = EXCLUDED.cohorte;
        """

    with gestionar_conexion() as conn:
        cur = conn.cursor()
        cur.executemany(sql, lista_estudiantes)

    return len(lista_estudiantes)


def insertar_evaluaciones(lista_evaluaciones: List[Dict[str, Any]]) -> int:
    """
    Inserta una lista de diccionarios de evaluaciones en la base de datos.
    """
    if not lista_evaluaciones:
        return 0

    es_local = usar_sqlite()

    if es_local:
        sql = """
        INSERT INTO evaluaciones (identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre)
        VALUES (:identificacion, :programa, :modulo, :nota, :asistencia_pct, :fecha_cierre);
        """
    else:
        sql = """
        INSERT INTO evaluaciones (identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre)
        VALUES (%(identificacion)s, %(programa)s, %(modulo)s, %(nota)s, %(asistencia_pct)s, %(fecha_cierre)s);
        """

    with gestionar_conexion() as conn:
        cur = conn.cursor()
        cur.executemany(sql, lista_evaluaciones)

    return len(lista_evaluaciones)


def obtener_estudiantes() -> List[Dict[str, Any]]:
    """
    Consulta y retorna todos los registros de la tabla 'estudiantes'
    como una lista de diccionarios.
    """
    sql = """
    SELECT identificacion, nombre_completo, correo, programa, cohorte
    FROM estudiantes
    ORDER BY identificacion ASC;
    """
    with gestionar_conexion() as conn:
        if usar_sqlite():
            cur = conn.cursor()
            cur.execute(sql)
            filas = cur.fetchall()
            return [dict(fila) for fila in filas]
        else:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return cur.fetchall()


def obtener_evaluaciones() -> List[Dict[str, Any]]:
    """
    Consulta y retorna todos los registros de la tabla 'evaluaciones'
    como una lista de diccionarios.
    """
    sql = """
    SELECT id, identificacion, programa, modulo, nota, asistencia_pct, fecha_cierre
    FROM evaluaciones
    ORDER BY id ASC;
    """
    with gestionar_conexion() as conn:
        if usar_sqlite():
            cur = conn.cursor()
            cur.execute(sql)
            filas = cur.fetchall()
            return [dict(fila) for fila in filas]
        else:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(sql)
                return cur.fetchall()


def contar_estudiantes() -> int:
    """
    Retorna la cantidad total de filas en la tabla 'estudiantes'.
    """
    with gestionar_conexion() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM estudiantes;")
        resultado = cur.fetchone()
        return resultado[0] if resultado else 0


def contar_evaluaciones() -> int:
    """
    Retorna la cantidad total de filas en la tabla 'evaluaciones'.
    """
    with gestionar_conexion() as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM evaluaciones;")
        resultado = cur.fetchone()
        return resultado[0] if resultado else 0
