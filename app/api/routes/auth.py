from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from typing import Annotated
import httpx
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt

from app.core.config import settings
# 假设你有一个处理数据库用户操作的服务
# from app.services import user_service 

router = APIRouter()

class Token(BaseModel):
    access_token: str
    token_type: str

class WxLoginRequest(BaseModel):
    code: str

# --- JWT 工具函数 ---
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """创建 JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 默认 15 分钟过期
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

@router.post("/login", response_model=Token)
async def wechat_login(payload: Annotated[WxLoginRequest, Body()]):
    """
    微信小程序登录接口。
    接收小程序端发送的 code，换取 openid，并返回自定义登录态 (JWT)。
    """
    if not payload.code:
        raise HTTPException(status_code=400, detail="Login 'code' is required.")

    # 1. 构造请求微信服务器的 URL
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": settings.WECHAT_APP_ID,
        "secret": settings.WECHAT_APP_SECRET,
        "js_code": payload.code,
        "grant_type": "authorization_code",
    }

    # 2. 发送请求到微信服务器
    async with httpx.AsyncClient() as client:
        try:
            wx_response = await client.get(url, params=params)
            wx_response.raise_for_status() # 如果状态码不是 2xx，则抛出异常
            wx_data = wx_response.json()
        except httpx.RequestError as exc:
            raise HTTPException(status_code=502, detail=f"Error requesting WeChat API: {exc}")

    # 3. 处理微信服务器的响应
    openid = wx_data.get("openid")
    if not openid:
        # 微信返回了错误信息
        # 在终端打印出微信返回的原始错误，方便调试
        print(f"从微信服务器获取 openid 失败: {wx_data}")
        raise HTTPException(status_code=400, detail=f"WeChat API error: {wx_data.get('errmsg', 'Unknown error')}")
    
    # 在终端打印从微信服务器获取到的原始用户信息
    print(f"成功从微信服务器换取用户信息: {wx_data}")

    # session_key = wx_data.get("session_key") # session_key 用于解密用户敏感数据，请妥善保管

    # 4. 在你的数据库中查找或创建用户 (***这里需要自己实现***)
    # user = await user_service.get_user_by_openid(openid)
    # if not user:
    #     user = await user_service.create_user(openid=openid)
    # 假设我们拿到了用户的唯一ID，这里我们直接使用 openid
    user_id = openid 

    # 5. 创建 JWT
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id}, expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}