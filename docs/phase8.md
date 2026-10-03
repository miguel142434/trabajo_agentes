# Fase 8: control de alucinaciones

## Implementación

1. `grade_context` calcula similitud coseno como `1 - distance` y descarta cada
   fragmento que no supere `RAG_MIN_RELEVANCE_SCORE` antes de construir el prompt.
   Scores no finitos o fuera del rango [-1, 1] también se descartan.
2. Si no queda contexto, pasa directamente a `reject_question`, sin Qwen.
3. El evaluador clasifica el contexto filtrado y limitado con un JSON que contiene
   exclusivamente `classification: SUFFICIENT | INSUFFICIENT`. Se valida con Pydantic;
   valores desconocidos y campos adicionales provocan error técnico.
4. Solo `SUFFICIENT` habilita la generación. El modelo debe usar exclusivamente
   el contexto y rechazar datos ausentes, dudas y contradicciones. Las preguntas
   parcialmente documentadas también deben rechazarse.
5. Se validan las referencias contra los fragmentos que realmente llegaron al prompt.
   La respuesta conserva documento, página (puede ser null) y número de fragmento.
6. Logs: cantidad recuperada, scores, umbral, cantidad retenida, clasificación y ruta.
   No se solicita ni se devuelve razonamiento interno.

## Configuración y latencia

```dotenv
RAG_MIN_RELEVANCE_SCORE=0.65
RAG_SINGLE_PASS=false
RAG_MAX_OUTPUT_TOKENS=512
RAG_KEEP_ALIVE=15m
```

Reiniciar el backend después de cambiar `.env`. El umbral es una similitud, no un
porcentaje de certeza. Aumentarlo puede rechazar documentos útiles; reducirlo puede
admitir documentos irrelevantes. Debe calibrarse con preguntas representativas del
corpus, especialmente al cambiar el modelo de embeddings. El valor inicial no
constituye una calibración completa.

La fase 8 usa clasificación independiente; requiere dos llamadas para responder,
una para rechazar contexto relevante pero incompleto y cero si todo queda bajo el
umbral. Por eso algunos casos pueden tardar más que el modo rápido anterior.
`RAG_SINGLE_PASS=true` permanece como alternativa con filtro y evaluación combinada,
pero no satisface el requisito de clasificación independiente. La configuración local
y `.env.example` quedan en modo estricto (`false`).

## Comprobación manual

Desde `backend/`, con PostgreSQL y Ollama activos:

```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Abrir `http://127.0.0.1:8000/docs`, `POST /api/chat/rag`, `Try it out`.
Cada petición usa `{"question":"..."}`. Con el documento de Mundial 2022 cargado:

| Caso | Pregunta | Esperado |
|---|---|---|
| Documentada | ¿Qué selección ganó el Mundial de fútbol de 2022? | Argentina y fuente documental |
| Parcial | ¿Quién ganó el Mundial de 2022 y cuál era el salario exacto de su entrenador? | Rechazo si el salario no figura en el corpus |
| No relacionada | ¿Cuál es la composición química de la atmósfera de Venus? | Rechazo si no está documentada |
| Base vacía | Cualquier pregunta en una tabla vacía de prueba | Rechazo sin llamar al LLM |

El rechazo exacto es:

```json
{"answer":"No tengo suficiente información en mi base de conocimiento para responder esa pregunta.","sources":[]}
```

Para comprobar la base vacía no hay que borrar documentos. El script siguiente
crea una tabla aislada `test_phase8_<uuid>`, prueba primero vacía, añade un fragmento
de Mundial 2022 y prueba los otros tres casos por el endpoint real. Finalmente
elimina únicamente su tabla de prueba y guarda respuestas y tiempos en
[`phase8-results.json`](phase8-results.json).

```powershell
.venv\Scripts\python.exe scripts/verify_phase8.py
```

## Pruebas automatizadas

Verificación del 3 de octubre de 2026: **72 pruebas aprobadas**, incluidas las
integraciones reales de documentos y vectores. El script de fase 8 aprobó los
cuatro casos con Qwen `qwen3:8b`, umbral 0.65 y modo estricto:

| Caso | Resultado obtenido | Tiempo |
|---|---|---:|
| Base vacía | Rechazo exacto, sin fuentes | 1,87 s |
| Documentada | Argentina; `phase8-mundial.txt`, página 1, chunk 0 | 33,82 s |
| Parcial | Rechazo exacto, sin fuentes | 7,36 s |
| No relacionada | Rechazo exacto, sin fuentes | 0,42 s |

Son mediciones individuales con un único fragmento de prueba; no son comparables
directamente con el benchmark anterior de cuatro fragmentos ni garantizan latencia.

```powershell
.venv\Scripts\python.exe -m unittest tests.test_agent tests.test_rag tests.test_rag_performance tests.test_hallucinations -v
$env:TEST_VECTOR_INTEGRATION="1"
.venv\Scripts\python.exe -m unittest discover -s tests -v
Remove-Item Env:TEST_VECTOR_INTEGRATION
```

Las pruebas con mocks comprueban el flujo y sus límites; el script real comprueba
las decisiones de Qwen en cuatro casos concretos. Ninguna prueba garantiza ausencia
total de alucinaciones. Validar que una referencia existe no demuestra por sí solo
que sustente todas las afirmaciones de la respuesta.

## Archivos

Creados:

- `backend/tests/test_hallucinations.py`: controles del umbral y cuatro escenarios.
- `backend/scripts/verify_phase8.py`: prueba HTTP con Ollama y PostgreSQL reales.
- `docs/phase8.md`: explicación y reproducción de pruebas.
- `docs/phase8-results.json`: evidencia de la ejecución real.

Modificados:

- `backend/app/core/config.py` y `.env.example`: umbral y modo estricto por defecto.
- `backend/app/agents/graph.py`, `state.py`, `nodes/rag_nodes.py`: filtro, clasificación y logs.
- `backend/app/services/context_grader.py`: veredicto estructurado estricto.
- `backend/app/services/rag_prompt.py`: rechazo ante dudas y contradicciones.
- `backend/app/services/rag_service.py`: propaga la configuración al grafo.
- `backend/tests/test_agent.py` y `test_rag.py`: nuevo contrato del evaluador.
- `backend/scripts/benchmark_rag.py`: registra y aplica el umbral configurado.
- `README.md` y `docs/performance/README.md`: estado actual y contexto de mediciones históricas.
- `.env` local (ignorado por Git): valores de fase 8; no se publican credenciales.

El historial sigue siendo temporal en el estado de cada ejecución. La persistencia
de conversaciones corresponde a la fase 9 y no forma parte de este cambio.
