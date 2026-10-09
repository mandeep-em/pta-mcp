"""Find authType + credentials construction for signin."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent
files = [p for p in RECON.glob("js_*.txt")]

for f in files:
    text = f.read_text(encoding="utf-8")
    for pat in ["authType", "credentials:{", "credentials:{" , "authType:"]:
        idxs = [m.start() for m in re.finditer(re.escape(pat), text)]
        if not idxs:
            continue
        print(f"\n--- {f.name} :: {pat!r} ({len(idxs)} hits) ---")
        for i in idxs[:5]:
            ctx = text[max(0, i - 220): i + 240].replace("\n", " ")
            print(f"  ...{ctx}...\n")
