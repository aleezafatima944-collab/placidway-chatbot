import json
from pathlib import Path

text = json.loads(Path("data/raw/01.json").read_text(encoding="utf-8"))["text"]
out = []
for line in text.split("\n"):
    s = line.strip()
    if s and not s.startswith(("-", "|")) and len(s) < 90:
        out.append(s)
Path("headings.txt").write_text("\n".join(out), encoding="utf-8")
print("Saved headings.txt")