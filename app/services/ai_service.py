from openai import AsyncOpenAI
from app.core.config import settings
from app.core.prompts import SYSTEM_PROMPT, PLAN_PROMPT
import json
import asyncio
import re
import time

# 使用通用的 OpenAI 客户端初始化
# 通过设置 base_url，可以无缝切换到任何兼容 OpenAI 接口的模型服务商（如智谱、DeepSeek、Moonshot等）

# 1. 聊天客户端 (火山引擎)
chat_client = AsyncOpenAI(
    api_key=settings.AI_CHAT_API_KEY,
    base_url=settings.AI_CHAT_BASE_URL,
)

# 2. 生图客户端 (硅基流动)
image_client = AsyncOpenAI(
    api_key=settings.AI_IMAGE_API_KEY,
    base_url=settings.AI_IMAGE_BASE_URL,
)

def extract_dimensions(prompt: str) -> tuple[int, int]:
    """从 prompt 中提取尺寸信息，如果没有则返回默认值。"""
    # 匹配 "横版"
    if "横版" in prompt:
        print("检测到'横版'关键词，使用尺寸 1200x800")
        return 1200, 800
    
    # 匹配如 1920x1080, 800*600 的尺寸
    match = re.search(r'(\d+)\s*[x*×]\s*(\d+)', prompt)
    if match:
        width, height = int(match.group(1)), int(match.group(2))
        print(f"从 prompt 中提取到尺寸: {width}x{height}")
        return width, height

    # 匹配如 16:9, 4:3 的宽高比
    match = re.search(r'(\d+)\s*:\s*(\d+)', prompt)
    if match:
        width = 1200
        height = int(width * int(match.group(2)) / int(match.group(1)))
        print(f"从 prompt 中提取到宽高比，计算出尺寸: {width}x{height}")
        return width, height

    print("未在 prompt 中发现尺寸信息，使用默认尺寸 800x1200")
    return 800, 1200 # 默认尺寸

async def plan_image_generation(prompt: str) -> dict:
    """第一步：调用语言模型规划需要生成的图片数量和内容。"""
    print("开始规划图片生成...")
    try:
        response = await chat_client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": f"我的核心需求是: {prompt}"},
            ],
            extra_body={
                "thinking": {
                    "type": "disabled",  # 不使用深度思考能力
                    # "type": "enabled", # 使用深度思考能力
                    # "type": "auto", # 模型自行判断是否使用深度思考能力
                }
            },
            # temperature=0.5,
        )
        plan_str = response.choices[0].message.content
        # 在尝试解析 JSON 之前，先检查字符串是否为空
        if not plan_str:
            print("AI 返回了空的图片生成计划，将使用默认计划。")
            # 如果规划失败，默认生成一张图
            return {"image_prompts": [prompt]}
            
        print(f"获取到 AI 返回的原始计划内容: {plan_str}")
        # 使用正则表达式提取 JSON 内容，以应对 AI 可能返回的 markdown 代码块
        match = re.search(r'\{.*\}', plan_str, re.DOTALL)
        if match:
            json_str = match.group(0)
            print(f"提取到的纯净 JSON 字符串: {json_str}")
            return json.loads(json_str)
        else:
            raise json.JSONDecodeError("在 AI 返回的内容中未找到有效的 JSON 对象。", plan_str, 0)
    except json.JSONDecodeError as json_e:
        print(f"规划图片生成时出错: JSON 解析失败。AI 返回内容: '{plan_str}'。错误: {json_e}")
        # 如果 JSON 解析失败，默认生成一张图
        return {"image_prompts": [prompt]}
    except Exception as general_e:
        print(f"规划图片生成时发生未知错误: {general_e}")
        # 如果规划失败，默认生成一张图
        return {"image_prompts": [prompt]}

