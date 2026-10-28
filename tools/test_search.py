from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)

db = Chroma(collection_name="placidway", embedding_function=embeddings,
            persist_directory="chroma_store")
QUESTIONS = [
    "How much does anal cancer treatment cost in Tijuana?",
    "What is included in the out-patient program?",
    "Is ozone therapy cheaper in Turkey or Mexico?",
    "How much is ozone therapy at Fizikon in Turkey?",
    "What is the price of In-Patient program for adrenal cancer?",
    "Can you book me an appointment for tomorrow?",
    "What is the weather in Cancun?",
    "Is this surgery safe for my diabetes?",
    "What is the cost of cancer treatment in Tijuana?",
    "ٹیجوانا میں کینسر کے علاج کی قیمت کیا ہے؟",
]


lines = []
for q in QUESTIONS:
    lines.append("=" * 70)
    lines.append("Q: " + q)
    for doc, score in db.similarity_search_with_score(q, k=4):
        first = doc.page_content.replace("\n", " ")[:110]
        lines.append(f"  score {score:.3f} | {doc.metadata['url'][-45:]} | {first}")

with open("test_search.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print("Saved test_search.txt")