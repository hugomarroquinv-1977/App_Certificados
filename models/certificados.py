"""
models/certificados.py
Capa de Modelo (Lógica de Negocio y Reglas de Certificación)

Implementa las reglas de negocio descritas en AGENTS.md:
  - Constantes exactas: NOTA_MINIMA = 70, ASISTENCIA_MINIMA = 80.
  - R1. Agrupar por identificación + programa.
  - R2. Promedio de nota y promedio de asistencia redondeados a 2 decimales.
  - R3. Aprobación: promedio_nota >= 70 y promedio_asistencia >= 80.
  - R4. Participación: promedio_nota < 70 y promedio_asistencia >= 80.
  - R5. Sin certificado: promedio_asistencia < 80 (y >= 50).
  - R6. Inconsistencias (se alertan y no se certifican):
        * Estudiante en el maestro sin evaluaciones.
        * Evaluación con identificación que no está en el maestro.
        * Asistencia promedio menor a 50 %.
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from models.datos import obtener_estudiantes, obtener_evaluaciones

# Constantes del negocio según AGENTS.md
NOTA_MINIMA: float = 70.0
ASISTENCIA_MINIMA: float = 80.0
ASISTENCIA_CRITICA: float = 50.0


def calcular_promedios(evaluaciones: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Calcula el promedio de nota y el promedio de asistencia de un conjunto de evaluaciones,
    redondeando ambos resultados a 2 decimales (R2).
    """
    if not evaluaciones:
        return 0.0, 0.0

    total_notas = sum(float(ev.get("nota") or 0.0) for ev in evaluaciones)
    total_asistencias = sum(
        float(ev.get("asistencia_pct") or 0.0) for ev in evaluaciones
    )
    cantidad = len(evaluaciones)

    promedio_nota = round(total_notas / cantidad, 2)
    promedio_asistencia = round(total_asistencias / cantidad, 2)

    return promedio_nota, promedio_asistencia


def clasificar_estado(promedio_nota: float, promedio_asistencia: float) -> str:
    """
    Clasifica el estado del estudiante según las reglas R3, R4 y R5.
    (Solo se aplica a estudiantes sin inconsistencias de asistencia < 50%).
    """
    if promedio_asistencia >= ASISTENCIA_MINIMA:
        if promedio_nota >= NOTA_MINIMA:
            return "Aprobación"
        else:
            return "Participación"
    else:
        return "Sin certificado"


