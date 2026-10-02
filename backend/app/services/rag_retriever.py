from app.schemas.vector import VectorSearchRequest


class RAGRetriever:
    def __init__(self, vector_service, top_k: int):
        self.vector_service = vector_service
        self.top_k = top_k

    async def retrieve(self, question: str):
        response = await self.vector_service.search(VectorSearchRequest(query=question, k=self.top_k))
        return response.results
