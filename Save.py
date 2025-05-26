import asyncio
from playwright.async_api import async_playwright

async def save_login():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # interactive
        context = await browser.new_context()
        page = await context.new_page()

        await page.goto("https://www.instagram.com", timeout=60000)
        print("Log in manually in the opened browser window...")

        await page.wait_for_timeout(60000)  # give you time to log in manually
        await context.storage_state(path="auth.json")
        print("Login saved to auth.json")

        await browser.close()

asyncio.run(save_login())
