"""
Playwright Web Data Extraction and Dashboard Inspection Tool.
Enables headless browser interaction, DOM table scraping, and visual snapshotting.
"""

from __future__ import annotations
import asyncio
import io
import logging
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class PlaywrightWebExtractor:
    """Headless browser data extraction and visual verification engine."""

    @staticmethod
    async def extract_tabular_data(
        url: str,
        table_selector: str = "table",
        wait_ms: int = 3000,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Navigate to a webpage, wait for DOM rendering, and extract HTML tables into structured datasets.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {
                "status": "ERROR",
                "error": "Playwright is not installed. Please install playwright and run 'playwright install chromium'."
            }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(wait_ms)

                tables = await page.locator(table_selector).all()
                if not tables:
                    # Fallback to general tables
                    tables = await page.locator("table").all()

                if not tables:
                    await browser.close()
                    return {
                        "status": "NO_TABLES_FOUND",
                        "url": url,
                        "tables_found": 0,
                        "message": f"No tabular data found with selector '{table_selector}'."
                    }

                extracted_data: List[Dict[str, Any]] = []
                for idx, tbl in enumerate(tables[:3]):  # limit to first 3 tables
                    html_content = await tbl.evaluate("el => el.outerHTML")
                    try:
                        dfs = pd.read_html(io.StringIO(html_content))
                        if dfs:
                            df = dfs[0]
                            extracted_data.append({
                                "table_index": idx + 1,
                                "row_count": len(df),
                                "column_count": len(df.columns),
                                "columns": [str(c) for c in df.columns],
                                "sample_records": df.head(50).to_dict(orient="records")
                            })
                    except Exception as parse_err:
                        logger.warning(f"Failed parsing table {idx}: {parse_err}")

                page_title = await page.title()
                await browser.close()

                return {
                    "status": "SUCCESS",
                    "url": url,
                    "page_title": page_title,
                    "tables_extracted": len(extracted_data),
                    "tables": extracted_data
                }

            except Exception as e:
                await browser.close()
                return {
                    "status": "ERROR",
                    "url": url,
                    "error": str(e)
                }

    @staticmethod
    async def capture_snapshot(
        url: str,
        wait_ms: int = 2000,
        full_page: bool = False
    ) -> Dict[str, Any]:
        """
        Capture a screenshot of a dashboard or web application for visual analysis.
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {"status": "ERROR", "error": "Playwright is not installed."}

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 1920, "height": 1080})
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(wait_ms)
                screenshot_bytes = await page.screenshot(full_page=full_page)
                page_title = await page.title()
                await browser.close()

                return {
                    "status": "SUCCESS",
                    "url": url,
                    "page_title": page_title,
                    "screenshot_bytes_length": len(screenshot_bytes),
                    "bytes": screenshot_bytes
                }
            except Exception as e:
                await browser.close()
                return {"status": "ERROR", "url": url, "error": str(e)}


def run_extract_tables(url: str, table_selector: str = "table") -> Dict[str, Any]:
    """Synchronous helper to run the async Playwright extraction."""
    return asyncio.run(PlaywrightWebExtractor.extract_tabular_data(url, table_selector))


def run_capture_snapshot(url: str) -> Dict[str, Any]:
    """Synchronous helper to run the async Playwright snapshot."""
    return asyncio.run(PlaywrightWebExtractor.capture_snapshot(url))
