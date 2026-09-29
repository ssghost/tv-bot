import asyncio
from fastapi import FastAPI, Request
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from tools.logger import record_alert

app = FastAPI()

CDP_URL = "http://127.0.0.1:9222"
playwright_instance = None
browser_instance = None
lock = asyncio.Lock()

async def get_tradingview_page():
    global playwright_instance, browser_instance
    try:
        if browser_instance and not browser_instance.is_connected():
            browser_instance = None
    except Exception:
        browser_instance = None

    if not playwright_instance:
        playwright_instance = await async_playwright().start()

    if not browser_instance:
        try:
            browser_instance = await playwright_instance.chromium.connect_over_cdp(
                CDP_URL
            )
        except Exception:
            return None

    for context in browser_instance.contexts:
        for p in context.pages:
            if "tradingview.com/chart" in p.url:
                try:
                    await p.bring_to_front()
                except Exception:
                    pass
                return p
    return None

async def ensure_authenticated(tv_page) -> bool:
    try:
        auth_error_selectors = [
            'text="Authentication Error"',
            'text="Session expired"',
            'div[class*="toast-"]:has-text("Authentication")',
            'div[class*="danger"]:has-text("Authentication")'
        ]
        has_error = False
        for sel in auth_error_selectors:
            el = await tv_page.query_selector(sel)
            if el and await el.is_visible():
                has_error = True
                break

        if has_error:
            reconnect_btn = await tv_page.query_selector(
                'button:has-text("Reconnect"), [data-name="reconnect-button"]'
            )
            if reconnect_btn and await reconnect_btn.is_visible():
                await reconnect_btn.click(timeout=1500, force=True)
                await asyncio.sleep(2)
                return True

            await tv_page.reload(wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(3)

            connect_btn = await tv_page.query_selector(
                '[data-name="connect-button"], button:has-text("Connect")'
            )
            if connect_btn and await connect_btn.is_visible():
                await connect_btn.click(timeout=2000, force=True)
                await asyncio.sleep(2)
            return True
    except Exception:
        pass
    return True

async def reload_and_wait_page(tv_page):
    try:
        await tv_page.reload(wait_until="domcontentloaded", timeout=15000)
        await tv_page.wait_for_selector(
            '[data-name="buy-button"], .button-buy, [aria-label*="Buy"]',
            timeout=10000,
            state="visible"
        )
        return True
    except Exception:
        return False

async def is_button_ready(tv_page, selector: str) -> bool:
    try:
        btn = await tv_page.wait_for_selector(selector, timeout=1500, state="visible")
        if not btn:
            return False
        is_disabled = await btn.get_attribute("aria-disabled")
        disabled_prop = await btn.get_attribute("disabled")
        if is_disabled == "true" or disabled_prop is not None:
            return False
        return True
    except Exception:
        return False

async def set_order_quantity(tv_page, contracts: int):
    target_val = str(contracts)
    selectors = [
        'div[data-name="order-ticket-quantity"] input',
        '[data-name="order-ticket-quantity-input"]',
        '.bid-ask-button-quantity input',
        'input[class*="input-"][inputmode="numeric"]',
        'input[class*="input-"][type="text"]'
    ]
    for sel in selectors:
        qty_input = await tv_page.query_selector(sel)
        if qty_input:
            try:
                await qty_input.evaluate(
                    """(el, value) => {
                        el.focus();
                        el.value = value;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    target_val
                )
                await tv_page.keyboard.press("Enter")
                val = await qty_input.input_value()
                if target_val in val:
                    return True

                await qty_input.click(click_count=3, timeout=1000)
                await tv_page.keyboard.press("Backspace")
                await qty_input.type(target_val, delay=10)
                await tv_page.keyboard.press("Enter")
                val = await qty_input.input_value()
                if target_val in val:
                    return True
            except Exception:
                continue
    return False

async def confirm_order_dialog(tv_page):
    selector = '[data-name="confirm-dialog-confirm-button"], button[data-name="confirm"], button[name="confirm"]'
    try:
        btn = await tv_page.wait_for_selector(selector, timeout=800, state="visible")
        if btn:
            await btn.click(timeout=800, force=True)
            return True
    except Exception:
        pass
    return False

async def execute_trade_task(action: str, contracts: int, market_position: str):
    async with lock:
        tv_page = await get_tradingview_page()
        if not tv_page:
            return

        await ensure_authenticated(tv_page)

        is_flat_exit = (market_position == "flat") or ("close" in action) or ("exit" in action)

        buy_selector = '[data-name="buy-button"], .button-buy, [aria-label*="Buy"]'
        sell_selector = '[data-name="sell-button"], .button-sell, [aria-label*="Sell"]'
        close_selector = '[data-name="close-position"], button[aria-label*="Close position"], [data-role="close-position-button"]'

        for attempt in range(2):
            try:
                if is_flat_exit:
                    close_btn = await tv_page.query_selector(close_selector)
                    if close_btn:
                        await close_btn.click(timeout=3000, force=True)
                        await confirm_order_dialog(tv_page)
                    return

                if action in ["buy", "sell"]:
                    target_selector = buy_selector if action == "buy" else sell_selector
                    ready = await is_button_ready(tv_page, target_selector)

                    if not ready and attempt == 0:
                        reloaded = await reload_and_wait_page(tv_page)
                        if not reloaded:
                            return
                        await ensure_authenticated(tv_page)
                        continue

                    if contracts > 0:
                        await set_order_quantity(tv_page, contracts)

                    await tv_page.click(target_selector, timeout=3000, force=True)
                    await confirm_order_dialog(tv_page)
                    return

            except PlaywrightTimeoutError:
                if attempt == 0:
                    reloaded = await reload_and_wait_page(tv_page)
                    if not reloaded:
                        return
                    await ensure_authenticated(tv_page)
                    continue
                return
            except Exception:
                return

@app.post("/webhook")
async def handle_webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "message": "Invalid JSON payload"}

    try:
        record_alert(data)
    except Exception:
        pass

    action = data.get("action", "").lower()
    try:
        contracts = int(float(data.get("contracts", 25)))
    except (ValueError, TypeError):
        contracts = 25

    market_position = data.get("market_position", "").lower()

    if action == "ping":
        return {"status": "success", "action": "ping", "contracts": contracts}

    if action in ["buy", "sell"] or market_position == "flat" or ("close" in action) or ("exit" in action):
        asyncio.create_task(execute_trade_task(action, contracts, market_position))
        return {
            "status": "received",
            "action": action,
            "contracts": contracts,
            "market_position": market_position
        }

    return {"status": "ignored", "action": action}

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
