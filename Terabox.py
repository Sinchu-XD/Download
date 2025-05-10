# terabox.py

import asyncio
import aiohttp
import os
from playwright.async_api import async_playwright

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

async def get_terabox_video_url(share_link: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(share_link, timeout=60000)

        await page.wait_for_selector("video", timeout=15000)
        video_element = await page.query_selector("video")

        if not video_element:
            await browser.close()
            raise Exception("No video element found")

        video_url = await video_element.get_attribute("src")

        filename = share_link.split("/")[-1][:8] + ".mp4"
        await browser.close()

        return video_url, filename


async def download_file(url: str, filename: str) -> str:
    path = f"downloads/{filename}"
    os.makedirs("downloads", exist_ok=True)

    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Download failed: HTTP {resp.status}")

            with open(path, "wb") as f:
                while True:
                    chunk = await resp.content.read(1024 * 1024)  # 1MB
                    if not chunk:
                        break
                    f.write(chunk)

    return path
