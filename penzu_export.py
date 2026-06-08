"""
penzu_export.py
---------------
Python rewrite of mirontoli's penzu-export.js
Original: https://gist.github.com/mirontoli/a3dd9d9618477f1ddc5311c509bb8bab

Why rewritten:
- The original depends on axios (npm), which was compromised in March 2026.
- Python + Playwright avoids the npm supply chain risk entirely.
- Easier to run as a one-off script without a Node.js project setup.

Requirements:
    pip install playwright
    playwright install chromium  # only needed if you don't use --connect-over-cdp

Usage:
    1. Start Chrome with remote debugging:
         Windows:  Start-Process Chrome -ArgumentList '--remote-debugging-port=9222'
         Mac:      /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
         Linux:    google-chrome --remote-debugging-port=9222

    2. Log in to Penzu in that Chrome window.

    3. Navigate to your most recent journal entry. The URL will look like:
         https://penzu.com/journals/{journalId}/{mostRecentPostId}
       Note those two IDs and update the config below.

    4. Run:
         python penzu_export.py

    Output: posts.json in the same directory.
"""

import asyncio
import json
import random
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

# ─── CONFIG — update these three values ───────────────────────────────────────
JOURNAL_ID = "0000000"           # from the URL: penzu.com/journals/{JOURNAL_ID}/...
MOST_RECENT_POST_ID = "00000000" # from the URL: penzu.com/journals/.../{MOST_RECENT_POST_ID}
OUTPUT_FILE = "posts.json"

# Minimum delay between page navigations in seconds.
# Do NOT go below 10 to avoid HTTP 429 rate limiting.
MIN_DELAY_SECONDS = 10
MAX_EXTRA_DELAY_SECONDS = 5
# ──────────────────────────────────────────────────────────────────────────────


def get_ws_endpoint(cdp_url: str = "http://127.0.0.1:9222/json/version") -> str:
    """Fetch the WebSocket debugger URL from the running Chrome instance."""
    with urllib.request.urlopen(cdp_url) as response:
        data = json.loads(response.read())
    ws_url = data.get("webSocketDebuggerUrl")
    if not ws_url:
        raise RuntimeError(
            "Could not find webSocketDebuggerUrl. "
            "Make sure Chrome is running with --remote-debugging-port=9222 "
            "and that you are logged in to Penzu."
        )
    print(f"Connected to Chrome: {ws_url}")
    return ws_url


async def export_journal():
    posts = []
    processed_ids = set()
    output_path = Path(OUTPUT_FILE)

    # Clear output file if it already exists
    if output_path.exists():
        output_path.unlink()

    ws_url = get_ws_endpoint()

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(ws_url)
        context = browser.contexts[0]
        page = await context.new_page()

        # We use a Future to drive the crawl from inside the response handler
        next_post_id: asyncio.Future = asyncio.get_event_loop().create_future()

        async def handle_response(response):
            url = response.url
            entries_prefix = f"https://penzu.com/api/journals/{JOURNAL_ID}/entries/"

            if not url.startswith(entries_prefix) or url.endswith("/photos"):
                return

            try:
                body = await response.json()
            except Exception:
                return

            entry = body.get("entry")
            history = body.get("previous", [])

            if not entry:
                print("WARNING: Response had no entry field.")
                return

            post_id = entry.get("id")
            print(f"[{len(posts) + 1}] Captured entry id: {post_id}  |  {entry.get('created_at', '')[:10]}  |  {entry.get('title') or '(no title)'}")

            post = {
                "id": post_id,
                "created_at": entry.get("created_at"),
                "title": entry.get("title"),
                "plaintext": entry.get("plaintext_body"),
                "tags": [t["name"] for t in entry.get("tags", [])],
            }
            posts.append(post)
            processed_ids.add(post_id)

            # Find the next unprocessed previous entry
            next_id = None
            for item in history:
                candidate = item.get("entry", {})
                if candidate.get("id") not in processed_ids:
                    next_id = candidate.get("id")
                    break

            if next_id:
                if not next_post_id.done():
                    next_post_id.set_result(next_id)
            else:
                print("No more previous entries found. Export complete.")
                if not next_post_id.done():
                    next_post_id.set_result(None)

        page.on("response", handle_response)

        start_url = f"https://penzu.com/journals/{JOURNAL_ID}/{MOST_RECENT_POST_ID}"
        print(f"Navigating to most recent post: {start_url}")
        await page.goto(start_url)

        # Walk backwards through all entries
        current_id = MOST_RECENT_POST_ID
        while True:
            # Wait for the response handler to signal the next ID
            loop = asyncio.get_event_loop()
            next_post_id = loop.create_future()

            # Give the page time to fire the response event
            await asyncio.sleep(2)

            try:
                next_id = await asyncio.wait_for(next_post_id, timeout=30)
            except asyncio.TimeoutError:
                print("Timed out waiting for next entry. Stopping.")
                break

            if next_id is None:
                break

            delay = MIN_DELAY_SECONDS + random.uniform(0, MAX_EXTRA_DELAY_SECONDS)
            print(f"Waiting {delay:.1f}s before next request...")
            await asyncio.sleep(delay)

            next_url = f"https://penzu.com/journals/{JOURNAL_ID}/{next_id}"
            await page.goto(next_url)
            current_id = next_id

        await browser.close()

    # Write all posts to JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(posts)} entries saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(export_journal())
