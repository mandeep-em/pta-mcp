"""Find getUniversalLoginHeader, getTokenHeader, and the email signin body builder."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent
files = [p for p in RECON.glob("js_*.txt")]

needles = [
    "UniversalLoginHeader",
    "TokenHeader",
    "getUniversalLogin",
    "getTokenHeader",
    "UL-App",
    "Ul-App",
    "ul-app",
    "X-UL",
    "x-ul",
    "X-OTT",
    "x-ott",
    "OneTimeToken",
    "oneTimeToken",
    "nn=function",
    "var nn",
    "nn=function(e",
]

for f in files:
    text = f.read_text(encoding="utf-8")
    for needle in needles:
        idxs = [m.start() for m in re.finditer(re.escape(needle), text)]
        if not idxs:
            continue
        print(f"\n--- {f.name} :: {needle!r} ({len(idxs)} hits) ---")
        for i in idxs[:3]:
            ctx = text[max(0, i - 200): i + 260].replace("\n", " ")
            print(f"  ...{ctx}...\n")
