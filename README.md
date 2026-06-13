# RAG NoteBook 智能知识助手

RAG NoteBook 是一个面向个人知识管理的 AI 助手项目，核心能力是把“笔记、知识库文档、AI 对话、每日回顾”连接起来，让用户可以上传资料、记录笔记，并通过 AI 助手基于自己的知识内容进行问答和写作辅助。

项目采用前后端分离架构：

- 前端：Vue 3 + Vite + Vant，提供登录、聊天、知识库、笔记、每日回顾等页面。
- 用户服务：Django + DRF，负责用户注册登录、JWT 鉴权、文件管理等能力。
- AI 服务：FastAPI + LangChain，负责 Agent 对话、RAG 检索、知识库切片、向量检索、笔记检索和写作辅助。
- 数据层：MySQL 存储用户、会话、笔记等结构化数据；Redis 用于缓存和异步任务；ChromaDB 用于本地向量库。

## 核心功能

- 用户注册、登录和 JWT 身份认证。
- AI 流式对话，支持会话历史保存。
- RAG 知识库问答，支持 TXT、PDF、Markdown、PPTX、DOCX 等文档。
- 文档切片、MD5 去重、向量化入库和相似度检索。
- 笔记管理，支持 Markdown 编辑、分类、标签和搜索。
- 笔记与知识库联合检索，AI 回答时可以结合用户上传资料和个人笔记。
- HyDE 检索增强：先生成假设性文档，再结合原始问题进行双路检索。
- BM25 + 向量检索混合召回，提高短问题和语义问题的命中率。
- 每日回顾功能，基于遗忘曲线帮助用户复习笔记。
- AI 写作辅助，支持续写、扩写、摘要、联想补全等能力。
- Docker Compose 一键编排前端、后端、Django、MySQL、Redis。

## 技术栈

| 模块 | 技术 |
| --- | --- |
| 前端 | Vue 3、Vite、Vant、Pinia、Axios、ByteMD |
| AI 后端 | FastAPI、LangChain、LangChain OpenAI、DashScope、ChromaDB |
| 用户服务 | Django、Django REST Framework、SimpleJWT |
| 数据库 | MySQL、Redis、ChromaDB |
| 检索 | 向量检索、BM25、HyDE、可选 Reranker |
| 文档处理 | PyMuPDF、pypdf、unstructured、python-magic |
| 部署 | Docker、Docker Compose、Nginx |

## 项目结构

```text
LangChain-RAG-FastAPI-Service
├── backend/                 # FastAPI + LangChain AI 服务
│   ├── app/agent/            # Agent 对话、工具调用、流式响应
│   ├── app/rag/              # RAG 检索、切片、向量库、重排序
│   ├── app/router/           # 聊天、知识库、笔记、回顾接口
│   ├── app/prompt/           # Prompt 模板
│   ├── app/utils/            # 模型工厂、鉴权、文件处理等工具
│   └── pyproject.toml
├── DjangoUserService/        # Django 用户与文件服务
│   ├── apps/user/            # 用户注册、登录、鉴权
│   ├── apps/file/            # 文件上传和管理
│   └── pyproject.toml
├── front/                    # Vue 前端
│   ├── src/views/            # 页面
│   ├── src/components/       # 组件
│   └── package.json
├── docker/                   # Docker 初始化脚本
├── docs/                     # 项目说明和部署文档
└── docker-compose.yml        # Docker 编排文件
```

## 模型配置说明

本项目支持多种模型接入方式。

大语言模型可以使用：

- OpenAI 兼容接口，例如 OpenAI 官方接口或第三方中转站。
- 阿里云百炼 DashScope。
- Ollama 本地模型。

向量模型可以使用：

- 阿里云在线 Embedding API。
- Ollama 本地 Embedding。
- 本地 SentenceTransformer/Qwen Embedding 模型。

常见配置在 `backend/.env` 或 `backend/.env.docker` 中维护，例如：

```env
LLM_TYPE=OPENAI
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_API_KEY=your_api_key
OPENAI_MODEL_NAME=gpt-5.5

EMBED_MODEL_TYPE=LOCAL_QWEN
LOCAL_EMBED_MODEL_PATH=/models/Qwen3-Embedding-0.6B
LOCAL_EMBED_DEVICE=cpu

MYSQL_HOST=mysql
MYSQL_PORT=3306
REDIS_HOST=redis
REDIS_PORT=6379
DJANGO_API_URL=http://django:8001
```

注意：不要把真实 API Key、数据库密码、JWT 密钥提交到公开仓库。

## Docker 部署

