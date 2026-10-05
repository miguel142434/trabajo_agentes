from app.core.security import get_current_user
from tests.auth_helpers import USER_ID, CONVERSATION_ID, MemoryInteractions
import json
import unittest
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app
from app.schemas.rag import REFUSAL
from app.services.rag_service import RAGService, get_rag_service
from app.services.llm_service import LLMService, LLMError
from app.core.config import Settings
from tests.test_rag import match


class SinglePassTests(unittest.TestCase):
    def setUp(self):
        self.retriever = Mock(retrieve=AsyncMock(return_value=[match()]))
        self.llm = Mock(generate=AsyncMock())
        self.service = RAGService(self.retriever, self.llm, single_pass=True, interactions=MemoryInteractions(persisted=True))
        app.dependency_overrides[get_rag_service] = lambda: self.service
        app.dependency_overrides[get_current_user] = lambda: USER_ID
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()
        app.dependency_overrides.clear()

    def post(self):
        return self.client.post("/api/chat/rag", json={"question": "¿Quién ganó el Mundial de 2022?"})

    def test_answer_uses_exactly_one_llm_call(self):
        self.llm.generate.return_value = json.dumps({"sufficient": True, "answer": "Argentina", "source_ids": [1]})
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"conversation_id": CONVERSATION_ID, "answer": "Argentina", "sources": [
            {"document": "mundial.txt", "page": 3, "chunk_index": 2}]})
        self.llm.generate.assert_awaited_once()

    def test_negative_verdict_overrides_a_draft(self):
        self.llm.generate.return_value = json.dumps({"sufficient": False, "answer": "Inventado", "source_ids": [1]})
        self.assertEqual(self.post().json(), {"answer": REFUSAL, "sources": [], "conversation_id": CONVERSATION_ID})
        self.llm.generate.assert_awaited_once()

    def test_no_references_or_explicit_refusal_never_published(self):
        for answer, ids in [("Inventado", []), (REFUSAL, [1])]:
            self.llm.generate.return_value = json.dumps({"sufficient": True, "answer": answer, "source_ids": ids})
            self.assertEqual(self.post().json(), {"answer": REFUSAL, "sources": [], "conversation_id": CONVERSATION_ID})

    def test_invented_reference_is_still_an_error(self):
        self.llm.generate.return_value = json.dumps({"sufficient": True, "answer": "Argentina", "source_ids": [2]})
        self.assertEqual(self.post().status_code, 502)
        self.llm.generate.assert_awaited_once()

    def test_invalid_verdict_is_not_a_knowledge_refusal(self):
        for raw in ["not json", '{"sufficient":"true","answer":"x","source_ids":[1]}']:
            self.llm.generate.return_value = raw
            self.assertEqual(self.post().status_code, 502)

    def test_no_context_skips_llm(self):
        self.retriever.retrieve.return_value = []
        self.assertEqual(self.post().json(), {"answer": REFUSAL, "sources": [], "conversation_id": CONVERSATION_ID})
        self.llm.generate.assert_not_awaited()

    def test_new_request_retrieves_and_generates_again(self):
        self.llm.generate.side_effect = [
            json.dumps({"sufficient": True, "answer": "Argentina", "source_ids": [1]}),
            json.dumps({"sufficient": False, "answer": REFUSAL, "source_ids": []}),
        ]
        self.assertEqual(self.post().json()["answer"], "Argentina")
        self.assertEqual(self.post().json()["answer"], REFUSAL)
        self.assertEqual(self.retriever.retrieve.await_count, 2)
        self.assertEqual(self.llm.generate.await_count, 2)


class OutputLimitTests(unittest.IsolatedAsyncioTestCase):
    async def test_truncated_json_is_reported_as_error(self):
        service = LLMService(Settings(_env_file=None))
        with patch("app.services.llm_service.ChatOllama.ainvoke", new=AsyncMock(return_value=AIMessage(
            content='{"answer":"parcial"}', response_metadata={"done_reason": "length"},
        ))):
            with self.assertRaises(LLMError):
                await service.generate("Pregunta")
