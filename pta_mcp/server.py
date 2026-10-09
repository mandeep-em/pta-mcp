"""MCP server exposing Agoda PTA Chat as a trip-planning tool.

Run locally:
    uv run python -m pta_mcp.server
or with the MCP inspector:
    uv run mcp dev pta_mcp.server:mcp
"""
from __future__ import annotations

import asyncio
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


def _full_url(link: str) -> str:
    """Turn a relative Agoda path into an absolute URL."""
    link = link.strip()
    if not link:
        return link
    if link.startswith(("http://", "https://")):
        return link
    if link.startswith("//"):
        return "https:" + link
    if link.startswith("www."):
        return "https://" + link
    if not link.startswith("/"):
        link = "/" + link
    return "https://www.agoda.com" + link


def _renderprops(widget: dict[str, Any]) -> dict[str, Any] | None:
    """Widget cards arrive either as WidgetData events or embedded on the final message."""
    if widget.get("type") not in (None, "WidgetData"):
        return None
    content = widget.get("content")
    if not isinstance(content, dict):
        return None
    props = content.get("renderprops")
    return props if isinstance(props, dict) else None


def _price_label(pricing: Any, data: dict[str, Any]) -> str | None:
    if not isinstance(pricing, dict):
        pricing = {}
    display = pricing.get("displayPrice") or pricing.get("price") or data.get("price")
    if display:
        currency = pricing.get("currency")
        text = str(display)
        if currency and currency not in text:
            return f"{text} {currency}"
        return text
    after = pricing.get("priceAfterDiscount")
    if isinstance(after, dict) and after.get("amount"):
        amount = str(after["amount"])
        currency = str(after.get("currency") or "")
        if after.get("currencySymbolLocation") == "end":
            return f"{amount}{currency}"
        return f"{currency}{amount}" if currency else amount
    return None


def _flight_bits(data: dict[str, Any]) -> tuple[str | None, str | None]:
    """Airline, route, and schedule from a flight widget item."""
    slices = data.get("slices")
    if not isinstance(slices, list) or not slices or not isinstance(slices[0], dict):
        return None, None
    slice0 = slices[0]
    segments = slice0.get("segments") if isinstance(slice0.get("segments"), list) else []
    first = segments[0] if segments and isinstance(segments[0], dict) else {}
    last = segments[-1] if segments and isinstance(segments[-1], dict) else first
    origin = first.get("origin") if isinstance(first.get("origin"), dict) else {}
    dest = last.get("destination") if isinstance(last.get("destination"), dict) else {}
    carrier = first.get("marketingCarrierName") or origin.get("carrierName")
    number = first.get("flightNumber")
    route = None
    if origin.get("airportCode") and dest.get("airportCode"):
        route = f"{origin['airportCode']} → {dest['airportCode']}"
    title = " ".join(part for part in (carrier, number, route) if part) or None
    when = f"{origin['time']}–{dest['time']}" if origin.get("time") and dest.get("time") else None
    stops = slice0.get("stops")
    stop_label = "nonstop" if stops == 0 else (f"{stops} stops" if stops else None)
    detail = " · ".join(
        str(part) for part in (slice0.get("departureDate"), when, slice0.get("duration"), stop_label) if part
    )
    return title, detail or None


def _card_reason(item: dict[str, Any], data: dict[str, Any]) -> str | None:
    reason = item.get("reason") or data.get("reason") or data.get("reasons")
    if isinstance(reason, list):
        reason = "; ".join(str(part) for part in reason if part)
    return str(reason) if reason else None


