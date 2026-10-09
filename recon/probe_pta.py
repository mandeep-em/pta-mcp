"""M0 recon: probe PTA Chat APIs with exported cookies.

1. Create conversation -> capture conversation id
2. Send message -> capture raw response (detect SSE, structure)
"""
from __future__ import annotations

import json
import pathlib

import httpx

RECON = pathlib.Path(__file__).resolve().parent
SECRETS = RECON.parent / "secrets"
COOKIE = (SECRETS / "cookies.txt").read_text(encoding="utf-8").strip()

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
BASE = {
    "user-agent": UA,
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "cache-control": "no-cache",
    "origin": "https://www.agoda.com",
    "pragma": "no-cache",
    "referer": "https://www.agoda.com/pta/chat",
    "cookie": COOKIE,
}

CREATE_URL = "https://www.agoda.com/en-gb/pta/chat/api/conversations"


def main() -> None:
    client = httpx.Client(headers=BASE, timeout=60)

    print("=== 1. Create conversation ===")
    r = client.post(
        CREATE_URL,
        json={"title": "MCP probe", "conversationContext": {"chatType": "Common"}},
        headers={"content-type": "application/json"},
    )
    print("status:", r.status_code)
    print("content-type:", r.headers.get("content-type"))
    print("body:", r.text[:1500])
    (RECON / "create_conv_response.json").write_text(r.text, encoding="utf-8")

    conv_id = None
    try:
        data = r.json()
        # try common keys
        for k in ("id", "conversationId", "conversation_id", "data"):
            if k in data:
                conv_id = data[k]
                print(f"-> conversation id from {k!r}: {conv_id}")
                break
    except Exception:
        pass

    if not conv_id:
        print("!! could not find conversation id; aborting send")
        client.close()
        return

    print(f"\n=== 2. Send message to conversation {conv_id} ===")
    send_url = f"https://www.agoda.com/en-gb/pta/chat/api/conversations/{conv_id}/messages"
    body = {
        "type": "Message",
        "content": {"text": "I want to plan a 3-day trip to Tokyo. Find me hotels and things to do."},
        "context": {"pageContext": {"hostPageTypeName": "Unknown", "hostPageTypeId": -1}},
        "chatType": "Common",
    }
    # Stream to capture raw bytes + detect SSE
    with client.stream("POST", send_url, json=body, headers={"content-type": "application/json", "accept": "text/event-stream,application/json, text/plain, */*"}) as r:
        print("status:", r.status_code)
        print("content-type:", r.headers.get("content-type"))
        print("resp headers:")
        for k, v in r.headers.items():
            if k.lower() in ("content-type", "transfer-encoding", "cache-control") or k.lower().startswith("x-"):
                print(f"   {k}: {v[:160]}")
        raw = b""
        with open(RECON / "send_message_raw.bin", "wb") as f:
            try:
                for chunk in r.iter_bytes():
                    if not chunk:
                        break
                    raw += chunk
                    f.write(chunk)
                    if len(raw) > 200_000:
                        break
            except Exception as e:
                print("stream ended:", e)
    print(f"\nraw bytes captured: {len(raw)}")
    print("first 2000 bytes:")
    print(raw[:2000].decode("utf-8", errors="replace"))
    client.close()


if __name__ == "__main__":
    main()
