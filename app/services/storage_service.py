import aiohttp
import aiofiles
import os
import uuid
from datetime import datetime
import asyncio


async def download_and_save_image(session: aiohttp.ClientSession, url: str, base_path: str) -> str:
    """下载单个图片并保存到本地"""
    try:
        async with session.get(url, ssl=False) as response:
            response.raise_for_status()
            content = await response.read()
            # 使用 URL 的最后一部分作为文件名基础，或者生成一个 UUID
            file_ext = os.path.splitext(url.split('?')[0])[-1] or '.png'
            file_name = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(base_path, file_name)
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            print(f"图片已保存到: {file_path}")
            return file_path
    except Exception as e:
        print(f"下载图片 {url} 失败: {e}")
        return ""

async def save_final_image(image_bytes: bytes, path: str):
    """异步保存最终渲染出的海报图片。"""
    try:
        async with aiofiles.open(path, 'wb') as f:
            await f.write(image_bytes)
        print(f"最终渲染海报已保存到: {path}")
    except Exception as e:
        print(f"保存最终渲染海报时出错: {e}")


async def save_artifacts(html_content: str, image_urls: list[str], final_image_bytes: bytes) -> str:
    """
    保存所有生成物：HTML、原始图片和最终渲染的海报。
    返回最终海报的相对路径。
    """
    # 创建一个基于日期的文件夹来存放本次生成的所有文件
    base_dir = "generated_content"
    session_dir = os.path.join(base_dir, datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:6]}")
    os.makedirs(session_dir, exist_ok=True)

    # 1. 保存 HTML 文件
    html_file_path = os.path.join(session_dir, "poster.html")
    async with aiofiles.open(html_file_path, 'w', encoding='utf-8') as f:
        await f.write(html_content)
    print(f"HTML 文件已保存到: {html_file_path}")

    # 2. 保存最终渲染的海报图片
    final_image_path = os.path.join(session_dir, "final_poster.jpg")
    
    # 3. 仅保存最终渲染的海报图片
    await save_final_image(final_image_bytes, final_image_path)
    
    return final_image_path