
import io, re
from typing import List, Tuple, Dict, Optional
from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from PyPDF2 import PdfReader

MAX_CHARS = 2800
OVERLAP = 300

# Dynamic chunking parameters
SENTENCE_ENDINGS = r'[.!?]\s+'
PARAGRAPH_SEPARATOR = r'\n\n+'


def extract_and_chunk(docs: List[Tuple[str, bytes]], pii_detector=None, use_dynamic_chunking: bool = True) -> List[Dict]:
    '''Extract text from uploaded files and produce chunks with PII detection.
    
    Args:
        docs: List of (filename, content) tuples
        pii_detector: Optional PIIDetector instance for scanning chunks
        use_dynamic_chunking: If True, use semantic-aware chunking; if False, use fixed-size
    
    Returns list of dicts: {"id": str, "text": str, "metadata": {...}}
    '''
    out = []
    for fname, content in docs:
        text = extract_text(fname, content)
        
        # Use dynamic chunking if enabled, otherwise fall back to fixed-size
        if use_dynamic_chunking:
            chunks = chunk_text_dynamic(text)
        else:
            chunks = chunk_text(text)
            
        for i, ch in enumerate(chunks):
            metadata = {"source": fname, "chunk": i, "chunking_method": "dynamic" if use_dynamic_chunking else "fixed"}
            
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
    """Fixed-size chunking with overlap (legacy method)."""
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


def chunk_text_dynamic(text: str, min_chunk_size: int = 500, max_chunk_size: int = 3000, overlap: int = 200) -> List[str]:
    """
    Dynamic/Adaptive chunking that respects document structure.
    
    Strategy:
    1. Split on paragraph boundaries first
    2. Split long paragraphs on sentence boundaries
    3. Maintain semantic coherence while staying within size limits
    4. Add overlap between chunks for context continuity
    
    Args:
        text: Input text to chunk
        min_chunk_size: Minimum characters per chunk (avoid too small chunks)
        max_chunk_size: Maximum characters per chunk
        overlap: Number of characters to overlap between chunks
    
    Returns:
        List of text chunks with semantic boundaries
    """
    text = text.strip()
    if not text:
        return []
    
    # Split into paragraphs first (respects document structure)
    paragraphs = re.split(PARAGRAPH_SEPARATOR, text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]
    
    chunks = []
    current_chunk = []
    current_size = 0
    
    for para in paragraphs:
        para_size = len(para)
        
        # If paragraph itself is too large, split it by sentences
        if para_size > max_chunk_size:
            sentences = re.split(SENTENCE_ENDINGS, para)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            for sent in sentences:
                sent_size = len(sent)
                
                # If adding this sentence exceeds max, save current chunk
                if current_size + sent_size > max_chunk_size and current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append(chunk_text)
                    
                    # Keep last part for overlap
                    overlap_text = chunk_text[-overlap:] if len(chunk_text) > overlap else chunk_text
                    current_chunk = [overlap_text, sent]
                    current_size = len(overlap_text) + sent_size
                else:
                    current_chunk.append(sent)
                    current_size += sent_size
        
        # If adding this paragraph exceeds max, save current chunk
        elif current_size + para_size > max_chunk_size and current_chunk:
            chunk_text = ' '.join(current_chunk)
            
            # Only save if chunk meets minimum size
            if len(chunk_text) >= min_chunk_size:
                chunks.append(chunk_text)
                
                # Keep last part for overlap
                overlap_text = chunk_text[-overlap:] if len(chunk_text) > overlap else chunk_text
                current_chunk = [overlap_text, para]
                current_size = len(overlap_text) + para_size
            else:
                # Chunk too small, keep building
                current_chunk.append(para)
                current_size += para_size
        else:
            # Add paragraph to current chunk
            current_chunk.append(para)
            current_size += para_size
    
    # Add remaining chunk
    if current_chunk:
        chunk_text = ' '.join(current_chunk)
        if len(chunk_text) >= min_chunk_size or not chunks:  # Always keep at least one chunk
            chunks.append(chunk_text)
    
    # Final pass: merge very small chunks
    merged_chunks = []
    i = 0
    while i < len(chunks):
        chunk = chunks[i]
        
        # If chunk is too small and there's a next chunk, merge them
        if len(chunk) < min_chunk_size and i + 1 < len(chunks):
            merged = chunk + ' ' + chunks[i + 1]
            if len(merged) <= max_chunk_size:
                merged_chunks.append(merged)
                i += 2  # Skip next chunk as it's been merged
                continue
        
        merged_chunks.append(chunk)
        i += 1
    
    return merged_chunks if merged_chunks else [text]  # Fallback to original text

