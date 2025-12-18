from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    应用配置类，用于从环境变量或 .env 文件中加载配置。
    """
    # 从 .env 文件中读取 ZHIPUAI_API_KEY
    ZHIPUAI_API_KEY: str

    # model_config 用于指定 .env 文件的位置和编码
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- 新增配置 ---
    # 微信小程序配置
    WECHAT_APP_ID: str = "wx45e19bbc2f953f5f"
    WECHAT_APP_SECRET: str = "a85ef002a12f0f05a8b0968ee8a062e4"

    # JWT 配置
    JWT_SECRET_KEY: str = "a_very_secret_key_that_should_be_long_and_random" # 务必替换成一个复杂且随机的字符串
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # Token 有效期：7天


# 创建一个全局可用的配置实例
settings = Settings()