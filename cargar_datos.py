"""
cargar_datos.py
Script de inicialización y carga de datos desde insumos Excel hacia Supabase.

Ejecución:
    uv run cargar_datos.py
"""

import sys
from models.datos import crear_tablas, contar_estudiantes, contar_evaluaciones
from services.carga_excel import cargar_datos_desde_excel


def main():
    print("==================================================")
    print("  Academia de Certificados - Carga Inicial de Datos")
    print("==================================================")

    try:
        # 1. Asegurar la creación de tablas en Supabase
        print("\n1. Verificando y creando tablas en la base de datos...")
        crear_tablas()
        print("   -> Tablas 'estudiantes' y 'evaluaciones' listas.")

        # 2. Cargar datos desde los archivos Excel
        print("\n2. Leyendo archivos Excel y sincronizando con la base de datos...")
        insertados_est, insertados_eval = cargar_datos_desde_excel()
        print(f"   -> Estudiantes procesados: {insertados_est}")
        print(f"   -> Evaluaciones procesadas: {insertados_eval}")

        # 3. Consultar y verificar el conteo final en las tablas
        print("\n3. Verificando conteo de registros en Supabase...")
        total_estudiantes = contar_estudiantes()
        total_evaluaciones = contar_evaluaciones()

        print("--------------------------------------------------")
        print(f"  Total en tabla 'estudiantes':  {total_estudiantes} filas (Esperado: 24)")
        print(f"  Total en tabla 'evaluaciones': {total_evaluaciones} filas (Esperado: 88)")
        print("--------------------------------------------------")

        if total_estudiantes == 24 and total_evaluaciones == 88:
            print("\n[ÉXITO] Todos los registros fueron cargados y validados correctamente.")
        else:
            print(
                f"\n[AVISO] Los totales difieren de las cifras de control esperadas "
                f"(24 estudiantes, 88 evaluaciones)."
            )

    except Exception as e:
        print(f"\n[ERROR] Ocurrió un error durante la carga de datos: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
