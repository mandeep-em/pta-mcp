"""M0 recon: attempt signin with the credentials body + UL-App-Id header."""
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

    # establish session
    client.get(SIGNIN_URL)
    params = client.get(PARAMS_URL).json()
    ott = params.get("oneTimeToken")
    print("oneTimeToken:", (ott[:50] + "...") if ott else None)

    body = {
        "credentials": {
            "authType": "email",
            "username": CREDS["email"],
            "password": CREDS["password"],
        },
        "keepMeSignedIn": True,
    }
    headers = {
        "content-type": "application/json; charset=utf-8",
        "UL-App-Id": "dictator",
        "AG-Origin": "https://www.agoda.com",
    }
    if ott:
        headers["Authorization"] = ott

    print("\n=== POST /ul/api/v1/signin (credentials body) ===")
    r = client.post(SIGNIN_API, json=body, headers=headers)
    print("status:", r.status_code)
    print("resp headers:")
    for k, v in r.headers.items():
        if k.lower() in ("set-cookie", "content-type", "location") or k.lower().startswith("x-"):
            print(f"   {k}: {v[:240]}")
    print("resp body:")
    print(r.text[:2500])
    (RECON / "signin_response2.json").write_text(r.text, encoding="utf-8")
    print("\ncookies:", list(client.cookies.keys()))
    client.close()


if __name__ == "__main__":
    main()
