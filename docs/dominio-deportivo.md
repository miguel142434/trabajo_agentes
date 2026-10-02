# Dominio documental: deportes

El equipo propone Mundiales de fútbol, Fórmula 1 y otras disciplinas deportivas.
El alcance inicial puede incluir varias disciplinas; cada documento debe identificar
el deporte, la competición y el año o temporada para evitar ambigüedades.

## Qué hace la fase 5

Permite cargar PDF con texto, TXT UTF-8 y DOCX, extraer sus contenidos, dividirlos en
fragmentos e indexarlos. Conserva nombre de archivo, tipo, identificador del documento,
página del PDF e índice del fragmento. Las páginas de TXT y DOCX son `null`:
no se inventa una paginación que estos formatos no proporcionan de manera fiable.

No clasifica automáticamente por deporte ni rechaza documentos de otros temas.
La especialización depende del corpus elegido por el equipo. La fase 6 incorpora
RAG con un prompt estricto y rechazo cuando falta información. La fase 7 agrega
un grafo con evaluación básica de suficiencia; los umbrales de relevancia y el
refuerzo del control de alucinaciones corresponden a la fase 8.

## Cómo organizar el corpus

- Usar nombres concretos, por ejemplo `mundial-masculino-2022-final.pdf` o
  `formula1-2024-clasificacion-pilotos.txt`.
- Incluir título, año/temporada y URL de origen dentro del documento.
- Identificar si las estadísticas pertenecen a pilotos, constructores, selecciones,
  torneos masculinos/femeninos u otra categoría.
- Cargar textos legibles. Los PDF escaneados requieren una etapa previa de OCR;
  esta fase no interpreta imágenes, diagramas ni vídeos.
- Preferir documentos de organizadores, federaciones y reglamentos oficiales.

## Ejemplos incluidos

Los dos TXT de `docs/examples/deportes/` son resúmenes breves redactados para pruebas:

- `mundial-2022.txt`: campeón y marcador de la final. Fuente:
  [FIFA: Argentina y las definiciones por penales](https://www.fifa.com/es/tournaments/mens/worldcup/articles/seleccion-argentina-definicion-penales-tanda-historia-mundiales).
- `f1-2024.txt`: título de Verstappen y resultado de Las Vegas. Fuente:
  [Formula 1: crónica de Las Vegas 2024](https://www.formula1.com/en/latest/article/verstappen-clinches-fourth-drivers-title-with-fifth-place-finish-at-las-vegas-gp.3TZdhZEthj8sADUPU8p6Ni).

Las fuentes se consultaron el 2 de octubre de 2026. Los ejemplos describen temporadas
concretas; no representan resultados actuales ni un corpus deportivo completo.

Preguntas de prueba después de subir los archivos:

1. ¿Qué selección ganó el Mundial de fútbol de 2022?
2. ¿Cómo terminó la tanda de penales entre Argentina y Francia en 2022?
3. ¿En qué Gran Premio aseguró Verstappen su cuarto título mundial?

Desde la fase 6, envíalas a `/api/chat/rag` en el campo `question` para recibir
una respuesta redactada por Qwen con fuentes. `/api/vector/test-search` sigue
disponible para inspeccionar los fragmentos recuperados. Los datos ficticios de las pruebas automatizadas
se almacenan en tablas aisladas que se eliminan al terminar.
