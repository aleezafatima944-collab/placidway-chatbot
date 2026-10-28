import json
import re
from pathlib import Path

lines_out = []

for f in sorted(Path("data/raw").glob("*.json")):
    rec = json.loads(f.read_text(encoding="utf-8"))
    text = rec["text"]
    lines_out.append("=" * 70)
    lines_out.append(f"{f.name} | {rec['title']}")
    lines_out.append(
        f"chars: {len(text)} | '$': {text.count('$')} | 'USD': {text.count('USD')}"
    )
    counts = []
    for word in ["price", "cost", "includes", "included", "recovery", "days", "duration"]:
        counts.append(f"{word}: {len(re.findall(word, text, re.I))}")
    lines_out.append("  " + " | ".join(counts))
    for line in text.split("\n"):
        if "$" in line or "USD" in line:
            lines_out.append("   > " + line[:160])

Path("audit.txt").write_text("\n".join(lines_out), encoding="utf-8")
print("Saved audit.txt")