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

本项目的示例配置默认使用 API 模型：

- LLM：OpenAI 兼容接口，例如 OpenAI 官方接口或第三方中转站。
- Embedding：在线 Embedding API，例如阿里云百炼 DashScope 兼容接口。
- PDF 视觉理解：默认关闭，需要处理 PDF 图片内容时可改为在线视觉模型。
- Reranker：支持阿里云百炼 Qwen3-VL-Rerank API，默认关闭以避免额外费用。

代码中仍保留部分本地模型接入能力，但 Docker 部署模板不再默认挂载本地模型目录。常见配置在 `backend/.env` 或 `backend/.env.docker` 中维护，例如：

```env
LLM_TYPE=OPENAI
OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
OPENAI_API_KEY=your_api_key
OPENAI_MODEL_NAME=your_chat_model
OPENAI_TRUST_ENV=true

HTTP_PROXY=http://host.docker.internal:7890
HTTPS_PROXY=http://host.docker.internal:7890
NO_PROXY=localhost,127.0.0.1,mysql,redis,django,backend,front,host.docker.internal

EMBED_MODEL_TYPE=ALIYUN
ALIYUN_ACCESS_KEY_SECRET=your_embedding_api_key
ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
ALIYUN_EMBED_MODEL_NAME=qwen3-embedding

VISION_MODEL_TYPE=DISABLED

RERANKER_ENABLED=true
RERANKER_PROVIDER=ALIYUN
RERANKER_MODEL_NAME=qwen3-vl-rerank
RERANKER_WORKSPACE_ID=your_bailian_workspace_id
RERANKER_REGION=cn-beijing
RERANKER_TOP_N=8
RERANKER_TIMEOUT=30

MYSQL_HOST=mysql
MYSQL_PORT=3306
REDIS_HOST=redis
REDIS_PORT=6379
DJANGO_API_URL=http://django:8001
```

注意：不要把真实 API Key、数据库密码、JWT 密钥提交到公开仓库。

## Docker 部署

### 1. 准备环境变量

从脱敏模板生成本地配置文件：

```bash
cp .env.example .env
cp backend/.env.docker.example backend/.env.docker
cp DjangoUserService/.env.docker.example DjangoUserService/.env.docker
```

复制后必须编辑这三个文件：

- `.env` 里的 `COMPOSE_PROJECT_NAME` 可按需修改，也可以保持默认。
- `backend/.env.docker` 需要填写中转站地址、API Key、聊天模型名和 Embedding API Key。
- 如果服务器访问中转站必须走代理，在 `backend/.env.docker` 中配置 `HTTP_PROXY`、`HTTPS_PROXY` 和 `NO_PROXY`；如果不需要代理，删除或留空这几项。
- `backend/.env.docker` 的 `SECRET_KEY` 与 `DjangoUserService/.env.docker` 的 `JWT_SECRET_KEY` 必须相同。
- Backend 与 Django 的数据库账号密码必须与 `docker/mysql/init/01-init.sql` 中创建的 `rag_app` 用户一致；首次部署前请替换示例密码。
- 阿里云、OpenAI、LangSmith 等真实 API Key 只写入本地 `.env.docker`，不要提交到 Git。

Docker 内部服务之间通过 `mysql`、`redis`、`django` 等服务名通信，示例文件已经使用这些容器地址。

### 2. 校验配置

```bash
docker compose config
```

该命令应能输出完整 Compose 配置且不报错。不要把输出中的环境变量内容粘贴到公开渠道。

### 3. 生产环境启动

```bash
docker compose up -d --build
docker compose ps
```

生产环境只使用 `docker-compose.yml`，不要叠加开发配置。

### 4. Docker 开发模式

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

开发配置会挂载源码，并让 FastAPI 使用 `--reload`。查看开发后端日志：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f backend
```

### 5. 持久化数据

以下内容属于运行数据，不应提交到 Git，也不能在未备份时删除：

- `backend/data/`：Chroma 向量库、MD5 去重记录和文档处理数据。
- `mysql_data`：用户、会话、笔记、回顾等 MySQL 数据。
- `redis_data`：Redis 持久化数据。
- `django_media`：Django 用户上传媒体文件。

以下操作会造成数据丢失：

```bash
docker compose down -v
rm -rf backend/data/chromadb
```

- `docker compose down -v` 会删除 MySQL、Redis 和 Django media 等 named volumes。
- 删除 `backend/data/chromadb` 会清空知识库和笔记向量，之后必须重新上传知识库并重建笔记向量。

普通停止不会删除数据：

```bash
docker compose down
```

### 6. 查看日志

```bash
docker compose logs -f backend
docker compose logs -f django
docker compose logs -f front
```

### 7. 访问项目

- 前端页面：http://127.0.0.1:3000
- FastAPI 服务：http://127.0.0.1:8000
- Django 服务：http://127.0.0.1:8001

### 8. 管理员后台

项目使用 Django Admin 作为唯一管理员后台。首次启动后执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec django \
  uv run python manage.py createsuperuser
```

按提示设置管理员邮箱、用户名和密码，然后访问：

```text
http://127.0.0.1:8001/admin/
```

系统只允许创建一个超级管理员；已有管理员时再次执行 `createsuperuser` 会被拒绝。项目不再自动创建弱口令测试账号。

后台首页还提供以下功能：

- 系统状态：检查用户数据库、FastAPI 业务数据库、Redis 和 FastAPI readiness。
- 后端日志：查看 `backend/logs/` 最近生成的日志文件，默认显示每个文件最后 500 行。
- 业务数据：只读查看会话、消息、笔记和回顾记录。

业务数据由 FastAPI 同时维护 MySQL 和 Chroma 向量库，因此 Django Admin 默认不允许直接编辑或删除这些数据，避免数据库记录和向量索引不一致。

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

开发模式重启后端：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
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
