"""M0 recon: attempt programmatic login via /ul/api/v1/signin (no browser).

Establishes a session, fetches login params, then POSTs the signin
payload and prints the full response so we can learn the contract.
"""
from __future__ import annotations

import json
import pathlib

import httpx

RECON = pathlib.Path(__file__).resolve().parent
SECRETS = RECON.parent / "secrets"
CREDS = json.loads((SECRETS / "credentials.json").read_text(encoding="utf-8"))

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
SIGNIN_URL = "https://www.agoda.com/en-gb/account/signin.html?returnurl=%2Fen-gb%2Fpta%2Fchat"
PARAMS_URL = "https://www.agoda.com/api/cronos/layout/login/params"
SIGNIN_API = "https://www.agoda.com/ul/api/v1/signin"


def main() -> None:
    client = httpx.Client(
        headers={
            "user-agent": UA,
            "accept": "application/json, text/plain, */*",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "origin": "https://www.agoda.com",
            "referer": "https://www.agoda.com/en-gb/account/signin.html",
        },
        follow_redirects=True,
        timeout=30,
    )

    print("=== 1. GET signin page (establish session) ===")
    r = client.get(SIGNIN_URL)
    print("status:", r.status_code, "url:", r.url)
    print("cookies:", dict(client.cookies))

    print("\n=== 2. GET login params ===")
    r = client.get(PARAMS_URL)
    print("status:", r.status_code)
    (RECON / "login_params_live.json").write_text(r.text, encoding="utf-8")
    try:
        params = r.json()
        print("keys:", list(params.keys()))
        print("oneTimeToken present:", "oneTimeToken" in params)
        if "oneTimeToken" in params:
            print("oneTimeToken:", params["oneTimeToken"][:60], "...")
    except Exception:
        print(r.text[:500])

    print("\n=== 3. POST /ul/api/v1/signin ===")
    body = {
        "email": CREDS["email"],
        "password": CREDS["password"],
        "keepMeSignedIn": True,
    }
    r = client.post(
        SIGNIN_API,
        json=body,
        headers={"content-type": "application/json; charset=utf-8"},
    )
    print("status:", r.status_code)
    print("resp headers:")
    for k, v in r.headers.items():
        if k.lower() in ("set-cookie", "content-type", "x-*", "location"):
            print(f"   {k}: {v[:200]}")
    print("resp body:")
    print(r.text[:2000])
    (RECON / "signin_response.json").write_text(r.text, encoding="utf-8")
    print("\ncookies after signin:", dict(client.cookies))

    client.close()


if __name__ == "__main__":
    main()
