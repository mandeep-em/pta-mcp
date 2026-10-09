"""Probe: send a hotel-specific query and dump every SSE event's full structure.

Goal: see exactly how the final response (with hotel URLs/links) is encoded
so we can fix the client's event handling.
"""
from __future__ import annotations

import json
import pathlib

import httpx

RECON = pathlib.Path(__file__).resolve().parent
COOKIE = (RECON.parent / "secrets" / "cookies.txt").read_text(encoding="utf-8").strip()

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
BASE = {
    "user-agent": UA,
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "origin": "https://www.agoda.com",
    "referer": "https://www.agoda.com/pta/chat",
    "cookie": COOKIE,
}
CREATE_URL = "https://www.agoda.com/en-gb/pta/chat/api/conversations"


def main() -> None:
    client = httpx.Client(headers=BASE, timeout=120)
    r = client.post(
        CREATE_URL,
        json={"title": "hotel probe", "conversationContext": {"chatType": "Common"}},
        headers={"content-type": "application/json"},
    )
    r.raise_for_status()
    cid = r.json()["id"]
    print(f"conversation id: {cid}")

    send_url = f"https://www.agoda.com/en-gb/pta/chat/api/conversations/{cid}/messages"
    body = {
        "type": "Message",
        "content": {"text": "Find me 3 hotels in Tokyo for Dec 9-11 2026, 2 guests. Show me the hotel names and links."},
        "context": {"pageContext": {"hostPageTypeName": "Unknown", "hostPageTypeId": -1}},
        "chatType": "Common",
    }
    headers = {"content-type": "application/json", "accept": "text/event-stream,application/json, text/plain, */*"}

    out_path = RECON / "hotels_raw.bin"
    events = []
    with client.stream("POST", send_url, json=body, headers=headers) as r:
        print("status:", r.status_code)
        with open(out_path, "wb") as f:
            for chunk in r.iter_bytes():
                if not chunk:
                    break
                f.write(chunk)
    print(f"raw bytes: {out_path.stat().st_size}")

    # parse
    raw = out_path.read_bytes().decode("utf-8", "replace")
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            events.append(json.loads(payload))
        except json.JSONDecodeError:
            pass

    print(f"\n=== {len(events)} events ===")
    for i, e in enumerate(events):
        role = e.get("role")
        etype = e.get("type")
        isf = e.get("isFinal")
        content = e.get("content") or {}
        ctx = e.get("context") or {}
        txt = content.get("text") or ""
        has_widgets = bool(isinstance(ctx, dict) and ctx.get("widgets"))
        # look for any URL/link anywhere in the event
        blob = json.dumps(e)
        has_url = "http" in blob or "Link" in blob or "link" in blob or "agoda.com" in blob
        print(f"[{i}] role={role} type={etype} isFinal={isf} ctx_widgets={has_widgets} has_url={has_url} txtlen={len(txt)}")
        if has_url or has_widgets or isf:
            print("    FULL:", json.dumps(e)[:1500])
    client.close()


if __name__ == "__main__":
    main()
