from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes import poster, auth # 引入 auth 路由
from app.services.renderer_service import browser_manager
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时执行
    await browser_manager.start_browser()
    yield
    # 应用关闭时执行
    await browser_manager.close_browser()

app = FastAPI(title="AI Poster Generator", lifespan=lifespan)

# CORS 配置，允许前端 H5 或小程序跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
# 挂载静态文件目录，用于访问生成的海报图片
app.mount("/static", StaticFiles(directory="generated_content"), name="static")

# 注册路由
app.include_router(poster.router, prefix="/api")
app.include_router(auth.router, prefix="/api", tags=["Authentication"]) # 注册 auth 路由

@app.get("/")
def root():
    return {"message": "AI Poster Backend is running"}
