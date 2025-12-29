from openai import AsyncOpenAI
from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT, HTML_USER_PROMPT
import re

async def generate_html_code(prompt: str, image_urls: list[str], width: int, height: int) -> str:
    """
    生成 HTML 代码。
    """
    client = AsyncOpenAI(
        api_key=settings.AI_CHAT_API_KEY,
        base_url=settings.AI_CHAT_BASE_URL,
    )
    
    image_urls_str = "\n".join(image_urls)
    html_prompt_content = HTML_USER_PROMPT.format(
        width=width,
        height=height,
        image_urls_str=image_urls_str,
        prompt=prompt
    )
    
    response = await client.chat.completions.create(
        model=settings.AI_CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": html_prompt_content},
        ],
        extra_body={
            "thinking": {"type": "disabled"}
        },
    )
    html_content = response.choices[0].message.content
    print("成功从 AI 获取 HTML 内容。")
    
    match = re.search(r"```html(.*)```", html_content, re.DOTALL)
    if match:
        clean_html = match.group(1).strip()
    else:
        clean_html = html_content.strip().replace("```html", "").replace("```", "")
    return clean_html