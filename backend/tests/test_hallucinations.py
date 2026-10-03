import unittest
from unittest.mock import AsyncMock, Mock

from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.rag import REFUSAL
from app.services.rag_service import RAGService
from tests.test_rag import match


class HallucinationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.retriever = Mock(retrieve=AsyncMock(return_value=[match()]))
        self.llm = Mock(generate=AsyncMock())
        self.service = RAGService(self.retriever, self.llm, min_relevance_score=0.65)

    async def test_documented_question_and_filtered_source_mapping(self):
        excluded = match('excluded.txt', 'Texto que no debe llegar al modelo.')
        excluded.distance = 0.8
        self.retriever.retrieve.return_value = [excluded, match()]
        self.llm.generate.side_effect = [
            '{"classification":"SUFFICIENT"}',
            '{"answer":"Argentina","source_ids":[1]}',
        ]
        result = await self.service.answer('¿Quién ganó el Mundial de 2022?')
        self.assertEqual(result.answer, 'Argentina')
        self.assertEqual(result.sources[0].document, 'mundial.txt')
        self.assertEqual(self.llm.generate.await_count, 2)
        for call in self.llm.generate.await_args_list:
            self.assertNotIn('Texto que no debe', call.args[0][-1].content)

    async def test_partial_question_rejected_even_with_high_score(self):
        self.llm.generate.return_value = '{"classification":"INSUFFICIENT"}'
        result = await self.service.answer('¿Quién ganó y cuál era el salario del entrenador?')
        self.assertEqual(result.model_dump(), {'answer': REFUSAL, 'sources': []})
        self.llm.generate.assert_awaited_once()

    async def test_unrelated_question_skips_model(self):
        self.retriever.retrieve.return_value[0].distance = 0.7
        result = await self.service.answer('¿Cómo es la atmósfera de Venus?')
        self.assertEqual(result.answer, REFUSAL)
        self.assertEqual(result.sources, [])
        self.llm.generate.assert_not_awaited()

    async def test_empty_database_skips_model(self):
        self.retriever.retrieve.return_value = []
        self.assertEqual((await self.service.answer('Pregunta')).answer, REFUSAL)
        self.llm.generate.assert_not_awaited()

    async def test_boundary_and_invalid_scores_are_rejected(self):
        service = RAGService(self.retriever, self.llm, min_relevance_score=0.5)
        for distance in (0.5, float('nan'), float('inf'), -0.1, 2.1):
            self.retriever.retrieve.return_value[0].distance = distance
            self.assertEqual((await service.answer('Pregunta')).answer, REFUSAL)
        self.llm.generate.assert_not_awaited()

    async def test_threshold_applies_to_single_pass_too(self):
        service = RAGService(self.retriever, self.llm, single_pass=True, min_relevance_score=0.9)
        self.assertEqual((await service.answer('Pregunta')).answer, REFUSAL)
        self.llm.generate.assert_not_awaited()

    async def test_logs_contain_decision_and_scores_not_reasoning(self):
        self.llm.generate.return_value = '{"classification":"INSUFFICIENT"}'
        with self.assertLogs('app.agents.nodes.rag_nodes', level='INFO') as captured:
            await self.service.answer('private-question')
        output = '\n'.join(captured.output)
        for expected in ('scores=', 'retained=', 'INSUFFICIENT', 'reject_question'):
            self.assertIn(expected, output)
        self.assertNotIn('private-question', output)
        self.assertNotIn('Argentina', output)

    def test_threshold_configuration(self):
        for value in (-1.1, 1.1, float('nan'), float('inf')):
            with self.assertRaises(ValidationError):
                Settings(_env_file=None, rag_min_relevance_score=value)