def obtener_resumen_certificados() -> Dict[str, Any]:
    """
    Procesa todos los estudiantes y evaluaciones almacenados en la base de datos,
    aplica las reglas R1 a R6, detecta inconsistencias y genera el balance consolidado.

    Retorna un diccionario con:
      - 'metricas': conteos de Aprobación (19), Participación (3), Sin certificado (1),
                    Inconsistencias (3) y total de estudiantes.
      - 'alertas': lista de inconsistencias detectadas.
      - 'estudiantes': lista de todos los estudiantes clasificados con sus promedios y estado.
    """
    estudiantes = obtener_estudiantes()
    evaluaciones = obtener_evaluaciones()

    # Indexar estudiantes del maestro por identificación
    mapa_estudiantes: Dict[str, Dict[str, Any]] = {
        str(e["identificacion"]).strip(): e for e in estudiantes
    }

    # R1: Agrupar evaluaciones por (identificacion, programa)
    evals_por_clave: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    identificaciones_con_evaluaciones = set()

    for ev in evaluaciones:
        ident = str(ev["identificacion"]).strip()
        prog = str(ev["programa"]).strip()
        evals_por_clave[(ident, prog)].append(ev)
        identificaciones_con_evaluaciones.add(ident)

    alertas: List[Dict[str, Any]] = []
    estudiantes_procesados: List[Dict[str, Any]] = []

    conteo_aprobacion = 0
    conteo_participacion = 0
    conteo_sin_certificado = 0

    # R6. Caso 1: Estudiante del maestro sin evaluaciones (ej. Javier Espinoza 304560321)
    # y procesamiento de estudiantes válidos del maestro
    for ident, est in mapa_estudiantes.items():
        prog = str(est["programa"]).strip()
        evals_estudiante = evals_por_clave.get((ident, prog), [])

        if not evals_estudiante:
            alertas.append(
                {
                    "tipo": "Sin evaluaciones",
                    "identificacion": ident,
                    "nombre_completo": est.get("nombre_completo", "Desconocido"),
                    "programa": prog,
                    "cohorte": est.get("cohorte", ""),
                    "detalle": f"El estudiante '{est.get('nombre_completo')}' está registrado en el maestro pero no cuenta con evaluaciones registradas.",
                }
            )
            estudiantes_procesados.append(
                {
                    "identificacion": ident,
                    "nombre_completo": est.get("nombre_completo", ""),
                    "correo": est.get("correo", ""),
                    "programa": prog,
                    "cohorte": est.get("cohorte", ""),
                    "promedio_nota": 0.0,
                    "promedio_asistencia": 0.0,
                    "estado": "Inconsistencia (Sin evaluaciones)",
                    "es_elegible": False,
                }
            )
            continue

        prom_nota, prom_asist = calcular_promedios(evals_estudiante)

        # R6. Caso 3: Asistencia menor a 50 % (ej. Fernanda Zúñiga 36.25%)
        # R5. Sin certificado: asistencia < 80.
        if prom_asist < ASISTENCIA_CRITICA:
            conteo_sin_certificado += 1
            alertas.append(
                {
                    "tipo": "Asistencia crítica (<50%)",
                    "identificacion": ident,
                    "nombre_completo": est.get("nombre_completo", ""),
                    "programa": prog,
                    "cohorte": est.get("cohorte", ""),
                    "promedio_asistencia": prom_asist,
                    "detalle": f"El estudiante '{est.get('nombre_completo')}' tiene asistencia crítica de {prom_asist}% (menor al umbral del 50%). No se certifica.",
                }
            )
            estudiantes_procesados.append(
                {
                    "identificacion": ident,
                    "nombre_completo": est.get("nombre_completo", ""),
                    "correo": est.get("correo", ""),
                    "programa": prog,
                    "cohorte": est.get("cohorte", ""),
                    "promedio_nota": prom_nota,
                    "promedio_asistencia": prom_asist,
                    "estado": "Sin certificado",
                    "inconsistencia": "Asistencia crítica (<50%)",
                    "es_elegible": False,
                }
            )
            continue

        # Reglas R3, R4 y R5
        estado = clasificar_estado(prom_nota, prom_asist)
        if estado == "Aprobación":
            conteo_aprobacion += 1
            elegible = True
        elif estado == "Participación":
            conteo_participacion += 1
            elegible = True
        else:
            conteo_sin_certificado += 1
            elegible = False

        estudiantes_procesados.append(
            {
                "identificacion": ident,
                "nombre_completo": est.get("nombre_completo", ""),
                "correo": est.get("correo", ""),
                "programa": prog,
                "cohorte": est.get("cohorte", ""),
                "promedio_nota": prom_nota,
                "promedio_asistencia": prom_asist,
                "estado": estado,
                "es_elegible": elegible,
            }
        )

    # R6. Caso 2: Identificación con evaluaciones que no está en el maestro (ej. 999880777)
    for (ident, prog), evals_extra in evals_por_clave.items():
        if ident not in mapa_estudiantes:
            prom_nota, prom_asist = calcular_promedios(evals_extra)
            alertas.append(
                {
                    "tipo": "No registrado en maestro",
                    "identificacion": ident,
                    "nombre_completo": "No registrado",
                    "programa": prog,
                    "cohorte": "-",
                    "detalle": f"La identificación '{ident}' tiene evaluaciones en el programa '{prog}' pero no figura en la lista maestra de estudiantes.",
                }
            )
            estudiantes_procesados.append(
                {
                    "identificacion": ident,
                    "nombre_completo": "[No registrado en maestro]",
                    "correo": "-",
                    "programa": prog,
                    "cohorte": "-",
                    "promedio_nota": prom_nota,
                    "promedio_asistencia": prom_asist,
                    "estado": "Inconsistencia (No en maestro)",
                    "es_elegible": False,
                }
            )

    metricas = {
        "aprobacion": conteo_aprobacion,
        "participacion": conteo_participacion,
        "sin_certificado": conteo_sin_certificado,
        "inconsistencias": len(alertas),
        "total_maestro": len(estudiantes),
    }

    return {
        "metricas": metricas,
        "alertas": alertas,
        "estudiantes": estudiantes_procesados,
    }


def obtener_estudiante_para_certificado(
    identificacion: str, programa: str
) -> Optional[Dict[str, Any]]:
    """
    Busca los datos de un estudiante específico y evalúa si es elegible para certificado
    (Aprobación o Participación).
    """
    resumen = obtener_resumen_certificados()
    ident_limpia = str(identificacion).strip()
    prog_limpio = str(programa).strip()

    for est in resumen["estudiantes"]:
        if (
            str(est["identificacion"]).strip() == ident_limpia
            and str(est["programa"]).strip().lower() == prog_limpio.lower()
        ):
            if est["es_elegible"]:
                return est
            return None

    return None
