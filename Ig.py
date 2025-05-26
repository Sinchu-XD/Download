import os
import re
import json
import requests
from urllib.parse import urlparse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from playwright.async_api import async_playwright

API_ID = 6067591
API_HASH = "94e17044c2393f43fda31d3afe77b26b"
BOT_TOKEN = "7902638287:AAGyCNE-ndYeZ8t9n2G8P0ATzJp5eJi0uhY"

COOKIE_PATH = "ig_cookies.json"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

INSTAGRAM_REGEX = re.compile(
    r"(https?://)?(www\.)?instagram\.com/[\w\-/\?=]+", re.IGNORECASE
)


def load_cookies():
    with open(COOKIE_PATH, "r") as f:
        cookies = json.load(f)
    for cookie in cookies:
        same_site = cookie.get("sameSite")
        if same_site:
            normalized = same_site.capitalize()
            if normalized not in ["Strict", "Lax", "None"]:
                normalized = "Lax"
            cookie["sameSite"] = normalized
        else:
            cookie["sameSite"] = "Lax"
    return cookies


async def login_with_cookies(context, cookies):
    await context.add_cookies(cookies)


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def download_file(url, filename):
    r = requests.get(url, stream=True)
    full_path = os.path.join(DOWNLOAD_DIR, filename)
    with open(full_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
    return full_path


def get_instagram_type(url: str) -> str:
    if "/reel/" in url:
        return "reel"
    elif "/p/" in url or "/tv/" in url:
        return "post"
    else:
        return "profile"


app = Client("ig_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply("Hello! Send me an Instagram URL and I'll fetch info or media with buttons to choose what to download.")


@app.on_message(filters.regex(INSTAGRAM_REGEX))
async def on_instagram_url(client, message):
    insta_url = re.search(INSTAGRAM_REGEX, message.text).group(0)
    if not insta_url.startswith("http"):
        await message.reply("❌ Please send a valid Instagram URL.")
        return

    await message.reply("⏳ Processing your request... Please wait.")

    # Use async playwright properly
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()

        # Load cookies if available and add them to context
        cookies = load_cookies()
        await login_with_cookies(context, cookies)

        page = await context.new_page()

        ig_type = get_instagram_type(insta_url)
        parsed = urlparse(insta_url)
        username = parsed.path.strip("/").split("/")[-1]

        # Load page accordingly
        if ig_type == "profile":
            await page.goto(f"https://www.instagram.com/{username}/")
            await page.wait_for_timeout(4000)
        else:
            await page.goto(insta_url)
            await page.wait_for_timeout(4000)

        # Prepare buttons depending on type
        buttons = []

        if ig_type in ("reel", "post"):
            buttons.append(
                [InlineKeyboardButton("▶️ Download Reel/Post", callback_data=f"download_reel|{insta_url}")]
            )

        buttons.append(
            [InlineKeyboardButton("🖼️ Profile Pic", callback_data=f"profile_pic|{username}")]
        )
        buttons.append(
            [InlineKeyboardButton("📊 Account Details", callback_data=f"account_details|{username}")]
        )

        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(
            f"Choose what you want to download from Instagram URL:\n\n{insta_url}", reply_markup=reply_markup
        )

        await browser.close()


async def download_reel_or_post(page, url):
    await page.goto(url, timeout=60000)
    await page.wait_for_timeout(5000)

    video_element = await page.query_selector("video")
    if video_element:
        video_url = await video_element.get_attribute("src")
        if video_url:
            filename = sanitize_filename(url.split("/")[-2]) + ".mp4"
            path = download_file(video_url, filename)
            return path
    return None


async def get_profile_info(page, username: str) -> str:
    # Wait for page content to load fully
    await page.wait_for_timeout(5000)

    content = await page.content()

    # Extract JSON data embedded in the page (window._sharedData)
    json_data_match = re.search(r'window\._sharedData = (.*?);</script>', content)

    if not json_data_match:
        return "❌ Could not parse profile data."

    try:
        data = json.loads(json_data_match.group(1))
        user_data = data['entry_data']['ProfilePage'][0]['graphql']['user']

        bio_text = user_data.get('biography', 'N/A')
        posts = user_data['edge_owner_to_timeline_media']['count']
        followers = user_data['edge_followed_by']['count']
        following = user_data['edge_follow']['count']

        info_text = (
            f"👤 Username: {username}\n"
            f"📝 Bio: {bio_text or 'N/A'}\n"
            f"📷 Posts: {posts}\n"
            f"👥 Followers: {followers}\n"
            f"➡️ Following: {following}"
        )
        return info_text
    except Exception as e:
        return f"❌ Error parsing profile info: {e}"


@app.on_callback_query()
async def button_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    await callback_query.answer()  # Always answer callback queries

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        cookies = load_cookies()
        await context.add_cookies(cookies)
        page = await context.new_page()

        try:
            if data.startswith("download_reel|"):
                url = data.split("|")[1]
                await callback_query.message.reply("⏳ Downloading reel/post...")
                path = await download_reel_or_post(page, url)
                if path:
                    await client.send_video(callback_query.message.chat.id, video=path)
                else:
                    await callback_query.message.reply("❌ Failed to download reel/post.")

            elif data.startswith("profile_pic|"):
                username = data.split("|")[1]
                await callback_query.message.reply("⏳ Fetching profile picture...")
                await page.goto(f"https://www.instagram.com/{username}/")
                await page.wait_for_timeout(4000)
                pic_url = await get_profile_pic_url(page, username)
                if pic_url:
                    path = download_file(pic_url, f"{username}_profile_pic.jpg")
                    await client.send_photo(callback_query.message.chat.id, photo=path)
                else:
                    await callback_query.message.reply("❌ Could not fetch profile picture.")

            elif data.startswith("account_details|"):
                username = data.split("|")[1]
                await callback_query.message.reply("⏳ Fetching account details...")
                await page.goto(f"https://www.instagram.com/{username}/")
                await page.wait_for_timeout(4000)
                info = await get_profile_info(page, username)
                await callback_query.message.reply(info)
            else:
                await callback_query.answer("Unknown action.", show_alert=True)
        except Exception as e:
            await callback_query.message.reply(f"❌ Error: {e}")
        finally:
            await browser.close()


if __name__ == "__main__":
    print("Bot is running...")
    app.run()
    
