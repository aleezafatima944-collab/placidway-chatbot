from pathlib import Path
from retriever import get_db

data = get_db().get()
out = []
for doc, meta in zip(data["documents"], data["metadatas"]):
    if "search-medical-pricings" in meta["url"]:
        out.append("-" * 60)
        out.append(doc)
Path("check7.txt").write_text("\n".join(out), encoding="utf-8")
print("Saved check7.txt")