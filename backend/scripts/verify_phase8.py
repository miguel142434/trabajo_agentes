"""Prueba HTTP real de fase 8 en una tabla aislada; no modifica el corpus del usuario."""

import json
from pathlib import Path
import sys
from time import perf_counter
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from psycopg import Connection, sql

from app.core.config import get_settings
from app.main import app
from app.schemas.rag import REFUSAL
from app.schemas.vector import ChunkInput, VectorAddRequest
from app.services.embedding_service import EmbeddingService
from app.services.rag_service import get_rag_service
from app.services.vector_service import VectorService
from app.vectorstore.postgres import PostgresVectorStore


def main():
    settings = get_settings().model_copy(update={
        'vector_table': 'test_phase8_' + uuid4().hex, 'rag_single_pass': False,
    })
    store = PostgresVectorStore(settings)
    vector = VectorService(EmbeddingService(settings), store)
    report = {'model': settings.ollama_model, 'threshold': settings.rag_min_relevance_score, 'results': []}
    output = Path(__file__).resolve().parents[2] / 'docs/phase8-results.json'
    get_rag_service.cache_clear()
    try:
        with patch('app.services.rag_service.get_settings', return_value=settings), \
             patch('app.services.rag_service.get_vector_service', return_value=vector), TestClient(app) as client:
            cases = [
                ('empty', '¿Qué selección ganó el Mundial de fútbol de 2022?', False),
                ('documented', '¿Qué selección ganó el Mundial de fútbol de 2022?', True),
                ('partial', '¿Quién ganó el Mundial de 2022 y cuál era el salario exacto de su entrenador?', False),
                ('unrelated', '¿Cuál es la composición química de la atmósfera de Venus?', False),
            ]
            for case, question, supported in cases:
                if case == 'documented':
                    # Usar el mismo event loop que las peticiones del TestClient.
                    client.portal.call(vector.add, VectorAddRequest(chunks=[ChunkInput(
                        content='Argentina ganó el Mundial de fútbol de 2022 en Qatar. Lionel Messi fue el capitán de la selección argentina.',
                        filename='phase8-mundial.txt', page=1,
                    )]))
                started = perf_counter()
                response = client.post('/api/chat/rag', json={'question': question})
                body = response.json()
                passed = response.status_code == 200 and (
                    ('Argentina' in body.get('answer', '') and body.get('sources') == [
                        {'document': 'phase8-mundial.txt', 'page': 1, 'chunk_index': 0}])
                    if supported else body == {'answer': REFUSAL, 'sources': []})
                row = {'case': case, 'question': question, 'seconds': round(perf_counter()-started, 2),
                       'status_code': response.status_code, 'passed': passed, 'response': body}
                report['results'].append(row)
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
                print(json.dumps(row, ensure_ascii=True), flush=True)
    finally:
        get_rag_service.cache_clear()
        with Connection.connect(store._conninfo(), connect_timeout=5) as conn:
            conn.execute(sql.SQL('DROP TABLE IF EXISTS {}').format(sql.Identifier('public', settings.vector_table)))
    if not all(row['passed'] for row in report['results']):
        raise SystemExit('Falló una comprobación; revisar docs/phase8-results.json')


if __name__ == '__main__':
    main()
