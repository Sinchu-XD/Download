from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os
import re
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = 6067591
API_HASH = "94e17044c2393f43fda31d3afe77b26b"
BOT_TOKEN = "7902638287:AAGyCNE-ndYeZ8t9n2G8P0ATzJp5eJi0uhY"

app = Client("social_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

SOCIAL_URL_PATTERN = r"(https?:\/\/[^\s]+)"

async def download_media(message: Message, url: str):
    msg = await message.reply("🔍 Fetching media, please wait...")

    try:
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'bestvideo+bestaudio/best',
            'quiet': True,
            'cookiefile': "cookies/cookies.txt",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        await message.reply_document(file_path, caption=f"📥 Downloaded from:\n{url}")
        await msg.delete()
        os.remove(file_path)

    except Exception as e:
        await msg.edit(f"❌ Failed: `{str(e)}`")

@app.on_message(filters.group & filters.regex(SOCIAL_URL_PATTERN))
async def handle_download(_, message: Message):
    url = re.findall(SOCIAL_URL_PATTERN, message.text)[0]
    await download_media(message, url)

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text("I'm Live")

if __name__ == "__main__":
    app.run()
    logger.info("Stopping Bot! GoodBye")
