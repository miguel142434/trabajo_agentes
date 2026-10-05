from app.core.security import get_current_user
from tests.auth_helpers import USER_ID, CONVERSATION_ID, MemoryInteractions
import json
import unittest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.services.context_grader import ContextVerdict
from app.schemas.rag import REFUSAL
from app.schemas.vector import VectorMatch
from app.services.llm_service import LLMTimeoutError
from app.services.rag_prompt import build_prompt
from app.services.rag_service import RAGService, get_rag_service


def match(filename="mundial.txt", content="Argentina ganó el Mundial de 2022."):
    return VectorMatch(id=uuid4(), document_id=uuid4(), filename=filename, page=3,
                       chunk_index=2, content=content, metadata={}, distance=0.2)


class RAGTests(unittest.TestCase):
    def setUp(self):
        self.retriever = Mock(retrieve=AsyncMock(return_value=[match(), match("otro.txt")]))
        self.llm = Mock(generate=AsyncMock(return_value=json.dumps({"answer": "Argentina.", "source_ids": [1]})))
        self.grader = Mock(grade=AsyncMock(return_value=ContextVerdict(classification="SUFFICIENT")))
        self.service = RAGService(self.retriever, self.llm, grader=self.grader, interactions=MemoryInteractions(persisted=True))
        app.dependency_overrides[get_rag_service] = lambda: self.service
        app.dependency_overrides[get_current_user] = lambda: USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def post(self, question="¿Quién ganó el Mundial de 2022?"):
        return self.client.post("/api/chat/rag", json={"question": question})

    def test_answer_and_only_cited_sources(self):
        result = self.post()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json(), {"conversation_id": CONVERSATION_ID, "answer": "Argentina.", "sources": [
            {"document": "mundial.txt", "page": 3, "chunk_index": 2}]})
        messages = self.llm.generate.call_args.args[0]
        self.assertEqual(messages[0].type, "system")
        self.assertIn(REFUSAL, messages[0].content)
        self.assertIn("Argentina", messages[1].content)

    def test_empty_database_skips_llm(self):
        self.retriever.retrieve.return_value = []
        self.assertEqual(self.post().json(), {"answer": REFUSAL, "sources": [], "conversation_id": CONVERSATION_ID})
        self.llm.generate.assert_not_awaited()

    def test_refusal_without_sources(self):
        self.llm.generate.return_value = json.dumps({"answer": REFUSAL, "source_ids": [1]})
        self.assertEqual(self.post("¿Cómo reparar un reactor nuclear?").json(), {"answer": REFUSAL, "sources": [], "conversation_id": CONVERSATION_ID})

    def test_uncited_answer_is_rejected(self):
        self.llm.generate.return_value = json.dumps({"answer": "Una suposición", "source_ids": []})
        self.assertEqual(self.post().json(), {"answer": REFUSAL, "sources": [], "conversation_id": CONVERSATION_ID})

    def test_invalid_output_or_invented_reference(self):
        for raw in ["no json", '{"answer":"x","source_ids":[0]}', '{"answer":"x","source_ids":[true]}', '{"answer":"x","source_ids":[3]}']:
            with self.subTest(raw=raw):
                self.llm.generate.return_value = raw
                self.assertEqual(self.post().status_code, 502)

    def test_duplicate_sources_removed(self):
        self.llm.generate.return_value = json.dumps({"answer": "Argentina", "source_ids": [1, 1]})
        self.assertEqual(len(self.post().json()["sources"]), 1)

    def test_timeout_is_not_a_knowledge_refusal(self):
        self.llm.generate.side_effect = LLMTimeoutError("Tiempo excedido")
        self.assertEqual(self.post().status_code, 504)

    def test_invalid_question(self):
        for body in [{}, {"question": " "}, {"question": "a" * 2001}]:
            self.assertEqual(self.client.post("/api/chat/rag", json=body).status_code, 422)
        self.retriever.retrieve.assert_not_awaited()

    def test_context_budget_and_literal_braces(self):
        messages, selected = build_prompt("{question}", [match(content="abc{" * 30), match()], 100)
        self.assertEqual(len(selected), 1)
        payload = json.loads(messages[1].content.split("CONTEXTO (fragmentos JSON):\n")[1])
        self.assertEqual(len(payload[0]["text"]), 100)
        self.assertIn("{question}", messages[1].content)
