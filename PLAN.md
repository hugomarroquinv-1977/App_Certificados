# PLAN.md — App-Certificados (Academia Horizonte)

Construcción por etapas. No se avanza de etapa sin pasar su validación.
Reglas fijas: `Insumos/` no se modifica; toda la lógica vive en `app.py`, el HTML solo muestra.

## Etapa 0 — Entorno (pre-requisito)
- Qué: verificar intérprete Python, crear `.venv`, instalar `Flask + openpyxl`, crear `requirements.txt`.
- Validar: `python --version` funciona; `pip install -r requirements.txt` instala sin errores.
- Salida: entorno listo. Sin lógica todavía.

## Etapa 1 — Validación del cruce de datos (primero)
- Qué:
  1. Leer `Insumos/Maestro_Estudiantes.xlsx` (hoja `Estudiantes`) y `Insumos/Registro_Evaluaciones.xlsx` (hoja `Evaluaciones`) como texto (IDs como texto).
  2. Agrupar evaluaciones por `Identificacion + Programa`; promedio = suma Notas / módulos del grupo; asistencia = promedio `Asistencia_Pct`.
  3. Clasificar con límites inclusivos: Aprobación (>=70 y >=80), Participación (<70 y >=80), sin certificado (<80).
  4. Reportar: maestro sin notas, evaluaciones sin maestro, duplicados `ID+Programa+Modulo`, valores fuera de 0–100.
- Validar (conteos esperados ya calculados a mano):
  - 1 maestro sin notas: `304560321`.
  - 1 huérfano con notas: `999880777` (Aprobación calculada, pero sin nombre → no emitible).
  - Grupos válidos (cruce con maestro): 23 → 19 Aprobación + 3 Participación + 1 Sin (`111230984`).
  - Certificados emitibles: **22**. Sin duplicados ni valores fuera de rango.
  - Decisión pendiente antes de Etapa 2: qué mostrar para `304560321` ("sin datos") y `999880777` (reporte de error, no certificado).
- Salida: informe de validación OK. Sin Flask todavía.

## Etapa 2 — Backend Flask (después)
- Qué (`app.py`):
  1. Funciones puras y comentadas: `cargar_maestro`, `cargar_evaluaciones`, `calcular_promedio`, `calcular_asistencia`, `decidir_certificado`, `cruzar_datos`.
  2. Carga de Excel una vez al arrancar; rutas: `/` (buscador) y `/certificado/<identificacion>` (usa resultado ya calculado).
  3. Manejo de casos: sin datos, sin certificado, huérfano (no se emite, se reporta).
- Validar: comparo salida del backend contra los conteos de Etapa 1 (22 emitibles: 19+3); pruebo IDs límite (`402340178`, `306780145`, `108970234`), el sin certificado (`111230984`), el sin datos (`304560321`) y el huérfano (`999880777`); IDs como texto.
- Salida: backend responde conteos correctos. Sin diseño final todavía.

## Etapa 3 — Interfaz HTML (al final)
- Qué: `templates/base.html`, `index.html`, `certificado.html`, `sin_certificado.html` + `static/estilo.css` (azul marino y dorado). Jinja2 solo muestra variables que ya calculó `app.py`.
- Validar: navego buscador → certificado de Aprobación, de Participación y caso sin certificado; reviso tildes (`Técnico`, `Módulo`), responsive básico y que el HTML no calcula nada.
- Salida: app completa verificada contra Etapa 1.
