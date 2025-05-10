import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By

def get_terabox_video_url(share_link: str):
    options = uc.ChromeOptions()
    options.add_argument("--headless")  # Remove this if you want to see the browser
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,800")

    browser = uc.Chrome(options=options)
    browser.get(share_link)

    try:
        # Wait up to 15 seconds for video to load
        for _ in range(30):
            video_elements = browser.find_elements(By.TAG_NAME, "video")
            if video_elements:
                break
            time.sleep(0.5)

        if not video_elements:
            browser.quit()
            raise Exception("❌ Video element not found on page.")

        video_url = video_elements[0].get_attribute("src")
        if not video_url:
            browser.quit()
            raise Exception("❌ Video URL not found in element.")

        filename = share_link.split("/")[-1][:8] + ".mp4"
        browser.quit()
        return video_url, filename

    except Exception as e:
        browser.quit()
        raise Exception(f"❌ Failed: {str(e)}")

if __name__ == "__main__":
    link = "https://teraboxlink.com/s/1_BkRld5NS41YeIA2GD29Qw"
    try:
        video_url, filename = get_terabox_video_url(link)
        print("✅ Video URL:", video_url)
        print("📄 Filename:", filename)
    except Exception as e:
        print(str(e))
        
