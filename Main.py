from pyrogram import Client, filters
from pyrogram.types import Message
import yt_dlp
import os
import re

API_ID = 6067591
API_HASH = "94e17044c2393f43fda31d3afe77b26b"
BOT_TOKEN = "7875353720:AAG_Hg3W6P5vvR7WP1PzELqS-9exTLLQ3MU"

app = Client("social_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

SOCIAL_URL_PATTERN = r"(https?:\/\/[^\s]+)"

async def download_media(message: Message, url: str):
    msg = await message.reply("🔍 Fetching media, please wait...")

    try:
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'bestvideo+bestaudio/best',
            'quiet': True,
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

app.run()
