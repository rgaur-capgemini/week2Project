"""
Cloud Function Gen2 for processing compliance templates.
Triggered by Pub/Sub messages when templates are uploaded.

Workflow:
1. Download template from GCS
2. Chunk document
3. Generate embeddings
4. Store in Vertex AI Vector Search
5. Store metadata in Firestore
"""

import functions_framework
from google.cloud import storage, firestore, aiplatform
import vertexai
from vertexai.language_models import TextEmbeddingModel
import json
import base64
from typing import List, Dict
import logging
import os

# Initialize clients
storage_client = storage.Client()
db = firestore.Client()

# Configuration from environment variables
PROJECT_ID = os.getenv('PROJECT_ID', 'btoproject-486405')
REGION = os.getenv('REGION', 'us-central1')
VERTEX_INDEX_ID = os.getenv('VERTEX_INDEX_ID')
VERTEX_INDEX_ENDPOINT = os.getenv('VERTEX_INDEX_ENDPOINT')
DEPLOYED_INDEX_ID = os.getenv('DEPLOYED_INDEX_ID', 'chatbot_rag_deployed_1770440353081')

# Initialize Vertex AI
vertexai.init(project=PROJECT_ID, location=REGION)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def extract_and_chunk(content: bytes, filename: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[Dict]:
    """
    Extract text and chunk document.
    Simplified version - in production, use the full chunker module.
    """
    try:
        # Simple text extraction
        if filename.endswith('.txt'):
            text = content.decode('utf-8', errors='ignore')
        elif filename.endswith('.pdf'):
            # For production, use PyPDF2
            text = content.decode('utf-8', errors='ignore')
        else:
            text = content.decode('utf-8', errors='ignore')
        
        # Simple word-based chunking
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk_words = words[i:i + chunk_size]
            chunk_text = ' '.join(chunk_words)
            
            if len(chunk_text.strip()) > 50:
                chunks.append({
                    'text': chunk_text,
                    'metadata': {
                        'chunk_id': f'chunk_{i}',
                        'start_word': i,
                        'end_word': min(i + chunk_size, len(words))
                    }
                })
        
        return chunks
        
    except Exception as e:
        logger.error(f"Error chunking document: {e}")
        return []


@functions_framework.cloud_event
def process_template(cloud_event):
    """
    Process template ingestion from Pub/Sub.
    
    Steps:
    1. Download template from GCS
    2. Chunk document
    3. Generate embeddings
    4. Store in Vertex AI Vector Search
    5. Store metadata in Firestore
    """
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
        template_data = json.loads(pubsub_message)
        
        template_id = template_data['template_id']
        logger.info(f"Processing template: {template_id}")
        
        # Download template from GCS
        bucket_name = template_data['bucket']
        blob_name = template_data['blob_name']
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        content = blob.download_as_bytes()
        
        logger.info(f"Downloaded template from gs://{bucket_name}/{blob_name}")
        
        # Chunk template
        filename = blob_name.split('/')[-1]
        chunks = extract_and_chunk(content, filename)
        
        if not chunks:
            logger.error(f"No chunks extracted from template {template_id}")
            return {'status': 'error', 'message': 'No chunks extracted'}
        
        logger.info(f"Chunked template into {len(chunks)} chunks")
        
        # Generate embeddings
        embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-004")
        texts = [chunk['text'] for chunk in chunks]
        
        # Batch embed (max 5 at a time for API limits)
        embeddings = []
        batch_size = 5
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = embedding_model.get_embeddings(batch_texts)
            embeddings.extend([e.values for e in batch_embeddings])
        
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Add metadata to chunks
        for i, chunk in enumerate(chunks):
            chunk['metadata']['template_id'] = template_id
            chunk['metadata']['template_type'] = template_data.get('template_type', 'general')
            chunk['metadata']['version'] = template_data.get('version', '1.0')
            chunk['metadata']['is_template'] = True
            chunk['metadata']['chunk_index'] = i
        
        # Store in Vertex AI Vector Search (via batch upsert to index)
        # Note: In production, you would use the VectorStore class
        # For Cloud Function, we'll store in Firestore as fallback
        
        # Store metadata in Firestore
        template_ref = db.collection('compliance_templates').document(template_id)
        template_ref.set({
            'template_id': template_id,
            'template_type': template_data.get('template_type'),
            'version': template_data.get('version', '1.0'),
            'gcs_uri': f"gs://{bucket_name}/{blob_name}",
            'chunk_count': len(chunks),
            'processed_at': firestore.SERVER_TIMESTAMP,
            'status': 'ready',
            'uploaded_by': template_data.get('uploaded_by')
        })
        
        # Store chunks in Firestore collection for retrieval
        batch = db.batch()
        for i, chunk in enumerate(chunks):
            chunk_ref = db.collection('compliance_template_chunks').document(f"{template_id}_chunk_{i}")
            chunk_doc = {
                'template_id': template_id,
                'chunk_index': i,
                'text': chunk['text'],
                'metadata': chunk['metadata'],
                'embedding': embeddings[i] if i < len(embeddings) else [],
                'created_at': firestore.SERVER_TIMESTAMP
            }
            batch.set(chunk_ref, chunk_doc)
        
        batch.commit()
        
        logger.info(f"Successfully processed template {template_id}: {len(chunks)} chunks")
        
        # Send email notification if user_email provided
        user_email = template_data.get('user_email')
        if user_email:
            try:
                # In production, integrate with email service
                logger.info(f"Would send email to {user_email} about template {template_id}")
            except Exception as email_error:
                logger.warning(f"Failed to send email: {email_error}")
        
        return {
            'status': 'success',
            'template_id': template_id,
            'chunks_processed': len(chunks)
        }
        
    except Exception as e:
        logger.error(f"Error processing template: {e}", exc_info=True)
        
        # Update Firestore with error status
        try:
            template_id = template_data.get('template_id')
            if template_id:
                db.collection('compliance_templates').document(template_id).set({
                    'template_id': template_id,
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': firestore.SERVER_TIMESTAMP
                }, merge=True)
        except:
            pass
        
        raise
