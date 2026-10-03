# Latencia del agente antes de la fase 8

Medición local del 3 de octubre de 2026, con `qwen3:8b` en CPU, PostgreSQL y
Ollama reales. Se mantuvieron Top-K=4, contexto máximo de 6000 caracteres y
ventana de 8192 tokens. No se descargó ni sustituyó el modelo.

## Diagnóstico y cambio

La recuperación tarda aproximadamente 0,4–1 segundo. El costo principal está en
procesar el prompt con Qwen. El flujo anterior procesaba el contexto una vez para
evaluar suficiencia y otra para responder. El modo por defecto ahora combina
evaluación y borrador en una llamada con esquema JSON. El grafo conserva la
ruta de rechazo y valida las referencias antes de devolver una respuesta.

La decisión y el borrador proceden de una misma inferencia; ya no hay una segunda
inferencia independiente de generación. Los casos probados comprueban respuestas
respaldadas, rechazo fuera de dominio y rechazo por información parcial, pero no
constituyen una evaluación exhaustiva de alucinaciones. La fase 8 sigue pendiente.

También se limita la salida a 512 tokens (un truncamiento provoca error explícito)
y se solicita conservar el modelo cargado 15 minutos. Esto consume memoria y no
garantiza que Ollama pueda mantenerlo cargado si necesita liberar recursos.

## Repetir la medición

Con PostgreSQL, Ollama y los documentos `mundial-2022.txt` y `f1-2024.txt` de
ejemplo ya indexados, ejecutar desde `backend/`, una prueba después de la otra:

```powershell
.venv\Scripts\python.exe scripts/benchmark_rag.py --mode two --output ../docs/performance/local-two.json
.venv\Scripts\python.exe scripts/benchmark_rag.py --mode single --extended --output ../docs/performance/local-single.json
```

El modo `two` reproduce la configuración anterior sin límite explícito de salida
ni keep-alive adicional. El modo `single` usa el esquema y opciones actuales.
El script invoca el servicio y el grafo reales, sin transporte HTTP. Guarda tiempos,
respuestas, fuentes y comprobaciones básicas; retorna un error si alguna falla.
Los logs de la terminal detallan carga, procesamiento y generación.

Los tiempos varían con la carga del equipo, el tamaño de los documentos y si el
modelo ya está cargado. Para comparar cambios futuros con rigor, repetir varias
veces ambos modos bajo las mismas condiciones de carga y calentamiento. No hacer
consultas simultáneas mientras se mide.

## Informes

| Consulta | Antes, dos llamadas si responde | Ahora, una llamada | Resultado actual |
|---|---:|---:|---|
| Campeón del Mundial 2022 | 88,63 s | 47,55 s | Argentina, con fuente |
| Atmósfera de Venus | 38,04 s | 41,11 s | Rechazo, sin fuentes |
| Cuarto título de Verstappen | No medido | 45,73 s | Las Vegas 2024, con fuente |
| Mundial 2022 y salario del entrenador | No medido | 41,29 s | Rechazo por información incompleta |

El rechazo no mejoró en esta muestra: antes también requería solo una llamada y
ahora el JSON incluye campos adicionales. La mejora observada corresponde al
camino que sí responde. Son mediciones individuales, no promedios ni una garantía
de tiempo para cualquier consulta.

- `baseline-8b.json`: flujo anterior de dos llamadas.
- `single-pass-8b.json`: primera versión experimental, con instrucciones más largas.
- `single-pass-compact-8b.json`: versión final con instrucciones compactas.

La primera consulta del baseline incluyó 12,36 segundos de carga de Qwen; las
mediciones posteriores se realizaron con el modelo ya cargado. Por eso la diferencia
total observada no debe atribuirse exclusivamente al cambio de código.

## Validación

Pasaron las 64 pruebas de `unittest`, incluidas las integraciones reales de carga
de documentos y búsqueda vectorial (`TEST_VECTOR_INTEGRATION=1`), y `pip check`
no encontró conflictos. Las 8 pruebas nuevas comprueban una sola invocación,
rechazo, referencias inválidas, JSON incorrecto, ausencia de contexto, aislamiento
entre peticiones y detección de salida truncada. Los cuatro casos del benchmark
final también pasaron con Qwen real.
