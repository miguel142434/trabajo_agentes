"""PostgreSQL real aislado, HTTP real, JWT firmado y generación/embeddings simulados."""
import asyncio
import os
import sys
import time
import importlib.util
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from psycopg import Connection, sql
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import get_settings
from app.core.database import Base, engine, get_db
from app.core.exceptions import AppError
from app.main import app
from app.models.domain import Conversation, Message, User
from app.schemas.vector import ChunkInput
from app.services.document_service import DocumentService, get_document_service
from app.services.interaction_service import InteractionService
from app.services.rag_retriever import RAGRetriever
from app.services.rag_service import RAGService, get_rag_service
from app.services.vector_service import VectorService, get_vector_service
from app.vectorstore.postgres import PostgresVectorStore

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@unittest.skipUnless(os.environ.get('TEST_AUTH_INTEGRATION') == '1', 'Requiere PostgreSQL real')
class HistoryIsolationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        suffix = uuid4().hex
        self.schema = 'test_history_' + suffix
        self.settings = get_settings().model_copy(update={
            'vector_table': 'test_private_' + suffix, 'document_table': 'test_upload_' + suffix,
            'embedding_dimension': 3})
        self.store = PostgresVectorStore(self.settings)
        with Connection.connect(self.store._conninfo()) as conn:
            conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        self.db_engine = create_async_engine(engine.url, connect_args={'options': f'-c search_path={self.schema}'})
        async with self.db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.db_engine, expire_on_commit=False)
        self.interactions = InteractionService(self.sessions)
        self.embeddings = Mock(embed=AsyncMock(side_effect=lambda texts, **kw: [[1.,0.,0.] for _ in texts]))
        self.vector = VectorService(self.embeddings, self.store)
        self.llm = Mock(generate=AsyncMock(return_value='{"sufficient":true,"answer":"Dato privado","source_ids":[1]}'))
        self.rag = RAGService(RAGRetriever(self.vector, 4), self.llm,
                              single_pass=True, interactions=self.interactions)
        async def db():
            async with self.sessions() as session:
                yield session
        app.dependency_overrides[get_db] = db
        app.dependency_overrides[get_rag_service] = lambda: self.rag
        app.dependency_overrides[get_vector_service] = lambda: self.vector
        app.dependency_overrides[get_document_service] = lambda: DocumentService(self.settings, self.embeddings, self.store)
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        jwks = Mock()
        jwks.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        self.keys_patch = patch('app.core.security.get_jwks_client', return_value=jwks)
        self.keys_patch.start()
        self.a, self.b = str(uuid4()), str(uuid4())
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test')

    def headers(self, subject):
        settings = get_settings()
        payload = {'sub': subject, 'iss': settings.keycloak_issuer, 'aud': settings.keycloak_audience,
                   'azp': settings.keycloak_client_id, 'typ':'Bearer', 'iat': int(time.time())-1,
                   'exp': int(time.time())+300}
        return {'Authorization': 'Bearer '+jwt.encode(payload,self.key,algorithm='RS256')}

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.keys_patch.stop()
        await self.db_engine.dispose()
        with Connection.connect(self.store._conninfo()) as conn:
            for table in [self.settings.document_table, self.settings.vector_table]:
                conn.execute(sql.SQL('DROP TABLE IF EXISTS {}').format(sql.Identifier('public',table)))
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))

    async def test_upload_search_rag_history_and_cross_user_denial(self):
        # Datos anteriores sin propietario no deben quedar visibles al iniciar sesión.
        self.store.add(uuid4(), [ChunkInput(content='Legacy secreto')], [[1,0,0]])
        result = await self.client.post('/api/documents/upload', headers=self.headers(self.a),
                                       files={'file':('a.txt',b'Dato privado de A.')})
        self.assertEqual(result.status_code,201,result.text)
        result_b = await self.client.post('/api/documents/upload', headers=self.headers(self.b),
                                         files={'file':('b.txt',b'Dato privado de B.')})
        self.assertEqual(result_b.status_code,201,result_b.text)
        for user, filename in [(self.a,'a.txt'),(self.b,'b.txt')]:
            listing = await self.client.get('/api/documents',headers=self.headers(user))
            self.assertEqual([d['filename'] for d in listing.json()],[filename])
            search = await self.client.post('/api/vector/test-search',headers=self.headers(user),json={'query':'dato'})
            self.assertEqual([d['filename'] for d in search.json()['results']],[filename])
        first = await self.client.post('/api/chat/rag',headers=self.headers(self.a),json={'question':'dato'})
        self.assertEqual(first.status_code,200,first.text)
        cid = first.json()['conversation_id']
        self.assertEqual(first.json()['sources'][0]['document'],'a.txt')
        prompt = self.llm.generate.await_args.args[0][-1].content
        self.assertIn('Dato privado de A',prompt)
        self.assertNotIn('Dato privado de B',prompt)
        self.assertNotIn('Legacy secreto',prompt)
        second = await self.client.post('/api/chat/rag',headers=self.headers(self.a),
                                       json={'question':'otra pregunta','conversation_id':cid})
        self.assertEqual(second.status_code,200,second.text)
        self.assertEqual(second.json()['conversation_id'],cid)
        # Reabrir desde sesiones nuevas prueba persistencia, no estado del proceso.
        detail = await self.client.get('/api/conversations/'+cid,headers=self.headers(self.a))
        self.assertEqual([m['role'] for m in detail.json()['messages']],['user','assistant','user','assistant'])
        calls = self.llm.generate.await_count
        searches = self.embeddings.embed.await_count
        for other_id in [cid,str(uuid4())]:
            denied = await self.client.post('/api/chat/rag',headers=self.headers(self.b),
                                           json={'question':'dato','conversation_id':other_id})
            self.assertEqual(denied.status_code,404,denied.text)
        self.assertEqual(self.llm.generate.await_count,calls)
        self.assertEqual(self.embeddings.embed.await_count,searches)
        self.assertEqual((await self.client.get('/api/conversations/'+cid,headers=self.headers(self.b))).status_code,404)
        self.assertEqual((await self.client.get('/api/conversations',headers=self.headers(self.b))).json(),[])
        self.assertEqual(len((await self.client.get('/api/conversations',headers=self.headers(self.a))).json()),1)
        # Defensa adicional al guardar, aunque se invocase el servicio sin la comprobación inicial.
        with self.assertRaises(AppError):
            await self.interactions.save({'user_id':self.b,'conversation_id':cid,'question':'intruso','answer':'x'})
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(Message)),4)
        # Nueva conversación explícita se puede reutilizar desde el chat.
        created = await self.client.post('/api/conversations',headers=self.headers(self.b),json={'title':'Prueba B'})
        self.assertEqual(created.status_code,200,created.text)
        continued = await self.client.post('/api/chat/rag',headers=self.headers(self.b),
            json={'question':'dato','conversation_id':created.json()['id']})
        self.assertEqual(continued.status_code,200,continued.text)
        self.assertEqual(continued.json()['sources'][0]['document'],'b.txt')

    async def test_pair_is_atomic_and_rejections_are_saved(self):
        # Si la construcción del segundo mensaje falla, ni conversación ni primero se publican.
        original = Message
        def fail_assistant(**values):
            if values['role']=='assistant':
                raise RuntimeError('fallo simulado')
            return original(**values)
        with patch('app.services.interaction_service.Message',side_effect=fail_assistant):
            with self.assertRaises(RuntimeError):
                await self.interactions.save({'user_id':self.a,'question':'q','answer':'a'})
        async with self.sessions() as session:
            self.assertEqual(await session.scalar(select(func.count()).select_from(Conversation)),0)
            self.assertEqual(await session.scalar(select(func.count()).select_from(Message)),0)
        response = await self.client.post('/api/chat/rag',headers=self.headers(self.a),json={'question':'sin documentos'})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['sources'],[])
        self.llm.generate.assert_not_awaited()
        detail = await self.client.get('/api/conversations/'+response.json()['conversation_id'],headers=self.headers(self.a))
        self.assertEqual(len(detail.json()['messages']),2)

    async def test_global_and_private_documents_remain_isolated_through_chat(self):
        # Incluso con el mismo nombre, reemplazar/purgar el global no toca el privado.
        name = 'compartido.txt'
        document = {'filename': name, 'file_type': 'txt', 'size_bytes': 20, 'content_hash': 'v1'}
        self.store.replace_global_document(uuid4(), [ChunkInput(filename=name, content='Dato global inicial')],
                                           [[1, 0, 0]], document=document)
        for subject, content in [(self.a, b'Privado A'), (self.b, b'Privado B')]:
            response = await self.client.post('/api/documents/upload', headers=self.headers(subject),
                                             files={'file': (name, content)})
            self.assertEqual(response.status_code, 201, response.text)
        self.store.add(uuid4(), [ChunkInput(content='Legacy secreto')], [[1, 0, 0]])
        for subject, own, other in [(self.a, 'Privado A', 'Privado B'), (self.b, 'Privado B', 'Privado A')]:
            listing = await self.client.get('/api/documents', headers=self.headers(subject))
            self.assertEqual(listing.status_code, 200, listing.text)
            self.assertEqual([d['is_global'] for d in listing.json()], [True, False])
            search = await self.client.post('/api/vector/test-search', headers=self.headers(subject),
                                           json={'query': 'dato', 'k': 10})
            self.assertEqual({d['content'] for d in search.json()['results']}, {'Dato global inicial', own})
            self.llm.generate.return_value = '{"sufficient":true,"answer":"Respuesta con fuentes","source_ids":[1,2]}'
            answer = await self.client.post('/api/chat/rag', headers=self.headers(subject), json={'question': 'dato'})
            self.assertEqual(answer.status_code, 200, answer.text)
            self.assertEqual(len(answer.json()['sources']), 2)
            prompt = self.llm.generate.await_args.args[0][-1].content
            self.assertIn('Dato global inicial', prompt)
            self.assertIn(own, prompt)
            self.assertNotIn(other, prompt)
            self.assertNotIn('Legacy secreto', prompt)
            cid = answer.json()['conversation_id']
            history = await self.client.get('/api/conversations/' + cid, headers=self.headers(subject))
            self.assertEqual(len(history.json()['messages']), 2)
            foreign = self.b if subject == self.a else self.a
            self.assertEqual((await self.client.get('/api/conversations/' + cid,
                             headers=self.headers(foreign))).status_code, 404)
        self.assertTrue(self.store.global_document_is_current(name, 'v1'))
        self.store.replace_global_document(uuid4(), [ChunkInput(filename=name, content='Dato global actualizado')],
                                           [[1, 0, 0]], document={**document, 'content_hash': 'v2'})
        self.assertFalse(self.store.global_document_is_current(name, 'v1'))
        self.assertTrue(self.store.global_document_is_current(name, 'v2'))
        self.assertEqual(self.store.prune_global_documents([]), 1)
        for subject, own in [(self.a, 'Privado A'), (self.b, 'Privado B')]:
            self.assertEqual([r['content'] for r in self.store.search([1, 0, 0], 10, user_id=subject)], [own])

    async def test_explicit_legacy_migration_preserves_messages(self):
        async with self.sessions() as session, session.begin():
            session.add(User(id='legacy-test',username='legacy-test'))
            await session.flush()
            conv = Conversation(user_id='legacy-test',title='Anterior')
            session.add(conv)
            await session.flush()
            cid = conv.id
            session.add(Message(conversation_id=cid,role='user',content='Histórico'))
        path = Path(__file__).resolve().parents[1] / 'scripts/migrate_legacy_history.py'
        spec = importlib.util.spec_from_file_location('legacy_migration_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        def scoped_connection(*args, **kwargs):
            return Connection.connect(self.store._conninfo(), options=f'-c search_path={self.schema}')
        # Reemplazar la clase del módulo, no psycopg.Connection global.
        connection_factory = SimpleNamespace(connect=scoped_connection)
        argv = ['migrate_legacy_history.py','--legacy-user','legacy-test','--subject',self.a]
        with patch.object(module,'Connection',connection_factory), patch.object(sys,'argv',argv):
            module.main()
        async with self.sessions() as session:
            self.assertEqual((await session.get(Conversation,cid)).user_id,'legacy-test')
        with patch.object(module,'Connection',connection_factory), patch.object(sys,'argv',argv+['--apply']):
            module.main()
        async with self.sessions() as session:
            self.assertEqual((await session.get(Conversation,cid)).user_id,self.a)
            self.assertEqual(await session.scalar(select(func.count()).select_from(Message)),1)
