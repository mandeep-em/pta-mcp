"""M0 recon: find the programmatic login API by grepping the UL JS bundle.

No browser. Pure httpx. Fetches the universal-login JS + login params
config and extracts API endpoint paths and auth-related strings.
"""
from __future__ import annotations

import json
import re
import pathlib

import httpx

RECON = pathlib.Path(__file__).resolve().parent
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
BASE_HEADERS = {
    "user-agent": UA,
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "origin": "https://www.agoda.com",
    "referer": "https://www.agoda.com/en-gb/account/signin.html",
}

JS_FILES = [
    "https://cdn6.agoda.net/js/ul/spa/agoda-universal-login.0a98beb540aa7ce3.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-ul-libs.b0efa299dd23b291.js",
    "https://cdn6.agoda.net/js/ul/spa/agoda-agoda-libs.f97dc5c9e1cc00cc.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-4105.55ae93dc4d178bec.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-9482.5f170be3b86a6eeb.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-2469.3886ce28815a9583.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-7112.c8801cb49886cdb8.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-2650.614f54af70eba3d4.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-3557.0e60210896407691.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-8939.dafc726157ee6cf3.js",
    "https://cdn6.agoda.net/js/ul/spa/ul-clientside-chunk-8482.6dc9fb827d41a7f5.js",
]

ENDPOINT_RE = re.compile(r'["\'`](/ul/api/v[0-9][^"\'`\s]{0,80})["\'`]', re.I)
PATH_RE = re.compile(r'["\'`](/api/[^"\'`\s]{0,80}(?:login|signin|sign-in|auth|otp|verify|password|account)[^"\'`\s]{0,40})["\'`]', re.I)
KEYWORDS = ["password", "otp", "verify", "signin", "sign-in", "authenticate", "email", "credential", "token"]


def main() -> None:
    client = httpx.Client(headers=BASE_HEADERS, follow_redirects=True, timeout=30)

    # 1) login params config
    print("=== /api/cronos/layout/login/params ===")
    r = client.get("https://www.agoda.com/api/cronos/layout/login/params")
    print("status:", r.status_code)
    (RECON / "login_params.json").write_text(r.text, encoding="utf-8")
    try:
        print(json.dumps(r.json(), indent=2)[:2000])
    except Exception:
        print(r.text[:1000])

    # 2) grep JS bundles
    print("\n=== grepping JS bundles for endpoints ===")
    all_endpoints: set[str] = set()
    for url in JS_FILES:
        r = client.get(url)
        if r.status_code != 200:
            print(f"[{r.status_code}] {url}")
            continue
        text = r.text
        fname = url.rsplit("/", 1)[-1]
        (RECON / f"js_{fname}.txt").write_text(text, encoding="utf-8")
        eps = set(ENDPOINT_RE.findall(text)) | set(PATH_RE.findall(text))
        if eps:
            print(f"\n--- {fname} ({len(text)} chars) ---")
            for e in sorted(eps):
                print("   ", e)
            all_endpoints |= eps
        # keyword context: find 'password' usages near fetch/post
        for kw in ["password", "/otp", "verify"]:
            idxs = [m.start() for m in re.finditer(kw, text, re.I)]
            if idxs and len(idxs) < 50:
                for i in idxs[:3]:
                    snippet = text[max(0, i - 80): i + 80].replace("\n", " ")
                    print(f"   [{fname}] ...{snippet}...")

    print("\n=== ALL candidate endpoints ===")
    for e in sorted(all_endpoints):
        print("   ", e)


if __name__ == "__main__":
    main()
