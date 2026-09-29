import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        user_data_dir = "/root/tv_bot/browser_data"
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--remote-debugging-port=9222",
                "--remote-debugging-address=0.0.0.0"
            ]
        )

        page = context.pages[0] if context.pages else await context.new_page()
        print("[*] Navigating to chart layout...")
        await page.goto("https://www.tradingview.com/chart/pLLGFSTR/", wait_until="domcontentloaded")
        
        print("[+] Target chart loaded. Keeping alive with CDP on port 9222...")
        while True:
            await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(run())
