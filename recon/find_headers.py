"""Find how oneTimeToken and appId are transmitted in UL requests."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent
files = [p for p in RECON.glob("js_*.txt")]

needles = [
    "oneTimeToken",
    "OneTimeToken",
    "one-time-token",
    "X-OneTime",
    "x-one-time",
    "OTT",
    "appId",
    "X-App",
    "x-app",
    "X-Ul-App",
    "X-UL-",
    "x-ul-",
    "X-Client",
    "x-client",
    "X-Csrf",
    "x-csrf",
    "Xsrf",
    "xsrf",
    "RequestVerification",
    "defaultHeaders",
    "commonHeaders",
]

for f in files:
    text = f.read_text(encoding="utf-8")
    for needle in needles:
        idxs = [m.start() for m in re.finditer(re.escape(needle), text, re.I)]
        if not idxs:
            continue
        print(f"\n--- {f.name} :: {needle!r} ({len(idxs)} hits) ---")
        for i in idxs[:2]:
            ctx = text[max(0, i - 120): i + 160].replace("\n", " ")
            print(f"   ...{ctx}...")
