import aiohttp
import os
import asyncio

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

async def download_file(url: str, filename: str, max_retries: int = 3) -> str:
    path = f"downloads/{filename}"
    os.makedirs("downloads", exist_ok=True)

    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession(headers=HEADERS) as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=180)) as resp:
                    if resp.status != 200:
                        raise Exception(f"❌ HTTP {resp.status}")

                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    last_percent = 0

                    with open(path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1024 * 1024):  # 1MB
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total > 0:
                                percent = int((downloaded / total) * 100)
                                if percent - last_percent >= 10:
                                    print(f"⬇️ Downloaded {percent}%...")
                                    last_percent = percent

            return path

        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            else:
                raise Exception(f"❌ Download failed after {max_retries} attempts: {e}")

from playwright.async_api import async_playwright
import asyncio

async def get_terabox_video_url(share_link: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        await page.goto(share_link, timeout=60000)
        await page.wait_for_load_state("networkidle")

        # Wait and retry for the video element
        try:
            await page.wait_for_selector("video", timeout=15000)
        except:
            await browser.close()
            raise Exception("❌ Video element not found on TeraBox page.")

        # Try to get video src via JS in case <video src=""> is empty
        video_url = await page.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video ? video.src || video.getAttribute('src') : null;
            }
        """)

        if not video_url:
            await browser.close()
            raise Exception("❌ Unable to extract video URL.")

        filename = share_link.split("/")[-1][:8] + ".mp4"
        await browser.close()

        return video_url, filename
        