def _extract_cards(widgets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pull clean card summaries out of WidgetData events.

    Handles accommodations (hotels), data (POI/activities), and
    flights lists, which use different field names.
    """
    cards: list[dict[str, Any]] = []
    for w in widgets:
        props = _renderprops(w)
        if props is None:
            continue
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
                flight_title, flight_detail = _flight_bits(d)
                cards.append(
                    {
                        "kind": kind,
                        "title": d.get("title") or d.get("hotelName") or d.get("name") or flight_title,
                        "reason": _card_reason(item, d),
                        "rating": d.get("rating"),
                        "review_score": reviews.get("score"),
                        "review_count": reviews.get("count") or d.get("review_count"),
                        "price": _price_label(pricing, d),
                        "detail": flight_detail,
                        "city": address.get("city") or d.get("localityName"),
                        "area": address.get("area"),
                        "id": d.get("id") or d.get("propertyId") or d.get("placeId") or d.get("flightId"),
                        "link": _full_url(
                            d.get("propertyLink") or d.get("navUrl") or d.get("bookingUrl") or ""
                        )
                        or None,
                    }
                )
    return cards


def _format_card(index: int, card: dict[str, Any]) -> str:
    bits = [f"{index}. {card.get('title') or 'Untitled'}"]
    if card.get("kind"):
        bits.append(f"[{card['kind']}]")
    if card.get("rating"):
        bits.append(f"★ {card['rating']}")
    if card.get("review_score"):
        review = f"· {card['review_score']}/10"
        if card.get("review_count"):
            review += f" ({card['review_count']} reviews)"
        bits.append(review)
    if card.get("price"):
        bits.append(f"· {card['price']}")
    if card.get("detail"):
        bits.append(f"· {card['detail']}")
    if card.get("city"):
        bits.append(f"· {card['city']}" + (f", {card['area']}" if card.get("area") else ""))
    if card.get("reason"):
        bits.append(f"— {card['reason']}")
    line = " ".join(bits)
    if card.get("link"):
        line += f"\n   → {card['link']}"
    return line


def _format_widget(widget: dict[str, Any]) -> str:
    cards = _extract_cards([widget])
    return "\n".join(_format_card(i, card) for i, card in enumerate(cards, 1))


def _mfe_id(raw: str) -> str | None:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(payload, dict) and payload.get("id"):
        return str(payload["id"])
    return None


def _format_response(resp: PtaResponse) -> str:
    """Keep the assistant markdown and replace each <mfe> tag with its widget.

    The final message is markdown, then the widget for that placeholder, then
    more markdown, and so on.
    """
    text = resp.text or ""
    widgets = [w for w in resp.widgets if _renderprops(w)]
    by_id: dict[str, dict[str, Any]] = {}
    for widget in widgets:
        content = widget.get("content") if isinstance(widget.get("content"), dict) else {}
        widget_id = content.get("id")
        if widget_id:
            by_id[str(widget_id)] = widget

    parts: list[str] = []
    unused = list(widgets)
    cursor = 0
    for match in re.finditer(r"<mfe>(.*?)</mfe>", text, flags=re.S):
        before = text[cursor:match.start()].strip()
        if before:
            parts.append(before)
        widget_id = _mfe_id(match.group(1))
        widget = by_id.get(widget_id) if widget_id else None
        if widget is None and unused:
            widget = unused[0]
        if widget is not None:
            if widget in unused:
                unused.remove(widget)
            block = _format_widget(widget)
            if block:
                parts.append(block)
        cursor = match.end()

    tail = text[cursor:].strip()
    if tail:
        parts.append(tail)
    for widget in unused:
        block = _format_widget(widget)
        if block:
            parts.append(block)
    if not parts:
        parts.append("(no response text received)")
    return "\n\n".join(parts)


def _plan_trip(message: str, objective: str) -> str:
    """Run one search on its own HTTP connection.

    A shared client breaks when a caller times out and retries while the
    first Agoda stream is still open.
    """
    client = PtaClient(COOKIE_FILE)
    try:
        title = f"MCP: {objective}"[:80]
        resp = client.plan_trip(message, title=title)
        return _format_response(resp)
    finally:
        client.close()


@mcp.tool()
async def plan_trip(message: str, objective: str = "itinerary") -> str:
    """Plan a trip using Agoda's Personal Travel Assistant.

    Send a free-text travel request. The assistant can search hotels,
    flights, things to do, places to visit, and build itineraries.

    A search often takes 30-90 seconds. Wait at least 120 seconds for this
    tool. This server does not stop the search at 45 seconds.

    Args:
        message: The travel request in natural language, e.g.
            "Plan a 5-day trip to Bali in December, find hotels and activities."
        objective: Hint for the request type: "hotels" | "flights" |
            "activities" | "places" | "itinerary" (default "itinerary").

    Returns:
        The assistant's reply text, plus any widget/card data it produced.
    """
    return await asyncio.to_thread(_plan_trip, message, objective)


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
