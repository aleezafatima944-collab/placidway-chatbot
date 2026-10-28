import json
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

RAW_DIR = Path("data/raw")
CHROMA_DIR = "chroma_store"
COLLECTION = "placidway"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MAX_TABLE_CHARS = 600
VIDEO_PAGE_LIMIT = 3000  # the videos page is mostly noise


def clean_text(text):
    """Remove known junk from the scraped text."""
    # broken template sentence on the price list page
    text = re.sub(r"[^.\n]*=\$priceRange\?>[^.\n]*\.?", "", text)
    text = text.replace("PRICE TABLES:", "")
    text = text.replace("Share this listing", "")
    return text


def clean_row(line):
    """Return a clean table row, or None if the treatment name is missing."""
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    if len(cells) >= 2 and not cells[0] and not cells[1]:
        return None  # a price with no name: do not keep it
    return "| " + " | ".join(cells) + " |"


def split_blocks(text):
    """Split text into prose blocks and table blocks (with a title)."""
    blocks = []
    prose, table, caption = [], [], ""
    for line in text.split("\n"):
        if line.strip().startswith("|"):
            if not table:
                # a short line right before a table is its title
                if prose and len(prose[-1]) < 120:
                    caption = prose.pop()
                if prose:
                    blocks.append(("prose", "\n".join(prose)))
                prose = []
            table.append(line)
        else:
            if table:
                blocks.append(("table", caption, table))
                table, caption = [], ""
            if line.strip():
                prose.append(line.strip())
    if table:
        blocks.append(("table", caption, table))
    if prose:
        blocks.append(("prose", "\n".join(prose)))
    return blocks


def table_chunks(caption, lines):
    """Keep rows together. Long tables are split and the header is repeated."""
    rows = [r for r in (clean_row(l) for l in lines) if r and "---" not in r]
    if not rows:
        return []
    header, body = rows[0], rows[1:]
    start = (caption + "\n" if caption else "") + header
    chunks, current = [], start
    for row in body:
        if len(current) + len(row) > MAX_TABLE_CHARS and current != start:
            chunks.append(current)
            current = start
        current += "\n" + row
    chunks.append(current)
    return chunks
SECTION_STARTS = (
    "Cost of Alternative",
    "Included in the Out-Patient",
    "Included in the In-Patient",
    "Optional Specialized Procedures",
    "Excluded Services",
    "The ITC Philosophy",
    "Who Should Consider",
    "3-Week Typical Itinerary",
    "FAQs:",
)


def split_sections(prose):
    """Cut prose at known section headings, keeping the heading with its text."""
    sections, current = [], []
    for line in prose.split("\n"):
        if line.strip().startswith(SECTION_STARTS) and current:
            sections.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        sections.append("\n".join(current))
    return sections


def split_with_heading(section, splitter):
    """Split a long section, and repeat its first line (heading) in every piece."""
    lines = section.split("\n")
    heading = lines[0] if lines[0].strip().startswith(SECTION_STARTS) else ""
    pieces = splitter.split_text(section)
    if not heading:
        return pieces
    fixed = []
    for p in pieces:
        fixed.append(p if p.startswith(heading) else heading + "\n" + p)
    return fixed
def build_documents():
    splitter = RecursiveCharacterTextSplitter(chunk_size=600, chunk_overlap=80)
    
    docs = []
    for f in sorted(RAW_DIR.glob("*.json")):
        rec = json.loads(f.read_text(encoding="utf-8"))
        text = clean_text(rec["text"])
        if "profile-videos" in rec["url"]:
            text = text[:VIDEO_PAGE_LIMIT]

        pieces = []
        for block in split_blocks(text):
            if block[0] == "table":
                pieces += table_chunks(block[1], block[2])
            else:
                for section in split_sections(block[1]):
                    pieces += split_with_heading(section, splitter)
           

        for i, piece in enumerate(pieces):
            docs.append(Document(
                page_content=f"Page: {rec['title']}\n{piece}",
                metadata={"url": rec["url"], "title": rec["title"], "chunk_index": i},
            ))
        print(f"{f.name}: {len(pieces)} chunks")
    return docs

def ingest():
    docs = build_documents()
    if not docs:
        print("No documents found. Run scrape.py first.")
        return 0

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )

    # delete the old index so a refresh never leaves old data behind
    old = Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=CHROMA_DIR,
    )
    try:
        old.delete_collection()
    except Exception:
        pass

    Chroma.from_documents(
        docs,
        embeddings,
        collection_name=COLLECTION,
        persist_directory=CHROMA_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )
    print(f"\nDone. Indexed {len(docs)} chunks.")
    return len(docs)



if __name__ == "__main__":
    ingest()