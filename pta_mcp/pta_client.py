"""Agoda PTA Chat API client.

Creates a conversation and sends a message, buffering the SSE
stream into a single text response. Auth is via cookies exported
from a logged-in browser session (see secrets/cookies.txt).
"""
from __future__ import annotations

import json
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any

import httpx

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)
CREATE_URL = "https://www.agoda.com/en-gb/pta/chat/api/conversations"
SEND_URL_TMPL = "https://www.agoda.com/en-gb/pta/chat/api/conversations/{cid}/messages"


@dataclass
class PtaResponse:
    text: str
    message_id: int | None = None
    parent_message_id: int | None = None
    widgets: list[dict[str, Any]] = field(default_factory=list)
    raw_events: int = 0


def _is_final_agent_message(evt: dict[str, Any]) -> bool:
    """The completed assistant reply is one event, not the streamed chunks."""
    return (
        evt.get("role") == "Agent"
        and str(evt.get("type") or "").lower() == "message"
        and bool(evt.get("isFinal"))
    )


def collect_response(events: list[dict[str, Any]]) -> PtaResponse:
    """Build a reply from the SSE stream.

    When an Agent message with isFinal=true is present, that event is the
    full message: its text and content.widgetData replace streamed chunks
    and earlier widget events.
    """
    accumulated: list[str] = []
    fallback_widgets: list[dict[str, Any]] = []
    final_evt: dict[str, Any] | None = None
    message_id: int | None = None
    parent_id: int | None = None

    for evt in events:
        role = evt.get("role")
        etype = str(evt.get("type") or "")
        content = evt.get("content") if isinstance(evt.get("content"), dict) else {}
        chunk = content.get("text") or ""

        if role == "Receipt" and parent_id is None:
            parent_id = evt.get("parentMessageId")

        if _is_final_agent_message(evt):
            final_evt = evt
            message_id = evt.get("id")
            continue

        if role == "Agent" and etype.lower() == "message":
            if chunk:
                accumulated.append(chunk)
            continue

        if role == "Agent" and etype and etype.lower() != "message":
            fallback_widgets.append(evt)

    if final_evt is not None:
        content = final_evt.get("content") if isinstance(final_evt.get("content"), dict) else {}
        text_out = content.get("text") or ""
        widget_data = content.get("widgetData")
        widgets = widget_data if isinstance(widget_data, list) else fallback_widgets
        message_id = final_evt.get("id") or message_id
    else:
        text_out = "".join(accumulated)
        widgets = fallback_widgets

    return PtaResponse(
        text=text_out,
        message_id=message_id,
        parent_message_id=parent_id,
        widgets=widgets,
        raw_events=len(events),
    )


class PtaClient:
    """Thin client over the PTA Chat HTTP API."""

    def __init__(self, cookie_file: str | pathlib.Path, timeout: float = 120.0) -> None:
        self._cookie_file = pathlib.Path(cookie_file)
        self._cookies = self._load_cookies()
        self._client = httpx.Client(
            headers={
                "user-agent": UA,
                "accept": "application/json, text/plain, */*",
                "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
                "origin": "https://www.agoda.com",
                "referer": "https://www.agoda.com/pta/chat",
                "cookie": self._cookies,
            },
            timeout=timeout,
        )

    def _load_cookies(self) -> str:
        # Prefer cookies from env (lets hosted deployments store them as a
        # secret without a file on disk).
        env_cookie = os.environ.get("PTA_COOKIE")
        if env_cookie and env_cookie.strip():
            return env_cookie.strip()
        if not self._cookie_file.exists():
            raise FileNotFoundError(
                f"Cookie file not found: {self._cookie_file}. "
                "Export cookies from a logged-in browser session, or set the "
                "PTA_COOKIE environment variable to the cookie header value."
            )
        return self._cookie_file.read_text(encoding="utf-8").strip()

    def reload_cookies(self) -> None:
        self._cookies = self._load_cookies()
        self._client.headers["cookie"] = self._cookies

    def create_conversation(self, title: str = "Trip plan") -> int:
        body = {"title": title, "conversationContext": {"chatType": "Common"}}
        r = self._client.post(
            CREATE_URL,
            json=body,
            headers={"content-type": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
        cid = data.get("id")
        if cid is None:
            raise RuntimeError(f"No conversation id in response: {r.text[:300]}")
        return int(cid)

    def send_message(self, conversation_id: int, text: str) -> PtaResponse:
        url = SEND_URL_TMPL.format(cid=conversation_id)
        body = {
            "type": "Message",
            "content": {"text": text},
            "context": {"pageContext": {"hostPageTypeName": "Unknown", "hostPageTypeId": -1}},
            "chatType": "Common",
        }
        headers = {
            "content-type": "application/json",
            "accept": "text/event-stream,application/json, text/plain, */*",
        }

        events: list[dict[str, Any]] = []

        with self._client.stream("POST", url, json=body, headers=headers) as r:
            if r.status_code != 200:
                body_text = r.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"send_message failed ({r.status_code}): {body_text[:500]}")
            for line in r.iter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[len("data:"):].strip()
                if not payload:
                    continue
                try:
                    evt = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if isinstance(evt, dict):
                    events.append(evt)

        return collect_response(events)

    def plan_trip(self, message: str, title: str = "Trip plan") -> PtaResponse:
        """Convenience: create conversation + send one message + return buffered reply."""
        cid = self.create_conversation(title=title)
        return self.send_message(cid, message)

    def close(self) -> None:
        self._client.close()
