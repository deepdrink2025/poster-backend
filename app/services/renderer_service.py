import sys
import os
import asyncio
from playwright.async_api import async_playwright, Browser, Page, Playwright

# Windows 上设置环境变量，尝试影响 Playwright 的子进程创建
if sys.platform == "win32":
    # 设置环境变量，确保使用正确的 subprocess 方式
    os.environ.setdefault("PLAYWRIGHT_NODEJS_PATH", "")
    # 尝试设置其他可能影响 subprocess 的环境变量
    os.environ.setdefault("PYTHONUNBUFFERED", "1")

class BrowserManager:
    """
    一个管理 Playwright 浏览器实例的单例类，以在请求之间复用浏览器。
    """
    def __init__(self):
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self._started = False
        self._lock = asyncio.Lock()
        self._playwright_loop = None  # 存储 Playwright 线程中的事件循环（Windows）

    async def _ensure_browser_started(self):
        """确保浏览器已启动（延迟启动）"""
        if self._started and self.browser:
            return
        
        async with self._lock:
            # 双重检查
            if self._started and self.browser:
                return
            
            # Windows 上确保使用正确的事件循环类型
            if sys.platform == "win32":
                try:
                    loop = asyncio.get_running_loop()
                    # 检查事件循环类型
                    if not isinstance(loop, asyncio.SelectorEventLoop):
                        error_msg = (
                            f"错误: 当前事件循环类型为 {type(loop).__name__}，"
                            "Playwright 在 Windows 上需要 SelectorEventLoop。\n"
                            "请确保在应用启动前设置了 WindowsSelectorEventLoopPolicy。"
                        )
                        raise RuntimeError(error_msg)
                except RuntimeError as e:
                    # 如果没有运行中的循环，设置策略
                    if "事件循环类型" not in str(e):
                        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                    else:
                        raise
            
            print("正在启动全局浏览器实例...")
            try:
                # 尝试使用标准方式启动（如果事件循环策略已正确设置）
                # 如果失败，Windows 上回退到线程方案
                try:
                    self.playwright = await async_playwright().start()
                    self.browser = await self.playwright.chromium.launch()
                    self._started = True
                    print("全局浏览器实例已启动。")
                except NotImplementedError as e:
                    # Windows 上如果标准方式失败，使用线程方案
                    if sys.platform == "win32":
                        print("标准方式失败，使用线程方案启动 Playwright...")
                        def _start_in_thread():
                            """在单独线程中启动 Playwright"""
                            import asyncio as async_io
                            # 在新线程中设置事件循环策略
                            async_io.set_event_loop_policy(async_io.WindowsSelectorEventLoopPolicy())
                            # 创建新的事件循环
                            new_loop = async_io.new_event_loop()
                            async_io.set_event_loop(new_loop)
                            try:
                                # 在新循环中启动 Playwright
                                playwright = new_loop.run_until_complete(async_playwright().start())
                                browser = new_loop.run_until_complete(playwright.chromium.launch())
                                return playwright, browser, new_loop
                            except Exception:
                                new_loop.close()
                                raise
                        
                        # 在线程中执行
                        playwright, browser, loop = await asyncio.to_thread(_start_in_thread)
                        self.playwright = playwright
                        self.browser = browser
                        self._playwright_loop = loop  # 保存循环引用，用于清理
                        self._started = True
                        print("全局浏览器实例已启动（使用线程方案）。")
                    else:
                        # 非 Windows 系统不应该出现此错误
                        raise
            except Exception as e:
                print(f"启动浏览器时出错: {e}")
                import traceback
                traceback.print_exc()
                # 清理部分初始化的资源
                if self.browser:
                    try:
                        await self.browser.close()
                    except:
                        pass
                if self.playwright:
                    try:
                        await self.playwright.stop()
                    except:
                        pass
                self.browser = None
                self.playwright = None
                raise

    async def start_browser(self):
        """在应用启动时调用，初始化浏览器（Windows 上延迟启动）"""
        # Windows 上不立即启动，而是在第一次使用时启动
        if sys.platform == "win32":
            print("Windows 平台：浏览器将在第一次使用时延迟启动。")
            return
        
        # 非 Windows 系统立即启动
        await self._ensure_browser_started()

    async def close_browser(self):
        """在应用关闭时调用，清理资源。"""
        if not self._started:
            return
        
        # 设置超时，避免关闭操作无限阻塞
        try:
            # 关闭浏览器（最多等待 5 秒）
            if self.browser:
                try:
                    await asyncio.wait_for(self.browser.close(), timeout=5.0)
                except asyncio.TimeoutError:
                    print("警告: 关闭浏览器超时，强制关闭")
                    # 尝试强制关闭
                    try:
                        if hasattr(self.browser, 'close'):
                            # 如果浏览器对象有同步关闭方法，使用它
                            pass
                    except:
                        pass
                except Exception as e:
                    print(f"关闭浏览器时出错: {e}")
            
            # 停止 Playwright（最多等待 5 秒）
            if self.playwright:
                try:
                    await asyncio.wait_for(self.playwright.stop(), timeout=5.0)
                except asyncio.TimeoutError:
                    print("警告: 停止 Playwright 超时")
                except Exception as e:
                    print(f"停止 Playwright 时出错: {e}")
        except Exception as e:
            print(f"清理浏览器资源时出错: {e}")
        
        # Windows 上清理线程中的事件循环引用
        if sys.platform == "win32" and self._playwright_loop:
            try:
                # 注意：不能直接关闭其他线程的事件循环，这里只是清除引用
                # 实际的事件循环会在线程结束时自动清理
                self._playwright_loop = None
            except Exception as e:
                print(f"清理事件循环时出错: {e}")
        
        self._started = False
        self.browser = None
        self.playwright = None
        print("全局浏览器实例已关闭。")

    async def get_page(self) -> Page:
        """为每个请求获取一个新的页面。"""
        # 确保浏览器已启动（延迟启动）
        await self._ensure_browser_started()
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
