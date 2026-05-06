"""Search YouTube for the top candidates for a given query.

Uses Playwright (headless Chromium) to scrape the public YouTube search page
metadata: title, channel, duration, thumbnail, URL. No video downloading
happens here — this module only inspects publicly visible metadata so that
the user can verify which result is the right one.
"""
from __future__ import annotations

import asyncio
import re
import urllib.parse
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError


@dataclass
class CandidateData:
    title: str
    channel: str
    url: str
    duration: Optional[str]
    thumbnail_url: Optional[str]

    def to_dict(self) -> dict:
        return asdict(self)


YOUTUBE_SEARCH_URL = "https://www.youtube.com/results?search_query={query}"


async def _accept_consent_if_present(page) -> None:
    """YouTube sometimes shows a consent wall in EU/regions. Best-effort accept."""
    try:
        # The consent button text varies by language; try a few selectors.
        for selector in [
            'button[aria-label*="Accept"]',
            'button:has-text("Accept all")',
            'button:has-text("I agree")',
            'tp-yt-paper-button[aria-label*="Accept"]',
        ]:
            btn = await page.query_selector(selector)
            if btn:
                await btn.click()
                await page.wait_for_timeout(800)
                return
    except Exception:
        pass


async def _scrape_search_results(query: str, max_results: int, screenshot_path: Path | None) -> list[CandidateData]:
    url = YOUTUBE_SEARCH_URL.format(query=urllib.parse.quote_plus(query))

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await _accept_consent_if_present(page)

            # Wait for either the video renderer or a "no results" message
            try:
                await page.wait_for_selector("ytd-video-renderer", timeout=15000)
            except PWTimeoutError:
                if screenshot_path:
                    try:
                        await page.screenshot(path=str(screenshot_path), full_page=True)
                    except Exception:
                        pass
                return []

            # Pull the data we need with a single page.evaluate call.
            results = await page.evaluate(
                """(maxResults) => {
                    const out = [];
                    const items = document.querySelectorAll('ytd-video-renderer');
                    for (const item of items) {
                        if (out.length >= maxResults) break;

                        const titleEl = item.querySelector('a#video-title');
                        const title = titleEl ? (titleEl.getAttribute('title') || titleEl.textContent || '').trim() : '';
                        const href = titleEl ? titleEl.getAttribute('href') : '';
                        if (!title || !href) continue;
                        // Skip shorts and channel/playlist links — only watch URLs.
                        if (!href.startsWith('/watch?v=')) continue;

                        const channelEl = item.querySelector(
                            'ytd-channel-name a, #channel-name a, ytd-channel-name yt-formatted-string'
                        );
                        const channel = channelEl ? channelEl.textContent.trim() : '';

                        // Duration overlay — YouTube changes this element regularly,
                        // so try several selectors AND fall back to a regex over all
                        // text spans in the thumbnail area.
                        let duration = '';
                        const durSelectors = [
                            'ytd-thumbnail-overlay-time-status-renderer #text',
                            'ytd-thumbnail-overlay-time-status-renderer span',
                            '#text.ytd-thumbnail-overlay-time-status-renderer',
                            '.badge-shape-wiz__text',
                            'div.yt-thumbnail-view-model__overlay-badge',
                            'span.ytd-thumbnail-overlay-time-status-renderer',
                        ];
                        for (const sel of durSelectors) {
                            const el = item.querySelector(sel);
                            if (el && el.textContent.trim()) {
                                duration = el.textContent.trim();
                                break;
                            }
                        }
                        if (!duration) {
                            const thumb = item.querySelector('ytd-thumbnail, a#thumbnail');
                            if (thumb) {
                                const re = /\b\d{1,2}:\d{2}(?::\d{2})?\b/;
                                const allText = thumb.textContent || '';
                                const m = allText.match(re);
                                if (m) duration = m[0];
                            }
                        }

                        // Thumbnail
                        let thumb = '';
                        const img = item.querySelector('img');
                        if (img) thumb = img.getAttribute('src') || '';

                        out.push({
                            title,
                            channel,
                            url: 'https://www.youtube.com' + href,
                            duration,
                            thumbnail_url: thumb,
                        });
                    }
                    return out;
                }""",
                max_results,
            )

            return [
                CandidateData(
                    title=r.get("title", ""),
                    channel=r.get("channel", ""),
                    url=r.get("url", ""),
                    duration=r.get("duration") or None,
                    thumbnail_url=r.get("thumbnail_url") or None,
                )
                for r in results
            ]
        except Exception:
            if screenshot_path:
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                except Exception:
                    pass
            raise
        finally:
            await context.close()
            await browser.close()


def search_youtube(
    query: str,
    max_results: int = 5,
    screenshots_dir: Path | None = None,
) -> list[CandidateData]:
    """Synchronous wrapper around the async Playwright scrape.

    Returns up to ``max_results`` candidates (may be empty).
    """
    safe_query = re.sub(r"[^A-Za-z0-9_]+", "_", query)[:60] or "query"
    screenshot_path = None
    if screenshots_dir is not None:
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        screenshot_path = screenshots_dir / f"search_fail_{safe_query}_{ts}.png"

    return asyncio.run(_scrape_search_results(query, max_results, screenshot_path))
