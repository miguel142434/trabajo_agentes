# Medición local del 6 de octubre de 2026

La consulta «¿Cuál ha sido la mejor participación de Colombia en algún mundial?»
se ejecutó sobre `Base_Conocimiento_Mundiales_y_Deportes.pdf`, con el filtro del
propietario de ese documento. Se usaron Ollama y PostgreSQL reales. El historial
se sustituyó por almacenamiento en memoria para no crear conversaciones de prueba.

| Modo | Recuperación | Tiempo total del servicio |
|---|---:|---:|
| Dos llamadas | 1,23 s | 212,80 s |
| Una llamada | 0,43 s | 111,74 s |

Ambos devolvieron cuartos de final en Brasil 2014 y las mismas referencias.
La reducción observada fue del 47,5 %. Es una medición por modo, consecutiva,
con el modelo ya cargado, no un promedio ni una garantía de latencia.
No incluye navegador, autenticación ni escritura del historial.

`ollama ps` mostró `qwen3:8b` con `100% CPU`, ventana de 8192 tokens y 6,7 GB.
En el modo de dos llamadas, procesar los prompts tomó 93,95 y 104,04 segundos;
generar sus salidas tomó 2,26 y 10,68 segundos. En el modo de una llamada,
procesar el prompt tomó 95,37 segundos y generar la salida tomó 15,55 segundos.
La carga de Qwen fue inferior a 0,03 segundos por llamada: el cuello de botella
de esta muestra fue procesar el contexto, no cargar el modelo ni buscar documentos.

## Configuración aplicada

El `.env` local, excluido de Git, tiene ahora `RAG_SINGLE_PASS=true`. Se conservan
el modelo, Top-K=4, contexto máximo de 6000 caracteres, umbral de relevancia 0,65,
límite de salida de 512 tokens y permanencia solicitada de 15 minutos.

Se reutiliza el modo existente que evalúa suficiencia y prepara la respuesta en
una sola inferencia. El grafo sigue filtrando relevancia, rechazando falta de
respaldo y validando que las referencias pertenezcan al contexto. La evaluación
y la respuesta ya no son dos inferencias separadas; esto no garantiza ausencia
de alucinaciones. No se redujo el contexto ni se añadió caché de respuestas.

Reiniciar el backend desde su terminal con Ctrl+C y, desde `backend/`:

```powershell
.venv\Scripts\python.exe run.py
```

Volver a enviar la pregunta desde el frontend. El registro `grade_context`
debe mostrar `single_pass=True`. No hace falta subir otra vez el documento.
Los valores por defecto del código y de `.env.example` siguen en `false` para
preservar el modo de dos inferencias de la fase 8 en otras instalaciones.
Para trasladar esta optimización a otro equipo, configurar allí la variable.

## Validación y reproducción

Pasaron 35 pruebas de `tests.test_rag_performance`, `tests.test_rag`,
`tests.test_hallucinations` y `tests.test_agent`. Incluyen una sola llamada,
rechazo, referencias inválidas, salida truncada y rutas del grafo. Las pruebas
unitarias simulan el modelo; las dos mediciones adjuntas sí usan Qwen real.

El script `backend/scripts/benchmark_rag.py` admite ahora `--question`,
`--expected-answer` y `--expected-document`, además de `--user-id` y `--mode`.
Ambos modos usan los mismos límites de salida y permanencia del modelo.
Ejemplo desde `backend/`, sustituyendo el UUID por el propietario verificado:

```powershell
.venv\Scripts\python.exe scripts/benchmark_rag.py --mode single --user-id UUID_DEL_USUARIO --question '¿Cuál ha sido la mejor participación de Colombia en algún mundial?' --expected-answer '2014' --expected-document 'Base_Conocimiento_Mundiales_y_Deportes.pdf' --output ../docs/performance/local-single.json
```

Informes: [dos llamadas](colombia-two-8b.json) y [una llamada](colombia-single-8b.json).
Para una reducción mayor habría que medir un modelo más pequeño o usar
aceleración por GPU/un servicio remoto, comprobando también la calidad.
