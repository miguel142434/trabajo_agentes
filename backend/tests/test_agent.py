import asyncio
import json
import unittest
from unittest.mock import AsyncMock, Mock

from app.agents.graph import build_graph, graph_mermaid
from app.core.exceptions import AppError
from app.schemas.rag import REFUSAL
from app.services.context_grader import ContextGrader, ContextVerdict
from app.services.interaction_service import InteractionService
from app.services.llm_service import LLMError, LLMTimeoutError
from tests.test_rag import match


class AgentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.retriever = Mock(retrieve=AsyncMock(return_value=[match()]))
        self.llm = Mock(generate=AsyncMock(return_value=json.dumps({"answer": "Argentina", "source_ids": [1]})))
        self.grader = Mock(grade=AsyncMock(return_value=ContextVerdict(classification="SUFFICIENT")))
        self.interactions = InteractionService()
        self.graph = build_graph(self.retriever, self.llm, self.grader, self.interactions)

    async def path(self):
        return [name async for update in self.graph.astream({"question": "Mundial?"}, stream_mode="updates") for name in update]

    async def test_sufficient_route(self):
        self.assertEqual(await self.path(), ["receive_question", "validate_question", "retrieve_context",
                                             "grade_context", "generate_answer", "save_interaction"])

    async def test_insufficient_route_never_generates(self):
        self.grader.grade.return_value = ContextVerdict(classification="INSUFFICIENT")
        self.assertEqual(await self.path(), ["receive_question", "validate_question", "retrieve_context",
                                             "grade_context", "reject_question", "save_interaction"])
        self.llm.generate.assert_not_awaited()

    async def test_empty_context_skips_grader_and_generator(self):
        self.retriever.retrieve.return_value = []
        state = await self.graph.ainvoke({"question": "Mundial?"})
        self.assertEqual(state["answer"], REFUSAL)
        self.assertEqual(state["sources"], [])
        self.assertEqual(state["context_score"], 0)
        self.grader.grade.assert_not_awaited()
        self.llm.generate.assert_not_awaited()

    async def test_generation_can_still_reject(self):
        self.llm.generate.return_value = json.dumps({"answer": REFUSAL, "source_ids": []})
        self.assertEqual((await self.path())[-3:], ["generate_answer", "reject_question", "save_interaction"])

    async def test_invalid_question_stops_before_retrieval(self):
        with self.assertRaises(AppError) as error:
            await self.graph.ainvoke({"question": " "})
        self.assertEqual(error.exception.status_code, 422)
        self.retriever.retrieve.assert_not_awaited()

    async def test_interaction_and_identifiers_are_scoped_to_execution(self):
        first, second = await asyncio.gather(
            self.graph.ainvoke({"question": "Uno", "user_id": "test-user", "conversation_id": "test-conversation"}),
            self.graph.ainvoke({"question": "Dos"}),
        )
        self.assertEqual(first["interaction"]["user_id"], "test-user")
        self.assertEqual(first["interaction"]["conversation_id"], "test-conversation")
        self.assertIsNone(second["interaction"]["user_id"])
        self.assertIsNone(second["interaction"]["conversation_id"])
        self.assertEqual(second["interaction"]["question"], "Dos")
        self.assertFalse(first["interaction"]["persisted"])
        self.assertEqual(first["status"], "answered")
        self.assertAlmostEqual(first["context_score"], 0.8)

    async def test_grader_failure_is_not_a_rejection(self):
        self.grader.grade.side_effect = LLMTimeoutError("Timeout")
        with self.assertRaises(LLMTimeoutError):
            await self.graph.ainvoke({"question": "Pregunta"})
        self.llm.generate.assert_not_awaited()

    async def test_grader_receives_same_bounded_context_as_generator(self):
        self.graph = build_graph(self.retriever, self.llm, self.grader, self.interactions, max_context_chars=10)
        await self.graph.ainvoke({"question": "Pregunta"})
        self.assertEqual(self.grader.grade.call_args.args[0], self.llm.generate.call_args.args[0])

    def test_mermaid_contains_branches(self):
        diagram = graph_mermaid(self.graph)
        for name in ("grade_context", "reject_question", "generate_answer", "save_interaction", "__start__", "__end__"):
            self.assertIn(name, diagram)


class ContextGraderTests(unittest.IsolatedAsyncioTestCase):
    async def test_strict_verdict(self):
        from app.services.rag_prompt import build_prompt
        prompt, _ = build_prompt("Pregunta", [match()], 6000)
        llm = Mock(generate=AsyncMock())
        grader = ContextGrader(llm)
        for value in ("SUFFICIENT", "INSUFFICIENT"):
            llm.generate.return_value = json.dumps({"classification": value})
            self.assertEqual((await grader.grade(prompt)).classification, value)
        for raw in ('{"sufficient":"true"}', 'no json',
                    '{"classification":"SUFFICIENT","reason":"secret"}',
                    '{"classification":"MAYBE"}', '{"classification":true}'):
            llm.generate.return_value = raw
            with self.assertRaises(LLMError):
                await grader.grade(prompt)
