
# Architecture Notes

- **Chunking**: simple char-based with overlap (tune with tokens later)
- **Embeddings**: `text-embedding-004`
- **Vector Search**: Vertex AI Vector Search Index + Endpoint (created via gcloud script)
- **Generation**: Gemini 1.5 (Pro/Flash configurable)
- **Security**: Service Account, Secret Manager; lock down in Week‑2 with JWT/IAM
- **Observability**: OTel hooks (extend with exporters to Cloud Trace)
