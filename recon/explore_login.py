"""M0 recon: explore the Agoda login flow.

Navigates to the PTA chat page (forces login), captures redirects,
page HTML, screenshot, and network requests so we can find login
selectors and endpoints. Run headed so the user can observe.
"""
from __future__ import annotations

import json
import pathlib
import re

from playwright.sync_api import sync_playwright

RECON = pathlib.Path(__file__).resolve().parent
SECRETS = RECON.parent / "secrets"
SECRETS.mkdir(exist_ok=True)

TARGET = "https://www.agoda.com/en-gb/pta/chat"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36"
)


def main() -> None:
    requests_log: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(user_agent=UA, locale="en-GB")
        page = context.new_page()

        def on_response(resp):
            requests_log.append(
                {
                    "method": resp.request.method,
                    "url": resp.url,
                    "status": resp.status,
                    "ctype": resp.headers.get("content-type", ""),
                }
            )

        page.on("response", on_response)

        print(f"Navigating to {TARGET} ...")
        page.goto(TARGET, wait_until="domcontentloaded", timeout=60000)
        # give redirects/JS time to settle
        page.wait_for_timeout(6000)

        final_url = page.url
        print(f"Final URL: {final_url}")

        page.screenshot(path=str(RECON / "landing.png"), full_page=False)
        (RECON / "landing.html").write_text(page.content(), encoding="utf-8")
        print(f"Saved HTML ({len((RECON / 'landing.html').read_text())} chars) and screenshot.")

        # Try to locate likely login form fields
        html = (RECON / "landing.html").read_text(encoding="utf-8")
        emails = re.findall(r'(?:type="email"|name="[^"]*email[^"]*"|id="[^"]*email[^"]*")', html, re.I)
        passwords = re.findall(r'type="password"', html, re.I)
        buttons = re.findall(r'<button[^>]*>(.*?)</button>', html, re.S | re.I)
        print(f"Email-ish fields: {len(emails)}  Password fields: {len(passwords)}")
        print(f"Buttons: {[b.strip()[:40] for b in buttons[:10]]}")

        # Save network log (filter to agoda + auth-ish calls)
        (RECON / "network.json").write_text(json.dumps(requests_log, indent=2), encoding="utf-8")
        authish = [
            r for r in requests_log
            if re.search(r"(login|signin|sign-in|auth|account|otp|verify|password|token)", r["url"], re.I)
        ]
        print(f"\nAuth-ish network calls ({len(authish)}):")
        for r in authish[:40]:
            print(f"  [{r['status']}] {r['method']} {r['url'][:140]}")

        page.wait_for_timeout(2000)
        browser.close()


if __name__ == "__main__":
    main()
