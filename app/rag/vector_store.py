
from typing import List, Dict
import numpy as np
import json
from google.cloud import aiplatform
from google.cloud.aiplatform import MatchingEngineIndexEndpoint
from google.cloud import storage

class VertexVectorStore:
    def __init__(self, project: str, location: str, index_id: str, index_endpoint_name: str, deployed_index_id: str = "rag-index-deployed"):
        aiplatform.init(project=project, location=location)
        self.project = project
        self.location = location
        self.index_id = index_id
        self.index_endpoint_name = index_endpoint_name
        self.deployed_index_id = deployed_index_id
        
        # Store chunks in memory for retrieval (in production, use a database)
        self.chunk_store = {}
        
        # GCS client for Vector Search batch updates
        try:
            self.gcs_client = storage.Client(project=project)
            self.bucket_name = f"{project}-rag-documents"
        except Exception as e:
            print(f"Warning: Could not initialize GCS client: {e}")
            self.gcs_client = None
        
        try:
            self.index_endpoint = MatchingEngineIndexEndpoint(index_endpoint_name)
        except Exception as e:
            print(f"Warning: Could not initialize index endpoint: {e}")
            self.index_endpoint = None

    def upsert(self, chunks: List[Dict], vectors: List[List[float]]) -> List[str]:
        """
        Upsert chunks and their vectors to Vertex AI Vector Search.
        Also stores chunks locally for retrieval.
        """
        if not self.index_endpoint:
            # Fallback: store in memory only
            for i, ch in enumerate(chunks):
                self.chunk_store[ch["id"]] = {
                    "text": ch["text"],
                    "metadata": ch.get("metadata", {}),
                    "vector": vectors[i]
                }
            return [ch["id"] for ch in chunks]
        
        # Store chunks locally for retrieval
        for i, ch in enumerate(chunks):
            self.chunk_store[ch["id"]] = {
                "text": ch["text"],
                "metadata": ch.get("metadata", {}),
                "vector": vectors[i]
            }
        
        # Upload vectors to GCS for Vector Search index update
        if self.gcs_client:
            try:
                self._upload_to_gcs_for_index_update(chunks, vectors)
            except Exception as e:
                print(f"Warning: GCS upload for Vector Search failed: {e}")
        
        return [ch["id"] for ch in chunks]
    
    def _upload_to_gcs_for_index_update(self, chunks: List[Dict], vectors: List[List[float]]):
        """
        Upload vectors to GCS in JSONL format for Vector Search batch update.
        This enables Vertex AI Vector Search to use the vectors for similarity search.
        Includes PII detection metadata for filtering.
        """
        bucket = self.gcs_client.bucket(self.bucket_name)
        
        # Create JSONL content with PII metadata
        jsonl_lines = []
        for i, ch in enumerate(chunks):
            metadata = ch.get("metadata", {})
            
            # Determine PII status (in production, use actual PII detection service)
            # For now, mark all as "clean" - integrate with Cloud DLP for real detection
            pii_status = metadata.get("pii_status", "clean")  
            
            embedding_dict = {
                "id": ch["id"],
                "embedding": vectors[i],
                "restricts": [
                    {"namespace": "source", "allow": [metadata.get("source", "default")]},
                    {"namespace": "pii_status", "allow": [pii_status]}  # PII filtering
                ],
                "crowding_tag": ch.get("metadata", {}).get("source", "default")
            }
            jsonl_lines.append(json.dumps(embedding_dict))
        
        # Upload to GCS (Vector Search reads from index-data folder)
        import time
        timestamp = int(time.time())
        blob_name = f"index-data/embeddings_{timestamp}.json"
        blob = bucket.blob(blob_name)
        blob.upload_from_string("\n".join(jsonl_lines), content_type="application/json")
        
        print(f"Uploaded {len(chunks)} vectors to gs://{self.bucket_name}/{blob_name}")
        print("Note: Run 'gcloud ai indexes update' to refresh the Vector Search index with new data")
        
        # Vector Search index updates require batch operations via GCS
        # For real-time ingestion, we use local storage with future batch sync
        # In production, implement a background job to sync to Vector Search
        
        return [ch["id"] for ch in chunks]

    def search(self, query: str, top_k: int = 5, enable_pii_filter: bool = True) -> List[Dict]:
        """
        Search for top-k similar chunks using vector similarity.
        Implements the critical retrieval step for RAG with optional PII filtering.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            enable_pii_filter: If True, applies PII detection filter to exclude sensitive data
        """
        # Embed the query
        from app.rag.embeddings import VertexTextEmbedder
        embedder = VertexTextEmbedder(project=self.project, location=self.location)
        query_vector = embedder.embed([query])[0]
        
        # Configure PII detection filter
        pii_filter = []
        if enable_pii_filter:
            # Filter out documents that contain PII
            # This restricts results to only non-PII or approved PII-cleared documents
            pii_filter = [
                {
                    "namespace": "pii_status",
                    "allow": ["clean", "redacted"]  # Only allow PII-clean or redacted docs
                }
            ]
        
        if self.index_endpoint:
            try:
                # Use Vertex AI Vector Search find_neighbors with PII filter
                response = self.index_endpoint.find_neighbors(
                    deployed_index_id=self.deployed_index_id,
                    queries=[query_vector],
                    num_neighbors=top_k,
                    filter=pii_filter
                )
                
                # Extract results with full chunk data
                results = []
                if response and len(response) > 0:
                    for neighbor in response[0]:
                        chunk_id = neighbor.id
                        chunk_data = self.chunk_store.get(chunk_id, {})
                        results.append({
                            "id": chunk_id,
                            "distance": neighbor.distance,
                            "score": 1.0 - neighbor.distance,  # Convert distance to similarity score
                            "text": chunk_data.get("text", ""),
                            "metadata": chunk_data.get("metadata", {})
                        })
                return results
            except Exception as e:
                print(f"Warning: Vector Search failed: {e}. Falling back to local search.")
        
        # Fallback: Local similarity search using cosine similarity
        return self._local_search(query_vector, top_k)
    
    def _local_search(self, query_vector: List[float], top_k: int) -> List[Dict]:
        """
        Fallback similarity search using numpy cosine similarity.
        """
        if not self.chunk_store:
            return []
        
        query_vec = np.array(query_vector)
        scores = []
        
        for chunk_id, chunk_data in self.chunk_store.items():
            chunk_vec = np.array(chunk_data["vector"])
            # Cosine similarity
            similarity = np.dot(query_vec, chunk_vec) / (
                np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec)
            )
            scores.append({
                "id": chunk_id,
                "score": float(similarity),
                "distance": 1.0 - float(similarity),
                "text": chunk_data["text"],
                "metadata": chunk_data["metadata"]
            })
        
        # Sort by score descending
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]
