
import io, re
from typing import List, Tuple, Dict, Optional
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from PyPDF2 import PdfReader

MAX_CHARS = 2800
OVERLAP = 300

# Import semantic chunker
try:
    from app.rag.semantic_chunker import create_semantic_chunks
    SEMANTIC_CHUNKING_AVAILABLE = True
except ImportError:
    SEMANTIC_CHUNKING_AVAILABLE = False


def extract_and_chunk(
    docs: List[Tuple[str, bytes]], 
    pii_detector=None, 
    embedder=None,
    use_semantic_chunking: bool = True
) -> List[Dict]:
    '''Extract text from uploaded files and produce chunks with PII detection.
    
    Args:
        docs: List of (filename, content) tuples
        pii_detector: Optional PIIDetector instance for scanning chunks
        embedder: Optional embedder for semantic chunking
        use_semantic_chunking: Use semantic chunking if available (default: True)
    
    Returns list of dicts: {"id": str, "text": str, "metadata": {...}}
    '''
    out = []
    for fname, content in docs:
        text = extract_text(fname, content)
        
        # Use semantic chunking if available and requested
        if use_semantic_chunking and SEMANTIC_CHUNKING_AVAILABLE and embedder:
            try:
                chunks = create_semantic_chunks(text, embedder=embedder)
            except Exception:
                # Fallback to basic chunking
                chunks = chunk_text(text)
        else:
            chunks = chunk_text(text)
        for i, ch in enumerate(chunks):
            metadata = {"source": fname, "chunk": i}
            
            # Run PII detection if detector is provided
            if pii_detector:
                try:
                    pii_result = pii_detector.detect_pii(ch)
                    metadata["pii_status"] = pii_result["status"]
                    metadata["pii_detected"] = pii_result["has_pii"]
                    metadata["pii_types"] = pii_result["pii_types"]
                except Exception as e:
                    # Fail open - if PII detection fails, mark as clean
                    metadata["pii_status"] = "clean"
                    metadata["pii_detected"] = False
            else:
                # No PII detection - mark as clean by default
                metadata["pii_status"] = "clean"
                metadata["pii_detected"] = False
            
            out.append({
                "id": f"{fname}-{i}",
                "text": ch,
                "metadata": metadata
            })
    return out


def extract_text(fname: str, content: bytes) -> str:
    name = fname.lower()
    if name.endswith('.pdf'):
        reader = PdfReader(io.BytesIO(content))
        text = []
        for page in reader.pages:
            text.append(page.extract_text() or "")
        return "\n".join(text)
    if name.endswith('.html') or name.endswith('.htm'):
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text(" ", strip=True)
    if name.endswith('.docx'):
        doc = DocxDocument(io.BytesIO(content))
        return "\n".join([p.text for p in doc.paragraphs])
    # Fallback as utf-8 text
    try:
        return content.decode('utf-8', errors='ignore')
    except Exception:
        return ""


def chunk_text(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + MAX_CHARS, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - OVERLAP)
    return chunks
