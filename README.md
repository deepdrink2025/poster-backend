# AI 海报生成器后端

这是一个基于 FastAPI 和智谱 AI 大模型构建的后端服务，可以根据用户输入的文本提示（Prompt），自动生成一张设计精美的海报图片。

## ✨ 功能特性

- **AI 图片生成**: 调用智谱 `cogview-3` 模型，根据核心主题生成高质量的图片。
- **AI 布局设计**: 调用智谱 `glm-4.5-flash` 模型，围绕生成的图片和用户需求，智能地创建出完整的 HTML 和 CSS 布局。
- **自动化渲染**: 使用 Playwright 无头浏览器将 AI 生成的 HTML 代码精准渲染成一张 800x1200 像素的 PNG 图片。
- **异步高性能**: 基于 FastAPI 框架，所有 IO 密集型操作（如 API 请求、图片渲染）均为异步执行，保证了服务的性能和响应能力。

## 🚀 技术栈

- **后端框架**: FastAPI
- **AI 模型**: Zhipu AI (glm-4.5-flash, cogview-3)
- **HTML 渲染**: Playwright
- **Python 版本**: 3.9+

## 📂 项目结构

```
poster-backend/
├── services/
│   └── app/
│       ├── routes/
│       │   └── generate.py   # API 路由
│       ├── ai_client.py      # 智谱 AI 客户端
│       ├── config.py         # 配置加载
│       ├── main.py           # FastAPI 应用主入口
│       ├── models.py         # Pydantic 数据模型
│       └── renderer_client.py # Playwright 渲染客户端
├── .env                      # 环境变量文件 (需自行创建)
├── .env.example              # 环境变量模板
├── requirements.txt          # Python 依赖
└── README.md                 # 项目说明文档
```

## 🛠️ 安装与启动

请按照以下步骤在你的本地环境中设置并运行此项目。

### 1. 克隆项目

```bash
git clone <your-repository-url>
cd poster-backend
```

### 2. 创建并激活虚拟环境

使用虚拟环境是 Python 项目的最佳实践，可以隔离项目依赖。

```bash
# 创建虚拟环境 (文件夹名为 venv)
python3 -m venv venv

# 激活虚拟环境
# macOS / Linux
source venv/bin/activate
# Windows
# .\venv\Scripts\activate
```

### 3. 安装依赖

首先，安装 `requirements.txt` 中列出的所有 Python 包，然后为 Playwright 安装所需的浏览器核心。

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器依赖
playwright install
```

### 4. 配置环境变量

你需要一个智谱 AI 的 API Key 才能使用此服务。

1.  复制 `.env.example` 文件并重命名为 `.env`。
2.  打开 `.env` 文件，将 `your_zhipu_api_key_here` 替换为你自己的 Zhipu AI API Key。

### 5. 启动应用

一切准备就绪！运行以下命令启动 FastAPI 开发服务器。

```bash
uvicorn app.main:app --reload
```

服务器启动后，你会在终端看到类似 `Uvicorn running on http://127.0.0.1:8000` 的提示。

##  API 使用示例

你可以使用 `curl` 或任何 API 测试工具来调用生成接口。

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"prompt": "一个关于夏日海滩和冰淇淋的清新风格海报"}' \
  http://127.0.0.1:8000/api/generate \
  -o summer_poster.png
```

命令执行成功后，一张名为 `summer_poster.png` 的海报图片将会保存在你的当前目录。