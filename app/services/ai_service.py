from zhipuai import ZhipuAI
from app.core.config import settings
from fastapi.concurrency import run_in_threadpool
import json
import asyncio
import re

# 使用从配置中读取的 API 密钥初始化智谱 AI 客户端
# 这个客户端实例可以在多个请求之间复用
client = ZhipuAI(api_key=settings.ZHIPUAI_API_KEY)

# --- 用于生成最终 HTML 的系统提示 ---
# 为 AI 设计一个“系统提示”(System Prompt)，指导它如何行动
SYSTEM_PROMPT = """
你是一个创意十足的前端开发专家和设计师，专门使用 HTML 和内联 CSS 为用户创作精美的海报。
你的任务是根据用户的提示词，生成一段独立的、完整的 HTML 代码。

规则：
1.  **必须** 返回一个完整的 HTML 结构，包含 `<html>`, `<head>`, 和 `<body>`。
2.  **必须** 在 `<head>` 的 `<style>` 标签内定义所有样式。不要使用外部 CSS 文件。海报的根元素（通常是 body 或一个 div）**必须** 包含 `overflow: hidden;` 样式，以确保任何内容都不会溢出画布。
3.  **字体与艺术效果**: 你的设计应该在字体上更有创意。
    *   **字体选择**: 灵活运用多种中文字体组合来增强设计感。例如，正文使用 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei' 等清晰易读的字体，而标题可以尝试更大胆、更有表现力的字体。
    *   **艺术字**: 对于标题或slogan，请大胆使用 CSS 技术创造“艺术字”效果。例如：使用 `text-shadow` 制作阴影或发光效果；使用 `background: linear-gradient(to right, #ff8a00, #e52e71); -webkit-background-clip: text; color: transparent;` 创造渐变色文字；或者使用 `transform` 属性进行轻微的旋转或缩放。
4.  海报的默认根元素尺寸 **必须** 为 800x1200 像素。
5.  **固定画布与智能布局**:
    *   海报的根元素 **必须** 拥有一个固定的尺寸，例如 `width: 800px; height: 1200px;`，并且 **必须** 设置 `overflow: hidden;`。
    *   **核心挑战**: 你需要像一个真正的设计师一样，将所有内容（文字、图片）智能地排布在这个固定的画布内。因为设置了 `overflow: hidden`，任何超出画布的内容都将被隐藏。因此，你的布局策略 **必须** 保证核心信息（如文字和图片主体）完整可见。
    *   **实现策略**: 优先使用 Flexbox (`display: flex`) 和 Grid (`display: grid`) 来进行宏观布局和空间分配。对于内容可能变化的区域，要利用弹性布局的特性（如 `flex-grow`, `flex-shrink`）来适应空间。如果文本内容过多，你应该适度减小字体大小或调整间距，以保证所有信息都能在画布内完整展示，而不是依赖溢出隐藏。
6.  **布局与构图**: 不要局限于“标题-图片-正文”的死板结构。你可以大胆运用 CSS 的 `position`, `flexbox` 或 `grid` 来创造更自由、更有创意的布局。例如，将标题或slogan放置在图片的某个角落，或者实现文字环绕图片的效果。在进行自由布局时，请确保文本和图片的核心内容不会被严重遮挡，保持信息的可读性。
7.  **多图处理**: 我会提供给你一个或多个图片 URL 列表。你必须在设计中使用我提供的所有图片。你可以使用 `grid` 或 `flexbox` 来创建优雅的图片画廊或拼贴效果。
8.  **必须** 使用我提供给你的图片 URL 列表作为海报的主图。不要使用任何其他图片。
9.  生成的内容应该紧扣用户提示词的主题，并围绕我提供的图片进行创意设计。
10.  除了 HTML 代码，不要返回任何额外的解释或注释。
"""

# --- 用于规划图片生成的系统提示 ---
PLAN_PROMPT = """
你是一个富有创造力的视觉总监。你的任务是根据用户的核心需求，规划一张海报需要多少张图片，并为每一张图片生成一个详细、具体、充满画面感的描述。
规则:
1.  根据用户需求，决定需要生成 1 到 3 张图片。
2.  为每一张图片创建一个独立的、详细的描述。描述应该具体，便于文生图模型理解和创作。
3.  **非常重要**: 你的描述应该是纯粹的画面描述，**绝对不能包含任何具体的文字、字母或数字**。例如，不要描述“墙上有'欢迎'字样”，而应该描述“墙上有一个用于放置标语的空白区域”。所有文字内容将由后续步骤在HTML中添加。
4.  你的回答必须是一个 JSON 对象，格式如下：
    {
      "image_prompts": [
        "第一张图片的详细描述...",
        "第二张图片的详细描述...",
        "..."
      ]
    }
5.  除了这个 JSON 对象，不要返回任何其他文本或解释。
"""

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
        response = await run_in_threadpool(
            client.chat.completions.create,
            model="glm-4.5-flash",
            messages=[
                {"role": "system", "content": PLAN_PROMPT},
                {"role": "user", "content": f"我的核心需求是: {prompt}"},
            ],
            temperature=0.5,
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
        image_generation_prompt = f"{p}风格要求：画面中的主体元素需要清晰。重要提示：如果画面中出现人物，必须避免出现任何面部扭曲、模糊或抽象的五官。重要提示：图片中绝对不能出现任何汉字或中文字符，但可以根据设计需要包含英文或数字。"
        print(f"向 CogView 发送 prompt: {image_generation_prompt}")
        try:
            response = await run_in_threadpool(
                client.images.generations,
                model="cogview-3-flash",
                prompt=image_generation_prompt,
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
        plan = await plan_image_generation(prompt)
        image_prompts = plan.get("image_prompts", [prompt])

        # 3. 根据规划生成图片
        image_urls = await generate_images_from_ai(image_prompts)
        
        # 4. 生成最终的 HTML
        print("所有图片已生成，开始生成最终 HTML...")
        # 将图片 URL 列表格式化为字符串，方便注入到 prompt 中
        image_urls_str = "\n".join(image_urls)
        response = await run_in_threadpool(
            client.chat.completions.create,
            model="glm-4.5-flash",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"请为我创建一个尺寸为 {width}x{height} 像素的海报。\n\n这是我为你准备好的图片URL列表，请用它们来设计海报:\n{image_urls_str}\n\n我的核心需求是: {prompt}"},
            ],
            temperature=0.8,
        )
        
        html_content = response.choices[0].message.content
        print("成功从 AI 获取 HTML 内容。")
        # 使用正则表达式更稳定地移除 AI 可能返回的代码块标记
        match = re.search(r"```html(.*)```", html_content, re.DOTALL)
        if match:
            clean_html = match.group(1).strip()
        else:
            clean_html = html_content.strip().replace("```html", "").replace("```", "")
        return clean_html, width, height, image_urls

    except Exception as e:
        print(f"调用智谱 AI API 时发生错误: {e}")
        # 如果 AI 调用失败，可以返回一个展示错误信息的海报
        return f"<html><body><h1>错误</h1><p>无法生成海报: {e}</p></body></html>", 800, 1200, []
