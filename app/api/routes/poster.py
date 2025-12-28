import time
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from app.schemas.poster import GenerateRequest, GenerateResponse
from app.services.ai_service import generate_html_from_ai
from app.services.renderer_service import render_html_to_image
from app.services.storage_service import save_artifacts

router = APIRouter()

@router.post("/generate")
async def generate_poster(gen_request: GenerateRequest):
    """
    接收用户 prompt，生成海报。
    """
    start_time = time.time()
    # 1. 调用 AI 生成 HTML、尺寸和图片 URL
    step1_start = time.time()
    html_content, width, height, image_urls = await generate_html_from_ai(gen_request.prompt)
    print(f"Step 1 - AI 内容生成耗时: {time.time() - step1_start:.2f}秒")

    # 2. 渲染 HTML 为图片
    step2_start = time.time()
    final_image_bytes = await render_html_to_image(html_content, width, height)
    print(f"Step 2 - HTML 渲染耗时: {time.time() - step2_start:.2f}秒")

    # 3. 保存所有产物
    # 这一步仍然执行，以便在服务器上留档，但我们不再使用它的返回值
    step3_start = time.time()
    await save_artifacts(html_content, image_urls, final_image_bytes)
    print(f"Step 3 - 产物保存耗时: {time.time() - step3_start:.2f}秒")
    
    print(f"Total - 接口总耗时: {time.time() - start_time:.2f}秒")
    # 4. 直接返回图片二进制内容
    # FastAPI 会自动设置正确的 Content-Type (image/png)
    return Response(content=final_image_bytes, media_type="image/jpeg")