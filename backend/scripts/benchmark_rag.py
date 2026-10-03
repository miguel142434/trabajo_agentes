"""Comparación reproducible con el mismo modelo y corpus, sin caché de respuestas.

Desde backend/: .venv/Scripts/python.exe scripts/benchmark_rag.py --mode single --output ../docs/performance/single.json
Requiere Ollama, PostgreSQL y los documentos deportivos de ejemplo indexados.
"""

import argparse
import asyncio
import json
import logging
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings
from app.schemas.rag import REFUSAL
from app.services.context_grader import ContextAnswer
from app.services.llm_service import LLMService
from app.services.rag_retriever import RAGRetriever
from app.services.rag_service import RAGService
from app.services.vector_service import get_vector_service


async def benchmark(args):
    settings = get_settings()
    llm = LLMService(settings.model_copy(update={"ollama_temperature": 0}))
    llm.model.format = ContextAnswer.model_json_schema() if args.mode == "single" else "json"
    llm.model.num_ctx = 8192
    if args.mode == "single":
        llm.model.num_predict = settings.rag_max_output_tokens
        llm.model.keep_alive = settings.rag_keep_alive
    service = RAGService(RAGRetriever(get_vector_service(), settings.rag_top_k), llm,
                         settings.rag_max_context_chars, single_pass=args.mode == "single",
                         min_relevance_score=settings.rag_min_relevance_score)
    cases = [
        ("¿Qué selección ganó el Mundial de fútbol de 2022?", "Argentina", "mundial-2022.txt"),
        ("¿Cuál es la composición química de la atmósfera de Venus?", None, None),
    ]
    if args.extended:
        cases += [
            ("¿En qué Gran Premio aseguró Verstappen su cuarto título mundial?", "Vegas", "f1-2024.txt"),
            ("¿Quién ganó el Mundial de 2022 y cuál era el salario exacto de su entrenador?", None, None),
        ]
    report = {"mode": args.mode, "model": settings.ollama_model, "top_k": settings.rag_top_k,
              "max_context_chars": settings.rag_max_context_chars, "num_ctx": 8192,
              "min_relevance_score": settings.rag_min_relevance_score, "results": []}
    for question, text, document in cases:
        started = perf_counter()
        result = await service.answer(question)
        passed = (result.answer == REFUSAL and not result.sources) if text is None else (
            text.casefold() in result.answer.casefold() and any(s.document == document for s in result.sources))
        row = {"question": question, "elapsed_seconds": round(perf_counter() - started, 2),
               "passed": passed, **result.model_dump()}
        report["results"].append(row)
        print(json.dumps(row, ensure_ascii=True), flush=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not all(row["passed"] for row in report["results"]):
        raise SystemExit("Falló una comprobación; revisar el corpus y la respuesta.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["two", "single"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--extended", action="store_true")
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    asyncio.run(benchmark(arguments))
