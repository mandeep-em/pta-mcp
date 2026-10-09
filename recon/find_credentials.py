"""Find the credentials object shape used in signin."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent
files = [p for p in RECON.glob("js_*.txt")]

for f in files:
    text = f.read_text(encoding="utf-8")
    idxs = [m.start() for m in re.finditer(r"credentials", text, re.I)]
    if not idxs:
        continue
    print(f"\n===== {f.name} ({len(idxs)} hits) =====")
    for i in idxs[:6]:
        ctx = text[max(0, i - 200): i + 220].replace("\n", " ")
        print(f"  ...{ctx}...\n")
