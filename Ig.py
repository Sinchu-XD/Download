import json
import requests
import re
import os

# Load cookies from cookies.json file
def load_cookies(path="ig_cookies.json"):
    with open(path, "r") as file:
        raw = json.load(file)
        return {cookie["name"]: cookie["value"] for cookie in raw}

# Extract shortcode from URL
def extract_shortcode(url):
    match = re.search(r"instagram\.com/(?:reel|p|tv)/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else None

# Download file
def download_file(url, filename):
    print(f"Downloading: {url}")
    r = requests.get(url, stream=True)
    if r.status_code == 200:
        with open(filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Saved as: {filename}")
    else:
        print("Failed to download video")

# Main function
def download_instagram_video(url, cookies_path="ig_cookies.json"):
    shortcode = extract_shortcode(url)
    if not shortcode:
        print("Invalid Instagram URL.")
        return

    api_url = f"https://www.instagram.com/api/v1/media/{shortcode}/info/"
    cookies = load_cookies(cookies_path)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }

    response = requests.get(api_url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        print("Failed to fetch media info. Status:", response.status_code)
        print("Response:", response.text)
        return

    try:
        data = response.json()
        media = data["items"][0]

        if media.get("media_type") == 2:  # video
            video_url = media["video_versions"][0]["url"]
            download_file(video_url, f"{shortcode}.mp4")
        elif media.get("media_type") == 1:  # photo
            image_url = media["image_versions2"]["candidates"][0]["url"]
            download_file(image_url, f"{shortcode}.jpg")
        elif media.get("media_type") == 8:  # carousel
            for i, item in enumerate(media["carousel_media"]):
                if item["media_type"] == 2:
                    media_url = item["video_versions"][0]["url"]
                    ext = "mp4"
                else:
                    media_url = item["image_versions2"]["candidates"][0]["url"]
                    ext = "jpg"
                download_file(media_url, f"{shortcode}_{i}.{ext}")
        else:
            print("Unsupported media type.")

    except Exception as e:
        print("Error parsing response:", str(e))

# Example usage
if __name__ == "__main__":
    reel_url = "https://www.instagram.com/reel/DDn3HANoBd0/"
    download_instagram_video(reel_url)
