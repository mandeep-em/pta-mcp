"""MCP server exposing Agoda PTA Chat as a trip-planning tool.

Run locally:
    uv run python -m pta_mcp.server
or with the MCP inspector:
    uv run mcp dev pta_mcp.server:mcp
"""
from __future__ import annotations

import json
import logging
import os
import pathlib
import re
from typing import Any

logging.getLogger("httpx").setLevel(logging.WARNING)

from mcp.server.mcpserver import MCPServer

from pta_mcp.pta_client import PtaClient, PtaResponse

ROOT = pathlib.Path(__file__).resolve().parent.parent
COOKIE_FILE = pathlib.Path(os.environ.get("PTA_COOKIE_FILE", ROOT / "secrets" / "cookies.txt"))

mcp = MCPServer("pta-chat")

_client: PtaClient | None = None


def _get_client() -> PtaClient:
    global _client
    if _client is None:
        _client = PtaClient(COOKIE_FILE)
    return _client


def _extract_cards(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pull clean card summaries out of WidgetData events.

    Handles accommodations (hotels), data (POI/activities), and
    flights lists, which use different field names.
    """
    cards: list[dict[str, Any]] = []
    for w in widgets:
        if w.get("type") != "WidgetData":
            continue
        props = (w.get("content") or {}).get("renderprops") or {}
        # candidate list-valued keys holding card arrays
        list_keys = [k for k, v in props.items() if isinstance(v, list)]
        for key in list_keys:
            for item in props[key]:
                if not isinstance(item, dict):
                    continue
                d = item.get("data") if isinstance(item.get("data"), dict) else item
                reviews = d.get("reviews") or {}
                pricing = d.get("pricing") or {}
                address = d.get("address") or {}
                kind = item.get("type") or (
                    {"accommodations": "Hotel", "flights": "Flight"}.get(key, key)
                )
                cards.append(
                    {
                        "kind": kind,
                        "title": d.get("title") or d.get("hotelName") or d.get("name"),
                        "reason": item.get("reason") or d.get("reason"),
                        "rating": d.get("rating"),
                        "review_score": reviews.get("score"),
                        "review_count": reviews.get("count") or d.get("review_count"),
                        "price": pricing.get("displayPrice") or pricing.get("price") or d.get("price"),
                        "city": address.get("city") or d.get("localityName"),
                        "area": address.get("area"),
                        "id": d.get("id") or d.get("propertyId") or d.get("placeId"),
                        "link": d.get("propertyLink"),
                    }
                )
    return cards


def _format_response(resp: PtaResponse) -> str:
    parts: list[str] = []
    text = resp.text or ""
    # strip frontend micro-frontend placeholders (<mfe>...</mfe>)
    text = re.sub(r"<mfe>.*?</mfe>", "", text, flags=re.S).strip()
    if text:
        parts.append(text)
    cards = _extract_cards(resp.widgets)
    if cards:
        parts.append("\n\n--- Recommended items ---")
        for i, c in enumerate(cards, 1):
            bits = [f"{i}. {c.get('title') or 'Untitled'}"]
            if c.get("kind"):
                bits.append(f"[{c['kind']}]")
            if c.get("rating"):
                bits.append(f"★ {c['rating']}")
            if c.get("review_score"):
                bits.append(f"· {c['review_score']}/10" + (f" ({c['review_count']} reviews)" if c.get("review_count") else ""))
            if c.get("price"):
                bits.append(f"· {c['price']}")
            if c.get("city"):
                bits.append(f"· {c['city']}" + (f", {c['area']}" if c.get("area") else ""))
            if c.get("reason"):
                bits.append(f"— {c['reason']}")
            if c.get("link"):
                link = c["link"]
                if link.startswith("/"):
                    link = "https://www.agoda.com" + link
                bits.append(f"→ {link}")
            parts.append(" ".join(bits))
    if not parts:
        parts.append("(no response text received)")
    return "\n".join(parts)


@mcp.tool()
def plan_trip(message: str, objective: str = "itinerary") -> str:
    """Plan a trip using Agoda's Personal Travel Assistant.

    Send a free-text travel request. The assistant can search hotels,
    flights, things to do, places to visit, and build itineraries.

    Args:
        message: The travel request in natural language, e.g.
            "Plan a 5-day trip to Bali in December, find hotels and activities."
        objective: Hint for the request type: "hotels" | "flights" |
            "activities" | "places" | "itinerary" (default "itinerary").

    Returns:
        The assistant's reply text, plus any widget/card data it produced.
    """
    client = _get_client()
    title = f"MCP: {objective}"[:80]
    resp = client.plan_trip(message, title=title)
    return _format_response(resp)


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        host = os.environ.get("HOST", "0.0.0.0")
        port = int(os.environ.get("PORT", "8000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
