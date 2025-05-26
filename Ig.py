import json
import os
import re
import time
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright


COOKIE_PATH = "ig_cookies.json"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


def load_cookies():
    with open(COOKIE_PATH, "r") as f:
        cookies = json.load(f)
    return cookies


def get_instagram_type(url: str) -> str:
    if "/reel/" in url:
        return "reel"
    elif "/p/" in url or "/tv/" in url:
        return "post"
    else:
        return "profile"


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


def login_with_cookies(context, cookies):
    context.add_cookies(cookies)


def download_reel_or_post(page, url, ig_type):
    print(f"Fetching {ig_type} from: {url}")
    page.goto(url, timeout=60000)
    page.wait_for_timeout(5000)

    try:
        page.wait_for_selector("video", timeout=10000)
        video_element = page.query_selector("video")
        video_url = video_element.get_attribute("src")

        filename = sanitize_filename(url.split("/")[-2]) + ".mp4"
        download_file(video_url, filename)
        print(f"✅ {ig_type.capitalize()} downloaded: {filename}")
    except:
        print("❌ Failed to fetch video. Trying image fallback...")

        image_elements = page.query_selector_all("img")
        for idx, img in enumerate(image_elements):
            img_url = img.get_attribute("src")
            filename = sanitize_filename(f"{url.split('/')[-2]}_{idx}.jpg")
            download_file(img_url, filename)
        print("✅ Image(s) downloaded")


def download_profile(page, url):
    username = url.strip("/").split("/")[-1]
    profile_url = f"https://www.instagram.com/{username}/"

    print(f"Fetching profile: {profile_url}")
    page.goto(profile_url)
    page.wait_for_timeout(5000)

    try:
        profile_pic_url = page.query_selector("img")  # First image is usually profile pic
        profile_pic_url = profile_pic_url.get_attribute("src")
        download_file(profile_pic_url, f"{username}_profile_pic.jpg")

        bio_element = page.query_selector("div.-vDIg span")
        bio_text = bio_element.inner_text() if bio_element else "N/A"

        stats = page.query_selector_all("ul li span span")
        posts = stats[0].inner_text() if len(stats) > 0 else "N/A"
        followers = stats[1].get_attribute("title") if len(stats) > 1 else "N/A"
        following = stats[2].inner_text() if len(stats) > 2 else "N/A"

        with open(os.path.join(DOWNLOAD_DIR, f"{username}_profile_info.txt"), "w") as f:
            f.write(f"Username: {username}\n")
            f.write(f"Bio: {bio_text}\n")
            f.write(f"Posts: {posts}\n")
            f.write(f"Followers: {followers}\n")
            f.write(f"Following: {following}\n")

        print("✅ Profile data downloaded.")
    except Exception as e:
        print("❌ Failed to download profile info:", e)


def download_file(url, filename):
    import requests
    r = requests.get(url, stream=True)
    full_path = os.path.join(DOWNLOAD_DIR, filename)
    with open(full_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)


def main(insta_url: str):
    insta_type = get_instagram_type(insta_url)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        cookies = load_cookies()
        login_with_cookies(context, cookies)

        page = context.new_page()

        if insta_type == "reel" or insta_type == "post":
            download_reel_or_post(page, insta_url, insta_type)
        elif insta_type == "profile":
            download_profile(page, insta_url)
        else:
            print("❌ Unknown Instagram link type.")

        browser.close()


if __name__ == "__main__":
    insta_url = input("🔗 Enter Instagram URL: ").strip()
    main(insta_url)
