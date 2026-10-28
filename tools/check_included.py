import json
from pathlib import Path

from retriever import get_db

# 1. Is the list in the raw scraped page?
raw = json.loads(Path("data/raw/01.json").read_text(encoding="utf-8"))["text"]
pos = raw.find("Included in the Out-Patient")
print("In raw 01.json at position:", pos)
if pos >= 0:
    print(raw[pos:pos + 700])

# 2. Is it in the index?
data = get_db().get()
found = [d for d in data["documents"] if "Included in the Out-Patient" in d]
print("\nChunks in index containing that phrase:", len(found))
for d in found[:3]:
    print("-" * 50)
    print(d[:400])