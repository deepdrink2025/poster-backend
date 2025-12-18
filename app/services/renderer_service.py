from playwright.async_api import async_playwright, Browser, Page, Playwright

class BrowserManager:
    """
    一个管理 Playwright 浏览器实例的单例类，以在请求之间复用浏览器。
    """
    def __init__(self):
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None

    async def start_browser(self):
        """在应用启动时调用，初始化浏览器。"""
        print("正在启动全局浏览器实例...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()
        print("全局浏览器实例已启动。")

    async def close_browser(self):
        """在应用关闭时调用，清理资源。"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("全局浏览器实例已关闭。")

    async def get_page(self) -> Page:
        """为每个请求获取一个新的页面。"""
        if not self.browser:
            raise Exception("浏览器实例尚未启动。")
        return await self.browser.new_page()

# 创建一个全局的浏览器管理器实例
browser_manager = BrowserManager()

async def render_html_to_image(html_content: str, width: int, height: int) -> bytes:
    """
    使用 Playwright 将给定的 HTML 字符串渲染成图片。
    """
    page = await browser_manager.get_page()
    try:
        await page.set_viewport_size({"width": width, "height": height})
        await page.set_content(html_content)
        screenshot_bytes = await page.screenshot(type="png")
        return screenshot_bytes
    finally:
        await page.close() # 每次请求后关闭页面，而不是整个浏览器