async def generate_images_from_ai(image_prompts: list[str]) -> list[str]:
    """
    第二步：根据规划好的图片描述列表，并行调用文生图模型生成图片。
    """
    print(f"准备根据 {len(image_prompts)} 个描述生成图片...")

    async def generate_single_image(p: str) -> str:
        print(f"向 AI 发送生图 prompt: {p}")
        try:
            response = await image_client.images.generate(
                model=settings.AI_IMAGE_MODEL,
                prompt=p,
            )
            return response.data[0].url
        except Exception as e:
            print(f"生成单张图片时出错: {e}")
            return "" # 返回空字符串表示失败

    # 使用 asyncio.gather 并行执行所有图片的生成任务
    tasks = [generate_single_image(p) for p in image_prompts]
    image_urls = await asyncio.gather(*tasks)
    
    # 过滤掉生成失败的空字符串
    successful_urls = [url for url in image_urls if url]
    print(f"成功生成 {len(successful_urls)} 张图片。")
    if not successful_urls:
        raise Exception("所有图片生成均失败。")
    return successful_urls

async def generate_html_from_ai(prompt: str) -> tuple[str, int, int, list[str]]:
    """
    重构后的主函数，采用四步法生成海报：提取尺寸 -> 规划 -> 生成图片 -> 生成HTML。
    返回: (html_content, width, height, image_urls)
    """
    print(f"向 AI 发送总任务 prompt: {prompt}")
    try:
        # 1. 从 prompt 中提取尺寸
        width, height = extract_dimensions(prompt)

        # 2. 规划图片生成
        plan_start = time.time()
        plan = await plan_image_generation(prompt)
        image_prompts = plan.get("image_prompts", [prompt])
        print(f"  [AI Detail] 图片规划耗时: {time.time() - plan_start:.2f}秒")

        # 3. 根据规划生成图片
        img_gen_start = time.time()
        image_urls = await generate_images_from_ai(image_prompts)
        print(f"  [AI Detail] 图片生成耗时: {time.time() - img_gen_start:.2f}秒")
        
        # 4. 生成最终的 HTML
        print("所有图片已生成，开始生成最终 HTML...")
        html_gen_start = time.time()
        # 将图片 URL 列表格式化为字符串，方便注入到 prompt 中
        image_urls_str = "\n".join(image_urls)
        html_prompt_content = f"请为我创建一个尺寸为 {width}x{height} 像素的海报。\n\n这是我为你准备好的图片URL列表，请用它们来设计海报:\n{image_urls_str}\n\n我的核心需求是: {prompt}"
        
        response = await chat_client.chat.completions.create(
            model=settings.AI_CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": html_prompt_content},
            ],
            extra_body={
                "thinking": {
                    "type": "disabled",  # 不使用深度思考能力
                    # "type": "enabled", # 使用深度思考能力
                    # "type": "auto", # 模型自行判断是否使用深度思考能力
                }
            },
            # temperature=0.8,
        )
        # print(f"HTML 生成提示词:\n{SYSTEM_PROMPT, html_prompt_content}")
        html_content = response.choices[0].message.content
        print(f"  [AI Detail] HTML 代码生成耗时: {time.time() - html_gen_start:.2f}秒")
        print("成功从 AI 获取 HTML 内容。")
        # 使用正则表达式更稳定地移除 AI 可能返回的代码块标记
        match = re.search(r"```html(.*)```", html_content, re.DOTALL)
        if match:
            clean_html = match.group(1).strip()
        else:
            clean_html = html_content.strip().replace("```html", "").replace("```", "")
        return clean_html, width, height, image_urls

    except Exception as e:
        print(f"调用 AI API 时发生错误: {e}")
        if "InvalidEndpointOrModel" in str(e):
            print("【配置错误提示】火山引擎 (Volcengine) 需要使用 Endpoint ID 作为模型名称。")
            print("请去火山引擎控制台 -> 方舟 (Ark) -> 在线推理 -> 创建/查看接入点，复制以 'ep-' 开头的 ID，并填入 .env 文件的 AI_CHAT_MODEL 中。")
        # 如果 AI 调用失败，可以返回一个展示错误信息的海报
        return f"<html><body><h1>错误</h1><p>无法生成海报: {e}</p></body></html>", 800, 1200, []
