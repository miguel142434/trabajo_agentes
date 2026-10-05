from app.schemas.vector import VectorSearchRequest


class RAGRetriever:
    def __init__(self, vector_service, top_k: int):
        self.vector_service = vector_service
        self.top_k = top_k

    async def retrieve(self, question: str, *, user_id=None):
        response = await self.vector_service.search(VectorSearchRequest(query=question, k=self.top_k), user_id=user_id)
        return response.results
