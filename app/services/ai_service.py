from app.services.generator.planner import plan_image_generation
from app.services.generator.painter import generate_images_from_ai
from app.services.generator.coder import generate_html_code
from app.utils.extract_dimensions import extract_dimensions
from app.core.config import settings
import time
import asyncio

async def generate_html_from_ai(prompt: str) -> tuple[str, int, int, list[str]]:
    """
    重构后的主函数，采用四步法生成海报：提取尺寸 -> 规划 -> 生成图片 -> 生成HTML。
    返回: (html_content, width, height, image_urls)
    """
    print(f"向 AI 发送总任务 prompt: {prompt}")
    
    # 打印调试状态
    if any([settings.SKIP_PLANNING, settings.SKIP_IMAGE_GENERATION, settings.SKIP_HTML_GENERATION]):
        print(f"⚠️ [DEBUG模式] 规划跳过: {settings.SKIP_PLANNING}, 生图跳过: {settings.SKIP_IMAGE_GENERATION}, HTML跳过: {settings.SKIP_HTML_GENERATION}")

    try:
        # 1. 从 prompt 中提取尺寸
        width, height = extract_dimensions(prompt)

        # 2. 规划图片生成
        if settings.SKIP_PLANNING:
            print("  [DEBUG] 跳过规划，直接使用原始提示词作为图片描述")
            image_prompts = [prompt]
        else:
            plan_start = time.time()
            plan = await plan_image_generation(prompt)
            image_prompts = plan.get("image_prompts", [prompt])
            print(f"  [AI Detail] 图片规划耗时: {time.time() - plan_start:.2f}秒")

        # 3 & 4. 并行执行：生成图片 和 生成 HTML
        # 为了并行，我们需要先定义 HTML 生成时使用的临时图片占位符
        temp_image_urls = [f"https://temp-image-placeholder.local/{i}.png" for i in range(len(image_prompts))]
        
        async def task_generate_images():
            if settings.SKIP_IMAGE_GENERATION:
                print("  [DEBUG] 跳过生图，生成占位图 URL")
                # 生成带尺寸和序号的占位图，方便前端查看布局
                return [f"https://placehold.co/{width}x{height}/png?text=Image+{i+1}" for i in range(len(image_prompts))]
            else:
                t_start = time.time()
                urls = await generate_images_from_ai(image_prompts)
                print(f"  [AI Detail] 图片生成耗时: {time.time() - t_start:.2f}秒")
                return urls

        async def task_generate_html():
            if settings.SKIP_HTML_GENERATION:
                print("  [DEBUG] 跳过 HTML 生成，返回简单测试页面")
                return f"<html><body style='background:#f0f0f0; display:flex; justify-content:center; align-items:center; height:100vh;'><h1>DEBUG MODE</h1><p>Prompt: {prompt}</p></body></html>"
            else:
                print("  [并行任务] 开始生成 HTML (使用占位符)...")
                t_start = time.time()
                # 使用临时占位符 URL 生成 HTML
                html = await generate_html_code(prompt, temp_image_urls, width, height)
                print(f"  [AI Detail] HTML 代码生成耗时: {time.time() - t_start:.2f}秒")
                return html

        print("启动并行任务：图片生成 & HTML生成...")
        parallel_start = time.time()
        
        # 并发执行
        image_urls, clean_html = await asyncio.gather(task_generate_images(), task_generate_html())
        
        print(f"  [AI Detail] 并行阶段总耗时: {time.time() - parallel_start:.2f}秒")

        # 5. 拼接：将 HTML 中的占位符替换为真实图片 URL
        if not settings.SKIP_HTML_GENERATION:
            print("正在将真实图片 URL 注入 HTML...")
            for temp_url, real_url in zip(temp_image_urls, image_urls):
                if temp_url not in clean_html:
                    print(f"⚠️ [警告] 占位符 {temp_url} 未在 HTML 中找到，AI 可能篡改了 URL 格式，导致图片无法显示！")
                clean_html = clean_html.replace(temp_url, real_url)
            
        return clean_html, width, height, image_urls

    except Exception as e:
        print(f"调用 AI API 时发生错误: {e}")
        if "InvalidEndpointOrModel" in str(e):
            print("【配置错误提示】火山引擎 (Volcengine) 需要使用 Endpoint ID 作为模型名称。")
            print("请去火山引擎控制台 -> 方舟 (Ark) -> 在线推理 -> 创建/查看接入点，复制以 'ep-' 开头的 ID，并填入 .env 文件的 AI_CHAT_MODEL 中。")
        # 如果 AI 调用失败，可以返回一个展示错误信息的海报
        return f"<html><body><h1>错误</h1><p>无法生成海报: {e}</p></body></html>", 800, 1200, []
