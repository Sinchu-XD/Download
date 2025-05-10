from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ChatMembersFilter
from Message import get_random_message
import yt_dlp
import os
from asyncio import sleep
from typing import Dict
import re
import asyncio
import logging
from Terabox import get_terabox_video_url, download_file


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_ID = 6067591
API_HASH = "94e17044c2393f43fda31d3afe77b26b"
BOT_TOKEN = "7902638287:AAGyCNE-ndYeZ8t9n2G8P0ATzJp5eJi0uhY"

app = Client("social_downloader_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

@app.on_message(filters.group & filters.regex(SOCIAL_URL_PATTERN))
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
        await msg.edit_text(f"📥 Downloading `{filename}` ...")

        file_path = await download_file(video_url, filename)
        await msg.edit_text("📤 Uploading to Telegram...")

        await message.reply_video(video=file_path, caption=f"🎬 `{filename}`")
        os.remove(file_path)

    except Exception as e:
        logger.error(f"Error during TeraBox download: {str(e)}")
        await msg.edit_text(f"❌ Failed: {str(e)}")


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
    
