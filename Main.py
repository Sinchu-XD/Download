from pyrogram import Client, filters
from pyrogram.types import Message
from playwright.async_api import async_playwright

from pyrogram.enums import ChatMembersFilter
from Message import get_random_message
from Helper import extract_media_urls
import yt_dlp
import os
from asyncio import sleep
from typing import Dict
import re
import asyncio
import logging
from Terabox import get_terabox_video_url


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = 6067591
API_HASH = "94e17044c2393f43fda31d3afe77b26b"
BOT_TOKEN = "7902638287:AAGyCNE-ndYeZ8t9n2G8P0ATzJp5eJi0uhY"

app = Client("social_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

COOKIE_FILE = "ig_cookies.json"

tag_processes: Dict[int, bool] = {}
SOCIAL_URL_PATTERN = r"(https?:\/\/[^\s]+)"
TERABOX_URL_PATTERN = r"(https?:\/\/(?:www\.)?teraboxlink\.com\/[\w\/]+)"

async def is_admin(client, chat_id, user_id):
    member = await client.get_chat_member(chat_id, user_id)
    return member.status in ("administrator", "creator")


async def download_media(message: Message, url: str):
    msg = await message.reply("🔍 Fetching media, please wait...")

    try:
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'quiet': True,
            'cookiefile': "cookies/cookies.txt",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        await message.reply_video(file_path, caption=f"📥 Downloaded from:\n{url}")
        await msg.delete()
        os.remove(file_path)

    except Exception as e:
        await msg.edit(f"❌ Failed: `{str(e)}`")

@app.on_message(filters.group & filters.private & filters.regex(SOCIAL_URL_PATTERN))
async def handle_download(_, message: Message):
    url = re.findall(SOCIAL_URL_PATTERN, message.text)[0]
    await download_media(message, url)

@app.on_message(filters.private & filters.regex(TERABOX_URL_PATTERN))
async def handle_message(client, message):
    url = message.text.strip()

    if not url.startswith("http"):
        await message.reply("❌ Please send a valid TeraBox link.")
        return

    msg = await message.reply("🔍 Extracting video download link...")

    try:
        logger.info(f"Extracting video link for: {url}")
        video_url, filename = await get_terabox_video_url(url)

        # Debugging: Check if the returned values are strings
        if not isinstance(video_url, str) or not isinstance(filename, str):
            logger.error(f"Invalid return values: video_url={video_url}, filename={filename}")
            await msg.edit_text(f"❌ Failed: Invalid URL or filename.")
            return

        await msg.edit_text(f"📥 Downloading `{filename}` ...")

        # Ensure valid file path before download
        file_path = await download_file(video_url, filename)
        
        if not isinstance(file_path, str) or not os.path.exists(file_path):
            logger.error(f"Failed to download file. Invalid file path: {file_path}")
            await msg.edit_text(f"❌ Failed to download file.")
            return

        await msg.edit_text("📤 Uploading to Telegram...")

        await message.reply_video(video=file_path, caption=f"🎬 `{filename}`")
        os.remove(file_path)

    except Exception as e:
        logger.error(f"Error during TeraBox download: {str(e)}")
        await msg.edit_text(f"❌ Failed: {str(e)}")

"""
#@app.on_message(filters.group & filters.regex(r"^(https?://(www\.)?instagram\.com/.+)$"))
async def insta_link_handler(client, message):
    url = message.text.strip()
    await message.reply("Processing your Instagram link...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        import json
        with open(COOKIE_FILE, "r") as f:
            cookies = json.load(f)
        pw_cookies = []
        for c in cookies:
            pw_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c["domain"],
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", True),
                "sameSite": c.get("sameSite", "Lax").capitalize() if c.get("sameSite") else "Lax",
            })
        await context.add_cookies(pw_cookies)
        page = await context.new_page()
        try:
            await page.goto(url, timeout=15000)
            media_urls = await extract_media_urls(page)
            if not media_urls:
                await message.reply("Sorry, couldn't extract media from the provided link.")
                await browser.close()
                return
            files = []
            for idx, media_url in enumerate(media_urls):
                ext = ".mp4" if ".mp4" in media_url else ".jpg"
                filename = f"media_{idx}{ext}"
                async with aiohttp.ClientSession() as session:
                    async with session.get(media_url) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(filename, "wb") as f:
                                f.write(content)
                            files.append(filename)
            await browser.close()
            for file in files:
                if file.endswith(".mp4"):
                    await message.reply_video(file)
                else:
                    await message.reply_photo(file)
                os.remove(file)
        except Exception as e:
            await message.reply(f"An error occurred: {e}")
            await browser.close()

"""
@app.on_message(filters.command("tagall") & filters.group)
async def tag_all(_, message: Message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    admins = []
    async for admin in app.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
        admins.append(admin.user.id)

    if message.from_user.id not in admins:
        return await message.reply("🚫 Only admins can use /tagall")

    if tag_processes.get(chat_id):
        return await message.reply("⚠️ Tagging is already in progress. Use /cancel to stop.")

    tag_processes[chat_id] = True
    await message.reply("🔄 Tagging started. Sending tags one by one...")

    async for member in app.get_chat_members(chat_id):
        if not tag_processes.get(chat_id):
            await message.reply("❌ Tagging cancelled.")
            return

        user = member.user
        
        if user.is_bot or user.is_deleted:
            continue

        mention = f"@{user.username}" if user.username else f"[{user.first_name}](tg://user?id={user.id})"
        tag_line = f"{get_random_message()}\n{mention}"

        try:
            await app.send_message(chat_id, tag_line, disable_web_page_preview=True)
            await sleep(1.5)
        except Exception:
            continue

    await message.reply("✅ Finished tagging everyone.")
    tag_processes[chat_id] = False

@app.on_message(filters.command("cancel") & filters.group)
async def cancel_tag(_, message: Message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    admins = []
    async for admin in app.get_chat_members(chat_id, filter=ChatMembersFilter.ADMINISTRATORS):
        admins.append(admin.user.id)

    if message.from_user.id not in admins:
        return await message.reply("🚫 Only admins can use /cancel")

    if tag_processes.get(chat_id):
        tag_processes[chat_id] = False
        await message.reply("🛑 Tagging has been cancelled.")
    else:
        await message.reply("ℹ️ No tagging process is currently running.")


@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("I'm Live")

if __name__ == "__main__":
    app.run()
    logger.info("Stopping Bot! Goodbye")
    
