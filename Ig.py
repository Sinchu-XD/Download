import os
import re
import json
import requests
from urllib.parse import urlparse
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from playwright.sync_api import sync_playwright

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
    return cookies


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


def login_with_cookies(context, cookies):
    context.add_cookies(cookies)


def download_reel_or_post(page, url):
    page.goto(url, timeout=60000)
    page.wait_for_timeout(5000)

    video_element = page.query_selector("video")
    if video_element:
        video_url = video_element.get_attribute("src")
        if video_url:
            filename = sanitize_filename(url.split("/")[-2]) + ".mp4"
            path = download_file(video_url, filename)
            return path
    return None


def get_profile_pic_url(page, username):
    profile_pic_element = page.query_selector("img[data-testid='user-avatar']")
    if not profile_pic_element:
        imgs = page.query_selector_all("img")
        for img in imgs:
            alt = img.get_attribute("alt")
            if alt and username.lower() in alt.lower():
                profile_pic_element = img
                break
    if profile_pic_element:
        return profile_pic_element.get_attribute("src")
    return None


def get_profile_info(page, username):
    bio_element = page.query_selector("div.-vDIg span")
    bio_text = bio_element.inner_text() if bio_element else "N/A"

    stats = page.query_selector_all("ul li span span")
    posts = stats[0].inner_text() if len(stats) > 0 else "N/A"
    followers = stats[1].get_attribute("title") if len(stats) > 1 else "N/A"
    following = stats[2].inner_text() if len(stats) > 2 else "N/A"

    info_text = (
        f"👤 Username: {username}\n"
        f"📝 Bio: {bio_text}\n"
        f"📷 Posts: {posts}\n"
        f"👥 Followers: {followers}\n"
        f"➡️ Following: {following}"
    )
    return info_text


app = Client("ig_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


@app.on_message(filters.command("start"))
def start(_, message):
    message.reply("Hello! Send me an Instagram URL and I'll fetch info or media with buttons to choose what to download.")


@app.on_message(filters.regex(INSTAGRAM_REGEX))
def on_instagram_url(client, message):
    insta_url = re.search(INSTAGRAM_REGEX, message.text).group(0)
    if not insta_url.startswith("http"):
        message.reply("❌ Please send a valid Instagram URL.")
        return

    message.reply("⏳ Processing your request... Please wait.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = load_cookies()
        login_with_cookies(context, cookies)
        page = context.new_page()

        ig_type = get_instagram_type(insta_url)
        parsed = urlparse(insta_url)
        username = parsed.path.strip("/").split("/")[-1]

        # Load page for profile or reel/post accordingly
        if ig_type == "profile":
            page.goto(f"https://www.instagram.com/{username}/")
            page.wait_for_timeout(4000)
        else:
            page.goto(insta_url)
            page.wait_for_timeout(4000)

        # Prepare buttons depending on type
        buttons = []

        if ig_type in ("reel", "post"):
            buttons.append(
                [InlineKeyboardButton("▶️ Download Reel/Post", callback_data=f"download_reel|{insta_url}")]
            )

        if ig_type == "profile" or ig_type in ("reel", "post"):
            buttons.append(
                [InlineKeyboardButton("🖼️ Profile Pic", callback_data=f"profile_pic|{username}")]
            )
            buttons.append(
                [InlineKeyboardButton("📊 Account Details", callback_data=f"account_details|{username}")]
            )

        reply_markup = InlineKeyboardMarkup(buttons)
        message.reply(f"Choose what you want to download from Instagram URL:\n\n{insta_url}", reply_markup=reply_markup)
        browser.close()


@app.on_callback_query()
def button_handler(client: Client, callback_query: CallbackQuery):
    data = callback_query.data
    client = callback_query._client  # pyrogram client instance

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = load_cookies()
        login_with_cookies(context, cookies)
        page = context.new_page()

        try:
            if data.startswith("download_reel|"):
                url = data.split("|")[1]
                callback_query.answer("Downloading reel/post...")
                path = download_reel_or_post(page, url)
                if path:
                    client.send_video(callback_query.message.chat.id, video=path)
                else:
                    callback_query.message.reply("❌ Failed to download reel/post.")
            elif data.startswith("profile_pic|"):
                username = data.split("|")[1]
                callback_query.answer("Fetching profile picture...")
                page.goto(f"https://www.instagram.com/{username}/")
                page.wait_for_timeout(4000)
                pic_url = get_profile_pic_url(page, username)
                if pic_url:
                    path = download_file(pic_url, f"{username}_profile_pic.jpg")
                    client.send_photo(callback_query.message.chat.id, photo=path)
                else:
                    callback_query.message.reply("❌ Could not fetch profile picture.")
            elif data.startswith("account_details|"):
                username = data.split("|")[1]
                callback_query.answer("Fetching account details...")
                page.goto(f"https://www.instagram.com/{username}/")
                page.wait_for_timeout(4000)
                info = get_profile_info(page, username)
                callback_query.message.reply(info)
            else:
                callback_query.answer("Unknown action.")
        except Exception as e:
            callback_query.message.reply(f"❌ Error: {e}")
        finally:
            browser.close()


if __name__ == "__main__":
    print("Bot is running...")
    app.run()
    
