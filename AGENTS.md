# AGENTS.md

- Responde siempre en español sencillo, explicando lo que se va haciendo. Código y nombres técnicos en su convención original.
- Contexto: Academia Horizonte emite un certificado por estudiante al cerrar cada cohorte. Se automatiza el proceso manual Excel/Word como app web.

## Arquitectura (3 piezas)
- Bodega: `Insumos/` (en disco con mayúscula). Solo lectura, NO modificar.
- Cocina: `app.py` (planeado, aún no existe), Python + Flask. Toda la lógica va aquí, NUNCA en la interfaz.
- Salón: HTML servido por Flask. Solo muestra; no calcula ni decide.

## Datos
- `Insumos/Maestro_Estudiantes.xlsx`, hoja `Estudiantes` (A1:E25, 24 filas): `Identificacion | Nombre_Completo | Correo | Programa | Cohorte`
- `Insumos/Registro_Evaluaciones.xlsx`, hoja `Evaluaciones` (A1:F89, ~88 filas): `Identificacion | Programa | Modulo | Nota | Asistencia_Pct | Fecha_Cierre`
- Clave de cruce: `Identificacion`. Datos ficticios (`@ejemplo.cr`, `Técnico en IA Aplicada`).

## Reglas de negocio (límites inclusivos)
- Promedio = suma de Notas / módulos cursados. Asistencia = promedio de Asistencia_Pct.
- Agrupar por `Identificacion` + `Programa`: un certificado por estudiante y programa.
- Promedio >= 70 y Asistencia >= 80 → Aprobación. Promedio < 70 y Asistencia >= 80 → Participación. Asistencia < 80 → sin certificado.

## Estilo
- Código simple, comentado en español, señalando variables, tipos, condicionales, bucles y funciones.
- Web en azul marino y dorado.

## Decisiones técnicas (ver PLAN.md)
- Excel: `openpyxl` (ligera; la lógica de agrupar/promediar queda visible en `app.py`). IDs siempre como texto.
- Web: `Flask` (+ Jinja2 incluido). Lógica solo en `app.py`; HTML solo muestra.
- Estructura planeada: `app.py`, `templates/` (`base`, `index`, `certificado`, `sin_certificado`), `static/estilo.css`, `requirements.txt` (`Flask`, `openpyxl`).
- Validación por etapas: Etapa 1 cruce (conteos esperados: 22 emitibles = 19 Aprobación + 3 Participación; 1 sin, 1 sin datos `304560321`, 1 huérfano `999880777`) → Etapa 2 backend → Etapa 3 interfaz.

## Entorno
- Sin toolchain aún: no hay `requirements.txt` ni scripts. Al crear el stack, documenta aquí los comandos exactos.
- Sin runtime Python en esta máquina (`python`/`py`/`pip` no disponibles al verificar). Verifica el intérprete antes de asumir scripts.
- Ignorados esperados (`.gitignore` en `HEAD`, hoy borrado en disco): `.env`, `.venv`, `__pycache__`, `*.pyc`, `.vercel`. Restaurar con `git show HEAD:<archivo>` si hace falta.
- Rutas con espacios (OneDrive): entrecomillar siempre en PowerShell.
