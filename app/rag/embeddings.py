
from typing import List
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

class VertexTextEmbedder:
    def __init__(self, project: str, location: str):
        aiplatform.init(project=project, location=location)
        self.model = TextEmbeddingModel.from_pretrained("text-embedding-004")

    def embed(self, texts: List[str]) -> List[List[float]]:
        # Each text returns a single embedding vector
        resp = self.model.get_embeddings(texts)
        return [e.values for e in resp]
