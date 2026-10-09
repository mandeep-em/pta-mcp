"""Extract signin request body + headers from the UL JS bundle."""
from __future__ import annotations
import pathlib, re

RECON = pathlib.Path(__file__).resolve().parent

files = [
    RECON / "js_agoda-universal-login.0a98beb540aa7ce3.js.txt",
    RECON / "js_ul-clientside-chunk-ul-libs.b0efa299dd23b291.js.txt",
    RECON / "js_ul-clientside-chunk-2650.614f54af70eba3d4.js.txt",
    RECON / "js_ul-clientside-chunk-8482.6dc9fb827d41a7f5.js.txt",
]

needles = [
    "/ul/api/v1/signin\"",
    "signIn",
    "captchaVerifyInfo",
    "oneTimeToken",
    "appId",
    "x-ul",
    "x-agoda",
    "X-Ul",
    "X-Agoda",
    "headers:",
    "email:",
    "password:",
    "memberId",
]

for f in files:
    if not f.exists():
        continue
    text = f.read_text(encoding="utf-8")
    print(f"\n========== {f.name} ({len(text)} chars) ==========")
    for needle in needles:
        idxs = [m.start() for m in re.finditer(re.escape(needle), text)]
        if not idxs:
            continue
        print(f"\n--- needle: {needle!r} ({len(idxs)} hits) ---")
        for i in idxs[:2]:
            ctx = text[max(0, i - 160): i + 200].replace("\n", " ")
            print(f"   ...{ctx}...")
