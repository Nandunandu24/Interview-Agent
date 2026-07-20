import re
import math
from collections import Counter

class ResumeRAG:
    """
    Lightweight Retrieval-Augmented Generation (RAG) Engine for Candidate Resumes.
    Chunks resumes into semantic sections and performs vector similarity search (TF-IDF + Cosine Similarity)
    to retrieve top-K relevant chunks for question generation.
    """
    def __init__(self, resume_text: str = ""):
        self.chunks = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self.use_sklearn = False
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self.TfidfVectorizer = TfidfVectorizer
            self.cosine_similarity = cosine_similarity
            self.use_sklearn = True
        except Exception:
            self.use_sklearn = False

        if resume_text:
            self.index_resume(resume_text)

    def chunk_resume(self, resume_text: str) -> list[str]:
        """
        Splits resume text into semantic, logical structural chunks 
        (e.g., projects, experience blocks, skills list, education).
        """
        if not resume_text or not resume_text.strip():
            return []

        # Split by double linebreaks or section indicators
        raw_paragraphs = re.split(r'\n\s*\n+', resume_text.strip())
        chunks = []

        for p in raw_paragraphs:
            p_clean = p.strip()
            if not p_clean:
                continue
            
            # If paragraph is very long (> 600 chars), split into sentences/bullet points
            if len(p_clean) > 600:
                bullets_or_lines = re.split(r'\n|(?<=[.!?])\s+', p_clean)
                current_chunk = []
                current_len = 0
                for line in bullets_or_lines:
                    line_clean = line.strip()
                    if not line_clean:
                        continue
                    if current_len + len(line_clean) > 400 and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = [line_clean]
                        current_len = len(line_clean)
                    else:
                        current_chunk.append(line_clean)
                        current_len += len(line_clean)
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
            else:
                chunks.append(p_clean)

        # Deduplicate while preserving order
        unique_chunks = []
        seen = set()
        for c in chunks:
            if c not in seen and len(c) > 15:
                seen.add(c)
                unique_chunks.append(c)

        return unique_chunks

    def index_resume(self, resume_text: str):
        """Chunk and index resume text into vector store."""
        self.chunks = self.chunk_resume(resume_text)
        if not self.chunks:
            return

        if self.use_sklearn:
            try:
                self.vectorizer = self.TfidfVectorizer(stop_words='english')
                self.tfidf_matrix = self.vectorizer.fit_transform(self.chunks)
            except Exception:
                self.use_sklearn = False

    def query(self, query_str: str, top_k: int = 3) -> list[str]:
        """
        Retrieves top-K relevant resume chunks using Cosine Similarity vector search.
        """
        if not self.chunks:
            return []

        top_k = min(top_k, len(self.chunks))

        if self.use_sklearn and self.vectorizer and self.tfidf_matrix is not None:
            try:
                query_vec = self.vectorizer.transform([query_str])
                scores = self.cosine_similarity(query_vec, self.tfidf_matrix).flatten()
                top_indices = scores.argsort()[::-1][:top_k]
                
                retrieved = []
                for idx in top_indices:
                    # Include if similarity > 0 or fallback to top items
                    retrieved.append(self.chunks[idx])
                return retrieved
            except Exception:
                pass

        # Fallback pure-Python vector similarity calculation (TF-IDF approximation)
        return self._pure_python_query(query_str, top_k)

    def _tokenize(self, text: str) -> list[str]:
        return re.findall(r'\w+', text.lower())

    def _pure_python_query(self, query_str: str, top_k: int) -> list[str]:
        """Pure Python fallback for term vector cosine similarity search."""
        query_words = Counter(self._tokenize(query_str))
        if not query_words:
            return self.chunks[:top_k]

        scores = []
        for chunk in self.chunks:
            chunk_words = Counter(self._tokenize(chunk))
            # Calculate cosine similarity of word frequencies
            intersection = set(query_words.keys()) & set(chunk_words.keys())
            dot_product = sum(query_words[w] * chunk_words[w] for w in intersection)
            
            mag_q = math.sqrt(sum(v**2 for v in query_words.values()))
            mag_c = math.sqrt(sum(v**2 for v in chunk_words.values()))
            
            sim = dot_product / (mag_q * mag_c) if (mag_q * mag_c) > 0 else 0.0
            scores.append((sim, chunk))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [chunk for sim, chunk in scores[:top_k]]

    def get_indexed_chunk_count(self) -> int:
        return len(self.chunks)
