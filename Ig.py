import json
import os
import re
import asyncio
import aiohttp
from urllib.parse import urlparse

from pyrogram import Client, filters
from pyrogram.types import Message

from playwright.async_api import async_playwright

API_ID = "YOUR_API_ID"
API_HASH = "YOUR_API_HASH"
BOT_TOKEN = "YOUR_BOT_TOKEN"

RAW_COOKIE_PATH = "ig_cookies.json"
COOKIE_PATH = "playwright_cookies.json"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

bot = Client("IGScraperBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def sanitize_and_save_cookies(input_path, output_path):
    with open(input_path, "r") as f:
        raw_cookies = json.load(f)

    valid_same_sites = {"Lax", "Strict", "None"}
    converted_cookies = []

    for cookie in raw_cookies:
        new_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"].lstrip("."),
            "path": cookie.get("path", "/"),
            "secure": cookie.get("secure", True),
            "httpOnly": cookie.get("httpOnly", False),
            "sameSite": "Lax",  # fallback
        }

        ss = cookie.get("sameSite", "").capitalize()
        if ss in valid_same_sites:
            new_cookie["sameSite"] = ss

        if "expirationDate" in cookie and not cookie.get("session", False):
            new_cookie["expires"] = int(cookie["expirationDate"])

        converted_cookies.append(new_cookie)

    with open(output_path, "w") as f:
        json.dump(converted_cookies, f, indent=4)


def get_instagram_type(url: str) -> str:
    if "/reel/" in url:
        return "reel"
    elif "/p/" in url or "/tv/" in url:
        return "post"
    else:
        return "profile"


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


async def download_file(url, filename):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as r:
            if r.status == 200:
                path = os.path.join(DOWNLOAD_DIR, filename)
                with open(path, "wb") as f:
                    f.write(await r.read())
                return path
    return None


@bot.on_message(filters.command("start") & filters.private)
async def start_handler(_, message: Message):
    await message.reply("👋 Send me any public Instagram post, reel, or profile link to download.")


@bot.on_message(filters.private & filters.text)
async def handle_instagram_url(_, message: Message):
    url = message.text.strip()
    if not url.startswith("http") or "instagram.com" not in url:
        return await message.reply("❌ Invalid Instagram URL.")

    await message.reply("🔍 Processing...")

    try:
        sanitize_and_save_cookies(RAW_COOKIE_PATH, COOKIE_PATH)
        cookies = json.load(open(COOKIE_PATH))

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            await context.add_cookies(cookies)
            page = await context.new_page()

            ig_type = get_instagram_type(url)

            if ig_type in ["reel", "post"]:
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(5000)
                try:
                    await page.wait_for_selector("video", timeout=10000)
                    video_element = await page.query_selector("video")
                    video_url = await video_element.get_attribute("src")

                    filename = sanitize_filename(url.split("/")[-2]) + ".mp4"
                    file_path = await download_file(video_url, filename)
                    if file_path:
                        await message.reply_video(file_path)
                    else:
                        await message.reply("❌ Failed to download video.")
                except:
                    image_elements = await page.query_selector_all("img")
                    if not image_elements:
                        return await message.reply("❌ No media found.")
                    for idx, img in enumerate(image_elements[:3]):
                        img_url = await img.get_attribute("src")
                        filename = sanitize_filename(f"{url.split('/')[-2]}_{idx}.jpg")
                        file_path = await download_file(img_url, filename)
                        if file_path:
                            await message.reply_photo(file_path)
            elif ig_type == "profile":
                parsed = urlparse(url)
                username = parsed.path.strip("/").split("/")[-1]
                profile_url = f"https://www.instagram.com/{username}/"

                await page.goto(profile_url)
                await page.wait_for_timeout(5000)

                profile_pic_url = None
                pic_elem = await page.query_selector("img[data-testid='user-avatar']")
                if not pic_elem:
                    imgs = await page.query_selector_all("img")
                    for img in imgs:
                        alt = await img.get_attribute("alt")
                        if alt and username.lower() in alt.lower():
                            pic_elem = img
                            break
                if pic_elem:
                    profile_pic_url = await pic_elem.get_attribute("src")
                    pic_path = await download_file(profile_pic_url, f"{username}_profile.jpg")
                    if pic_path:
                        await message.reply_photo(pic_path)

                bio_elem = await page.query_selector("div.-vDIg span")
                bio = await bio_elem.inner_text() if bio_elem else "N/A"

                stats = await page.query_selector_all("ul li span span")
                posts = await stats[0].inner_text() if len(stats) > 0 else "N/A"
                followers = await stats[1].get_attribute("title") if len(stats) > 1 else "N/A"
                following = await stats[2].inner_text() if len(stats) > 2 else "N/A"

                info_text = (
                    f"👤 **Username:** {username}\n"
                    f"📝 **Bio:** {bio}\n"
                    f"📸 **Posts:** {posts}\n"
                    f"👥 **Followers:** {followers}\n"
                    f"🔄 **Following:** {following}"
                )
                await message.reply(info_text)
            else:
                await message.reply("❌ Unsupported Instagram link.")
            await browser.close()
    except Exception as e:
        await message.reply(f"⚠️ Error: {e}")


if __name__ == "__main__":
    print("Bot started...")
    bot.run()
    
