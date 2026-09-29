import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        user_data_dir = "/root/tv_bot/browser_data"
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            viewport={"width": 1920, "height": 1080},
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled"
            ]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("[*] Navigating to TradingView homepage...")
        await page.goto("https://www.tradingview.com/", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        print("[*] Clicking visible user menu icon...")
        user_menu_btn = page.locator("button[aria-label*='user menu' i]:visible").first
        await user_menu_btn.click(timeout=15000)
        await page.wait_for_timeout(1000)

        print("[*] Clicking 'Sign in' from dropdown...")
        sign_in_item = page.locator("button:has-text('Sign in'):visible, div[role='menuitem']:has-text('Sign in'):visible, span:has-text('Sign in'):visible").first
        await sign_in_item.click(timeout=10000)
        await page.wait_for_timeout(2000)

        email_btn = page.locator("button:has-text('Email'):visible, span:has-text('Email'):visible").first
        if await email_btn.count() > 0 and await email_btn.is_visible():
            print("[*] Clicking 'Email' option...")
            await email_btn.click()
            await page.wait_for_timeout(1500)

        print("[*] Waiting for Email and Password inputs...")
        email_input = page.locator("input[name='id_username'], input[placeholder*='Email or Username' i], input[type='text']:visible").first
        await email_input.wait_for(state="visible", timeout=15000)

        username = input("Enter TradingView Email or Username: ").strip()
        password = input("Enter TradingView Password: ").strip()

        await email_input.fill(username)
        pwd_input = page.locator("input[name='id_password'], input[type='password']:visible").first
        await pwd_input.fill(password)

        submit_btn = page.locator("button[type='submit']:visible, button:has-text('Sign in'):visible").last
        await submit_btn.click()
        print("[*] Credentials submitted. Waiting for 2FA screen...")
        await page.wait_for_timeout(4000)

        two_fa_input = page.locator("input[placeholder*='Code from your app' i], input[name='code'], input[autocomplete='one-time-code'], input[type='text']:visible").first
        if await two_fa_input.is_visible():
            two_fa_code = input("Enter your 2FA verification code: ").strip()
            await two_fa_input.fill(two_fa_code)
            await page.keyboard.press("Enter")
            print("[*] 2FA submitted.")

        print("[*] Waiting 10 seconds for page to settle...")
        await page.wait_for_timeout(10000)

        screenshot_path = "/root/tv_bot/login_result.png"
        await page.screenshot(path=screenshot_path)
        print(f"[+] Login screen captured to {screenshot_path}. Please inspect manually.")

        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
