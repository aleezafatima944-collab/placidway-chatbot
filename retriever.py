from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHROMA_DIR = "chroma_store"
COLLECTION = "placidway"
TOP_K = 8
MAX_DISTANCE = 0.75  # above this, a chunk is treated as unrelated

_db = None


def get_db():
    """Open the database once and reuse it."""
    global _db
    if _db is None:
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBED_MODEL,
            encode_kwargs={"normalize_embeddings": True},
        )
        _db = Chroma(
            collection_name=COLLECTION,
            embedding_function=embeddings,
            persist_directory=CHROMA_DIR,
        )
    return _db


def reset_db():
    """Call this after a refresh, so the new index is loaded."""
    global _db
    _db = None


def retrieve(question):
    """Return a list of (text, url, title, distance) that are close enough."""
    results = get_db().similarity_search_with_score(question, k=TOP_K)
    kept = []
    for doc, distance in results:
        if distance <= MAX_DISTANCE:
            kept.append((
                doc.page_content,
                doc.metadata["url"],
                doc.metadata["title"],
                distance,
            ))
    return kept
import re

STOPWORDS = {
    "the", "a", "an", "is", "are", "in", "at", "of", "or", "and", "for", "to",
    "how", "much", "what", "does", "do", "cost", "price", "cheaper", "than",
    "treatment", "therapy", "program", "which", "can", "i", "my", "me", "it",
}


def keyword_search(question, limit=3):
    """Find chunks that contain the rarer words of the question (exact match)."""
    words = [w for w in re.findall(r"[a-zA-Z]{4,}", question.lower())
             if w not in STOPWORDS]
    if not words:
        return []
    data = get_db().get()
    scored = []
    for doc, meta in zip(data["documents"], data["metadatas"]):
        low = doc.lower()
        hits = sum(1 for w in set(words) if w in low)
        if hits >= 2:
            scored.append((hits, doc, meta))
    scored.sort(key=lambda x: -x[0])
    return [(doc, meta["url"], meta["title"], 0.5) for _, doc, meta in scored[:limit]]
def retrieve_many(queries, limit=10):
    """Vector search + keyword search, remove duplicates, keep the closest."""
    best = {}
    for q in queries:
        for text, url, title, dist in retrieve(q) + keyword_search(q):
            if text not in best or dist < best[text][3]:
                best[text] = (text, url, title, dist)
    return sorted(best.values(), key=lambda c: c[3])[:limit]

if __name__ == "__main__":
    for q in ["What is included in the out-patient program?",
              "What is the weather in Cancun?"]:
        hits = retrieve(q)
        print("Q:", q, "->", len(hits), "chunks kept")
        for text, url, title, d in hits:
            print(f"   {d:.3f} | {text[:90].replace(chr(10), ' ')}")