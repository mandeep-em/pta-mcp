"""Find where .signIn( is called with its body."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent
files = [p for p in RECON.glob("js_*.txt")]

pats = [r"\.signIn\(", r"signIn\(\{", r"\.signIn\b", r"password:", r"keepMeSignedIn", r"checkPasskey", r"oneTimeToken", r"OneTimeToken"]
for f in files:
    text = f.read_text(encoding="utf-8")
    for pat in pats:
        idxs = [m.start() for m in re.finditer(pat, text)]
        if not idxs:
            continue
        print(f"\n--- {f.name} :: /{pat}/ ({len(idxs)} hits) ---")
        for i in idxs[:4]:
            ctx = text[max(0, i - 180): i + 220].replace("\n", " ")
            print(f"  ...{ctx}...\n")