### 1. 准备环境变量

复制本地环境变量文件，生成 Docker 专用配置：

```bash
cp backend/.env backend/.env.docker
cp DjangoUserService/.env DjangoUserService/.env.docker
```

Docker 内部服务之间通过容器名访问，所以需要把 `.env.docker` 中的地址改成容器名：

```env
# backend/.env.docker
MYSQL_HOST=mysql
REDIS_HOST=redis
DJANGO_API_URL=http://django:8001
LOCAL_EMBED_MODEL_PATH=/models/Qwen3-Embedding-0.6B
```

```env
# DjangoUserService/.env.docker
DB_HOST=mysql
REDIS_CACHE_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### 2. 构建镜像

```bash
docker compose build
```

如果之前构建失败或缓存异常，可以重新无缓存构建：

```bash
docker compose build --no-cache
```

### 3. 启动基础服务

```bash
docker compose up -d mysql redis
docker compose ps
```

如果本机已经启动了 MySQL 或 Redis，可能会出现 `address already in use`。这个项目的后端容器可以直接通过 `mysql:3306`、`redis:6379` 访问数据库和缓存，通常不需要把 MySQL/Redis 暴露到宿主机。

### 4. 启动全部服务

```bash
docker compose up -d
docker compose ps
```

### 5. 查看日志

```bash
docker compose logs -f backend
docker compose logs -f django
docker compose logs -f front
```

### 6. 访问项目

- 前端页面：http://127.0.0.1:3000
- FastAPI 服务：http://127.0.0.1:8000
- Django 服务：http://127.0.0.1:8001

停止服务：

```bash
docker compose down
```

停止服务并删除 Docker 数据卷：

```bash
docker compose down -v
```

`down -v` 会删除 MySQL、Redis 等 Docker 数据卷，已有 Docker 数据会被清空，执行前需要确认。

## 本地开发启动

### 启动 FastAPI AI 服务

```bash
cd backend
uv sync
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 启动 Django 用户服务

```bash
cd DjangoUserService
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:8001
```

### 启动前端

```bash
cd front
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```

访问：

```text
http://127.0.0.1:3000
```

## RAG 问答流程

用户在前端聊天页面提问后，请求会发送到 FastAPI AI 服务。后端会完成以下流程：

1. 校验用户 JWT，确认当前用户身份。
2. 读取当前会话历史，形成短期上下文。
3. 根据用户问题生成 HyDE 假设性文档。
4. 使用原始问题和 HyDE 文档分别检索笔记库与知识库。
5. 合并检索结果，并按相似度、BM25 或重排序结果筛选相关内容。
6. 把检索到的上下文注入 Prompt。
7. 调用大语言模型生成回答。
8. 通过 SSE 流式返回给前端。
9. 将用户问题和 AI 回复保存到 MySQL，供后续会话继续使用。

## 常用命令

查看容器状态：

```bash
docker compose ps
```

重启后端：

```bash
docker compose restart backend
```

查看后端日志：

```bash
docker compose logs -f backend
```

重新构建并启动：

```bash
docker compose build
docker compose up -d
```

进入后端容器：

```bash
docker compose exec backend bash
```

## Git 分支推送命令

第一次推送到自己的 Git 仓库，可以按下面步骤执行。

查看当前分支：

```bash
git branch
```

查看改动：

```bash
git status
```

添加改动：

```bash
git add .
```

提交改动：

```bash
git commit -m "docs: update project readme"
```

如果你还没有绑定远程仓库：

```bash
git remote add origin 你的仓库地址
```

如果已经绑定过远程仓库，可以查看：

```bash
git remote -v
```

推送当前分支到远程仓库：

```bash
git push -u origin 当前分支名
```

例如当前分支是 `main`：

```bash
git push -u origin main
```

如果你想新建一个分支再推送：

```bash
git checkout -b docker-deploy
git add .
git commit -m "docs: add docker deployment readme"
git push -u origin docker-deploy
```

## 注意事项

- `.env`、`.env.docker` 中通常包含密钥，提交前请确认 `.gitignore` 已经忽略这些文件。
- 本地向量模型体积较大，不建议提交到 Git 仓库。
- Docker 部署时，容器内访问 MySQL、Redis、Django 服务应使用 `mysql`、`redis`、`django` 这些服务名。
- 如果服务器内存较小，建议优先关闭重排序模型，或把向量模型放在本地/更高配置机器运行。
- 如果使用第三方 OpenAI 兼容中转站，`OPENAI_BASE_URL` 通常需要以 `/v1` 结尾。
