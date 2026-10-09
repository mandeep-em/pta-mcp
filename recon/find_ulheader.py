"""Find buildUniversalLoginHeader definition + deviceIntelligence headers."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent
files = [p for p in RECON.glob("js_*.txt")]

for f in files:
    text = f.read_text(encoding="utf-8")
    for needle in ["buildUniversalLoginHeader=function", "buildUniversalLoginHeader:", "buildUniversalLoginHeader ", "getDeviceIntelligenceHeaders", "DeviceIntelligence", "AG-Initiator-Version", "AG-Origin", "UL-App-Id", "UL-Fallback-Origin"]:
        idxs = [m.start() for m in re.finditer(re.escape(needle), text)]
        if not idxs:
            continue
        print(f"\n--- {f.name} :: {needle!r} ({len(idxs)} hits) ---")
        for i in idxs[:2]:
            ctx = text[max(0, i - 120): i + 320].replace("\n", " ")
            print(f"  ...{ctx}...\n")
