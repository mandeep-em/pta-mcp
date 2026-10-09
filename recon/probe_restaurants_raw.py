"""Inspect raw restaurant widget data from the PTA API.

Captures the raw SSE stream (not collect_response) so we can see every event
type, the final message content (incl. widgetData), and every field of each
restaurant card — to find URL/link fields that _extract_cards drops.
"""
import json
import pathlib
from collections import Counter

import httpx
from pta_mcp.pta_client import UA, CREATE_URL, SEND_URL_TMPL

COOKIE = pathlib.Path("/Users/mdahiya/pta_mcp/secrets/cookies.txt").read_text().strip()


def find_urls(obj, path=""):
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if isinstance(v, str) and ("http" in v or "link" in k.lower() or "url" in k.lower() or "nav" in k.lower()):
                hits.append((p, v[:140]))
            hits.extend(find_urls(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(find_urls(v, f"{path}[{i}]"))
    return hits


def main():
    client = httpx.Client(headers={
        "user-agent": UA, "accept": "application/json, text/plain, */*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8", "origin": "https://www.agoda.com",
        "referer": "https://www.agoda.com/pta/chat", "cookie": COOKIE,
    }, timeout=httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0))

    r = client.post(CREATE_URL, json={"title": "restaurant probe",
                       "conversationContext": {"chatType": "Common"}},
                    headers={"content-type": "application/json"})
    r.raise_for_status()
    cid = r.json()["id"]
    print(f"conversation: {cid}")

    url = SEND_URL_TMPL.format(cid=cid)
    body = {"type": "Message",
            "content": {"text": "Recommend restaurants in Tokyo near Shinjuku and Shibuya for dinner. Show names, cuisine and links."},
            "context": {"pageContext": {"hostPageTypeName": "Unknown", "hostPageTypeId": -1}},
            "chatType": "Common"}
    headers = {"content-type": "application/json",
               "accept": "text/event-stream,application/json, text/plain, */*"}

    events = []
    with client.stream("POST", url, json=body, headers=headers) as resp:
        for line in resp.iter_lines():
            if not line or not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                pass

    print(f"total events: {len(events)}")
    hist = Counter((e.get("role"), e.get("type"), bool(e.get("isFinal"))) for e in events)
    print("event histogram (role, type, isFinal):")
    for k, n in hist.most_common():
        print(f"  {n:4d}  {k}")

    # final event
    finals = [e for e in events if e.get("role") == "Agent" and str(e.get("type") or "").lower() == "message" and e.get("isFinal")]
    print(f"\nfinal messages: {len(finals)}")
    for f in finals:
        c = f.get("content") or {}
        print("  final content keys:", list(c.keys()) if isinstance(c, dict) else type(c).__name__)
        wd = c.get("widgetData")
        print(f"  final content.widgetData present: {isinstance(wd, list)} (len={len(wd) if isinstance(wd,list) else 0})")

    # gather all widgets: separate WidgetData events + final content.widgetData
    widgets = [e for e in events if e.get("role") == "Agent" and str(e.get("type") or "").lower() != "message"]
    for f in finals:
        c = f.get("content") or {}
        wd = c.get("widgetData")
        if isinstance(wd, list):
            widgets.extend(wd)
    print(f"\nwidget events/entries total: {len(widgets)}")

    card_idx = 0
    for w in widgets:
        content = w.get("content") if isinstance(w.get("content"), dict) else {}
        props = content.get("renderprops") if isinstance(content, dict) else None
        if not isinstance(props, dict):
            continue
        for key, val in props.items():
            if not isinstance(val, list):
                continue
            for item in val:
                if not isinstance(item, dict):
                    continue
                d = item.get("data") if isinstance(item.get("data"), dict) else item
                card_idx += 1
                print("\n" + "=" * 70)
                print(f"CARD {card_idx} (key={key!r}) title={d.get('title') or d.get('name')}")
                print("=" * 70)
                print("ALL FIELDS:")
                for k, v in d.items():
                    s = json.dumps(v) if not isinstance(v, str) else v
                    print(f"  {k}: {s[:160]}")
                urls = find_urls(item)
                print("URL/LINK-LIKE FIELDS:")
                if urls:
                    for p, v in urls:
                        print(f"  {p} = {v}")
                else:
                    print("  (none)")
    client.close()


if __name__ == "__main__":
    main()
