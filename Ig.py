import json
import requests
from bs4 import BeautifulSoup

# Load cookies from JSON file
def load_cookies(filename):
    with open(filename, 'r') as f:
        cookies_list = json.load(f)
    cookies = {cookie['name']: cookie['value'] for cookie in cookies_list}
    return cookies

# Download video from Instagram post
def download_instagram_video(post_url, cookies_file='ig_cookies.json'):
    cookies = load_cookies(cookies_file)
    headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    # Fetch the post page
    response = requests.get(post_url, cookies=cookies, headers=headers)
    if response.status_code != 200:
        print("Failed to fetch post. Check cookies or URL.")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    scripts = soup.find_all('script', type='application/ld+json')

    for script in scripts:
        try:
            data = json.loads(script.string)
            if 'video' in data:
                video_url = data['video']
                print(f"Downloading: {video_url}")
                video_data = requests.get(video_url).content
                with open('instagram_video.mp4', 'wb') as f:
                    f.write(video_data)
                print("Download complete: instagram_video.mp4")
                return
        except:
            continue

    print("Video URL not found.")

# Example usage
download_instagram_video("https://www.instagram.com/reel/DDn3HANoBd0/?igsh=cjF1MTVzZHdod2M4")
