import sys
sys.path.insert(0, '.')
from models.certificados import obtener_resumen_certificados

resumen = obtener_resumen_certificados()
m = resumen['metricas']

print('=== CIFRAS DE CONTROL ===')
print(f"Aprobacion: {m['aprobacion']} esperado 19 -> {'OK' if m['aprobacion'] == 19 else 'FALLO'}")
print(f"Participacion: {m['participacion']} esperado 3 -> {'OK' if m['participacion'] == 3 else 'FALLO'}")
print(f"Sin certificado: {m['sin_certificado']} esperado 1 -> {'OK' if m['sin_certificado'] == 1 else 'FALLO'}")
print(f"Inconsistencias: {m['inconsistencias']} esperado 3 -> {'OK' if m['inconsistencias'] == 3 else 'FALLO'}")

print('\n=== CASOS TESTIGO ===')
camila = next((e for e in resumen['estudiantes'] if e['identificacion'] == '101230456'), None)
if camila:
    ok = camila['promedio_nota'] == 91.25 and camila['promedio_asistencia'] == 96.25 and 'Aprobaci' in camila['estado']
    print(f"Camila 101230456: nota={camila['promedio_nota']} asis={camila['promedio_asistencia']} estado={camila['estado']} -> {'OK' if ok else 'FALLO'}")
else:
    print('Camila: NO ENCONTRADA -> FALLO')

luis = next((e for e in resumen['estudiantes'] if 'Acu' in e.get('nombre_completo', '')), None)
if luis:
    ok = luis['promedio_nota'] == 72.0 and abs(luis['promedio_asistencia'] - 81.67) < 0.01 and 'Aprobaci' in luis['estado']
    print(f"Luis Acuna: nota={luis['promedio_nota']} asis={luis['promedio_asistencia']} estado={luis['estado']} -> {'OK' if ok else 'FALLO'}")
else:
    print('Luis Acuna: NO ENCONTRADO -> FALLO')

print('\n=== INCONSISTENCIAS ===')
ids = [str(a['identificacion']) for a in resumen['alertas']]
print(f"304560321 Javier Espinoza sin evaluaciones: {'ENCONTRADO' if '304560321' in ids else 'FALTANTE'}")
print(f"999880777 no en maestro: {'ENCONTRADO' if '999880777' in ids else 'FALTANTE'}")
fernanda = [a for a in resumen['alertas'] if 'niga' in a.get('nombre_completo', '') or 'Zuniga' in a.get('nombre_completo', '')]
print(f"Fernanda Zuniga asistencia 36.25%: {'ENCONTRADO' if fernanda else 'FALTANTE'}")
if fernanda:
    print(f"  Asistencia reportada: {fernanda[0].get('promedio_asistencia', 'N/A')}")

print('\n=== RUTAS HTTP ===')
import urllib.request
for ruta in ['/', '/cargar']:
    try:
        req = urllib.request.urlopen(f'http://127.0.0.1:5000{ruta}', timeout=3)
        print(f"GET {ruta}: {req.status} OK")
    except Exception as ex:
        print(f"GET {ruta}: ERROR -> {ex}")
