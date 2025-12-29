from openai import AsyncOpenAI
from app.core.config import settings
from app.core.prompts import PLAN_PROMPT
import json
import re

async def plan_image_generation(prompt: str) -> dict:
    """调用语言模型规划需要生成的图片数量和内容。"""
    client = AsyncOpenAI(
        api_key=settings.AI_CHAT_API_KEY,
        base_url=settings.AI_CHAT_BASE_URL,
    )
    
    print("开始规划图片生成...")
    try:
        response = await client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": f"我的核心需求是: {prompt}"},
            ],
            extra_body={
                "thinking": {"type": "disabled"}
            },
        )
        plan_str = response.choices[0].message.content
        
        if not plan_str:
            print("AI 返回了空的图片生成计划，将使用默认计划。")
            return {"image_prompts": [prompt]}
            
        print(f"获取到 AI 返回的原始计划内容: {plan_str}")
        match = re.search(r'\{.*\}', plan_str, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            raise json.JSONDecodeError("在 AI 返回的内容中未找到有效的 JSON 对象。", plan_str, 0)
    except Exception as e:
        print(f"规划图片生成时出错: {e}")
        # 如果规划失败，默认生成一张图
        return {"image_prompts": [prompt]}