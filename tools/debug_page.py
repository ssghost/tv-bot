import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/root/tv_bot/browser_data",
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=["--no-sandbox", "--disable-setuid-sandbox"]
        )
        page = browser.pages[0] if browser.pages else await browser.new_page()
        print("[*] Navigating to https://www.tradingview.com/ ...")
        await page.goto("https://www.tradingview.com/", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        print("[*] Page title:", await page.title())
        print("[*] Current URL:", page.url)

        buttons = await page.eval_on_selector_all(
            "button, a",
            "els => els.map(e => ({tag: e.tagName, text: e.innerText.trim(), aria: e.getAttribute('aria-label')})).filter(e => e.text || e.aria)"
        )
        print("[*] Top buttons/links found:")
        for b in buttons[:20]:
            print("   ", b)

        await page.screenshot(path="/root/tv_bot/homepage_debug.png")
        print("[+] Screenshot saved to /root/tv_bot/homepage_debug.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect())
