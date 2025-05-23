import os
import re
import aiohttp
from pyrogram import Client, filters
from playwright.async_api import async_playwright


async def extract_media_urls(page):
    content = await page.content()
    import json
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, "html.parser")
        script = soup.find("script", type="application/ld+json")
        if script:
            data = json.loads(script.string)
            if "video" in data:
                return [data["video"]["contentUrl"]]
            elif "image" in data:
                if isinstance(data["image"], list):
                    return data["image"]
                else:
                    return [data["image"]]
    except Exception:
        pass
    try:
        shared_data_match = re.search(r'window\._sharedData = (.*?);</script>', content)
        if shared_data_match:
            shared_data = json.loads(shared_data_match.group(1))
            media_urls = []
            post = shared_data["entry_data"]["PostPage"][0]["graphql"]["shortcode_media"]
            if post.get("is_video"):
                media_urls.append(post["video_url"])
            else:
                if "edge_sidecar_to_children" in post:
                    for edge in post["edge_sidecar_to_children"]["edges"]:
                        node = edge["node"]
                        if node.get("is_video"):
                            media_urls.append(node["video_url"])
                        else:
                            media_urls.append(node["display_url"])
                else:
                    media_urls.append(post["display_url"])
            return media_urls
    except Exception:
        pass
    return []
