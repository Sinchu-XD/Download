import aiohttp
from bs4 import BeautifulSoup
import re
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


async def get_terabox_video_url(share_link: str):
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(share_link, timeout=60) as response:
            if response.status != 200:
                raise Exception(f"Failed to load page: HTTP {response.status}")

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Try to find file name
            filename_tag = soup.find("meta", {"name": "description"})
            filename = filename_tag["content"][:20] + ".mp4" if filename_tag else "video.mp4"

            # Try to find video URL in JS variables
            match = re.search(r'"video_url":"(https:[^"]+)"', html)
            if not match:
                raise Exception("❌ Video URL not found in page content")

            video_url = match.group(1).replace("\\u002F", "/")

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
