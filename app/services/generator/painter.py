from openai import AsyncOpenAI
from app.core.config import settings
import asyncio

async def generate_images_from_ai(image_prompts: list[str]) -> list[str]:
    """
    根据规划好的图片描述列表，并行调用文生图模型生成图片。
    """
    client = AsyncOpenAI(
        api_key=settings.AI_IMAGE_API_KEY,
        base_url=settings.AI_IMAGE_BASE_URL,
    )

    print(f"准备根据 {len(image_prompts)} 个描述生成图片...")

    async def generate_single_image(p: str) -> str:
        print(f"向 AI 发送生图 prompt: {p}")
        try:
            response = await client.images.generate(
                model=settings.AI_IMAGE_MODEL,
                prompt=p,
            )
            return response.data[0].url
        except Exception as e:
            print(f"生成单张图片时出错: {e}")
            return "" 

    tasks = [generate_single_image(p) for p in image_prompts]
    image_urls = await asyncio.gather(*tasks)
    
    successful_urls = [url for url in image_urls if url]
    if not successful_urls:
        raise Exception("所有图片生成均失败。")
    return successful_urls