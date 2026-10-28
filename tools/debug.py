import json
import re
from pathlib import Path

from retriever import retrieve

out = ["RECOVERY TEXT IN THE RAW PAGES"]
for f in sorted(Path("data/raw").glob("*.json")):
    text = json.loads(f.read_text(encoding="utf-8"))["text"]
    for m in re.finditer("recover", text, re.I):
        s, e = max(0, m.start() - 150), m.end() + 250
        out.append(f"{f.name}: ..." + text[s:e].replace("\n", " ") + "...")

queries = [
    "ozone therapy price Turkey Mexico clinic",
    "recovery time after treatment ITC",
    "out-patient program nutritional support medications follow-up care",
]
for q in queries:
    out.append("")
    out.append("QUERY: " + q)
    for text, url, title, d in retrieve(q):
        line = f"  {d:.3f} | {url[-40:]} | {text[:150]}"
        out.append(line.replace("\n", " "))

Path("debug.txt").write_text("\n".join(out), encoding="utf-8")
print("Saved debug.txt")