# Deployment Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变业务行为和不删除运行数据的前提下，规范测试目录、移除确认未使用的配置，并补齐可安全提交的 Docker 部署模板与说明。

**Architecture:** 测试脚本只迁移路径，运行时模块只删除无引用配置。部署参数继续通过宿主机环境文件注入，示例文件只提供占位值；Compose 负责服务编排，真实密钥不进入镜像和 Git。

**Tech Stack:** Python 3、FastAPI、Django、Vue 3、Docker Compose、YAML、Markdown

---

### Task 1: 迁移后端回归测试

**Files:**
- Create: `backend/tests/README.md`
- Move: `backend/test_agent_note_idempotency.py` -> `backend/tests/test_agent_note_idempotency.py`
- Move: `backend/test_chroma_settings.py` -> `backend/tests/test_chroma_settings.py`
- Move: `backend/test_factory.py` -> `backend/tests/test_factory.py`
- Move: `backend/test_file_handler.py` -> `backend/tests/test_file_handler.py`
- Move: `backend/test_note_auto_tag.py` -> `backend/tests/test_note_auto_tag.py`
- Move: `backend/test_rag_query.py` -> `backend/tests/test_rag_query.py`
- Move: `backend/test_related_notes.py` -> `backend/tests/test_related_notes.py`
- Move: `backend/test_response_text.py` -> `backend/tests/test_response_text.py`
- Move: `backend/test_review_question.py` -> `backend/tests/test_review_question.py`

- [ ] **Step 1: 创建测试目录并原样移动脚本**

```bash
mkdir -p backend/tests
mv backend/test_*.py backend/tests/
```

- [ ] **Step 2: 写测试执行说明**

`backend/tests/README.md` 写明：

```markdown
# 后端回归测试

纯工具测试可从项目根目录执行：

```bash
PYTHONPATH=backend python3 backend/tests/test_chroma_settings.py
PYTHONPATH=backend python3 backend/tests/test_rag_query.py
PYTHONPATH=backend python3 backend/tests/test_related_notes.py
PYTHONPATH=backend python3 backend/tests/test_review_question.py
PYTHONPATH=backend python3 backend/tests/test_note_auto_tag.py
PYTHONPATH=backend python3 backend/tests/test_response_text.py
```

依赖完整后端环境的测试在开发容器中执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_file_handler.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_factory.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_agent_note_idempotency.py
```
```

- [ ] **Step 3: 验证纯工具测试在新路径可运行**

```bash
PYTHONPATH=backend python3 backend/tests/test_chroma_settings.py
PYTHONPATH=backend python3 backend/tests/test_rag_query.py
PYTHONPATH=backend python3 backend/tests/test_related_notes.py
PYTHONPATH=backend python3 backend/tests/test_review_question.py
PYTHONPATH=backend python3 backend/tests/test_note_auto_tag.py
PYTHONPATH=backend python3 backend/tests/test_response_text.py
```

Expected: 所有命令退出码为 `0`。

---

### Task 2: 删除未使用 Prompt 和 Agent 配置

**Files:**
- Delete: `backend/app/prompt/report_prompt.txt`
- Delete: `backend/app/prompt/reorder_prompt.txt`
- Delete: `backend/app/config/agent.yaml`
- Modify: `backend/app/config/prompt.yaml`
- Modify: `backend/app/utils/config.py`
- Modify: `backend/app/utils/prompt_loader.py`

- [ ] **Step 1: 再次确认生产代码没有引用**

```bash
rg "report_prompt|reorder_prompt|agent_config|agent\.yaml" backend/app
```

Expected: 只命中待删除配置、文档注释或调试入口，不命中业务调用。

- [ ] **Step 2: 删除 Prompt 配置项**

将 `backend/app/config/prompt.yaml` 更新为：

```yaml
main_prompt: app/prompt/main_prompt.txt
rag_summary_prompt: app/prompt/rag_summarize.txt
auto_tag_prompt: app/prompt/auto_tag_prompt.txt
review_question_prompt: app/prompt/review_question_prompt.txt
autocomplete_prompt: app/prompt/autocomplete_prompt.txt
write_assistant_prompt: app/prompt/write_assistant_prompt.txt
```

- [ ] **Step 3: 删除未使用配置加载和调试入口**

将 `backend/app/utils/config.py` 保留为：

```python
from app.utils.config_handler import load_config
from app.utils.path_tool import get_abstract_path

chroma_config = load_config(config_path=get_abstract_path('app/config/chroma.yaml'))
prompt_config = load_config(config_path=get_abstract_path('app/config/prompt.yaml'))
```

- [ ] **Step 4: 更新 Prompt loader 文档并移除调试入口**

保留 `load_prompt()` 的现有异常处理，只把文档中的可用类型更新为当前六个配置项，并删除文件末尾：

```python
if __name__ == '__main__':
    print(load_prompt('report_prompt'))
```

- [ ] **Step 5: 删除三个无引用文件**

```bash
rm backend/app/prompt/report_prompt.txt
rm backend/app/prompt/reorder_prompt.txt
rm backend/app/config/agent.yaml
```

- [ ] **Step 6: 验证无残留引用**

```bash
rg "report_prompt|reorder_prompt|agent_config|agent\.yaml" backend/app
```

Expected: 无匹配。

---

### Task 3: 新增脱敏 Docker 环境模板

**Files:**
- Create: `.env.example`
- Create: `backend/.env.docker.example`
- Create: `DjangoUserService/.env.docker.example`

- [ ] **Step 1: 新增 Compose 级模板**

`.env.example`：

```dotenv
# 宿主机本地模型目录，将以只读方式挂载到容器 /models
LOCAL_MODELS_DIR=/path/to/models
```

- [ ] **Step 2: 新增 FastAPI Docker 模板**

`backend/.env.docker.example` 至少包含当前代码读取的变量，并使用 Docker 内部地址：

```dotenv
LLM_TYPE=ALIYUN
ALIYUN_ACCESS_KEY_SECRET=replace-with-api-key
ALIYUN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
CHAT_MODEL_NAME=qwen3-max

EMBED_MODEL_TYPE=LOCAL_QWEN
LOCAL_EMBED_MODEL_PATH=/models/Qwen3-Embedding-0.6B
LOCAL_EMBED_DEVICE=cpu

RERANKER_MODEL_PATH=/models/Qwen3-Reranker-0.6B
RERANKER_DEVICE=cpu

MYSQL_USER=rag_app
MYSQL_PASSWORD=replace-with-password-matching-docker-init
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_DATABASE=chat_history

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
DJANGO_API_URL=http://django:8001

SECRET_KEY=replace-with-a-long-random-secret
ALGORITHM=HS256
RATE_LIMIT_ENABLED=true
LANGCHAIN_TRACING_V2=false
```

- [ ] **Step 3: 新增 Django Docker 模板**

`DjangoUserService/.env.docker.example`：

```dotenv
JWT_SECRET_KEY=replace-with-the-same-secret-as-backend
ALLOWED_HOSTS=localhost,127.0.0.1,django

DB_ENGINE=mysql
DB_HOST=mysql
DB_PORT=3306
DB_NAME=user_service
DB_USER=rag_app
DB_PASSWORD=replace-with-password-matching-docker-init

REDIS_CACHE_URL=redis://redis:6379/1
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_TIME_LIMIT=10
CELERY_TASK_SOFT_TIME_LIMIT=8
CELERY_RESULT_EXPIRES=3600
```

- [ ] **Step 4: 检查模板没有真实密钥**

```bash
rg "sk-[A-Za-z0-9]|MY_JWT|123456" .env.example backend/.env.docker.example DjangoUserService/.env.docker.example
```

Expected: 无匹配。

---

### Task 4: 更新服务器部署文档

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 替换 Docker 环境准备流程**

使用以下命令替换从真实本地 `.env` 复制的旧流程：

```bash
cp .env.example .env
cp backend/.env.docker.example backend/.env.docker
cp DjangoUserService/.env.docker.example DjangoUserService/.env.docker
```

明确要求部署者编辑三个文件并保证：

- `LOCAL_MODELS_DIR` 指向服务器模型目录。
- Backend 与 Django 使用相同 JWT secret。
- 两个服务的数据库密码与 `docker/mysql/init/01-init.sql` 一致。
- 真实 API Key 只放在 `.env.docker`。

- [ ] **Step 2: 区分生产和开发命令**

生产环境：

```bash
docker compose config
docker compose up -d --build
```

开发环境：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

- [ ] **Step 3: 记录持久化和危险操作**

文档明确：

- `backend/data` 保存 Chroma 和上传处理数据。
- `mysql_data`、`redis_data`、`django_media` 是 Docker volume。
- `docker compose down -v` 会删除 named volumes。
- 删除 `backend/data/chromadb` 会清空知识库和笔记向量，必须重新入库。

- [ ] **Step 4: 更新常用重启命令**

生产环境：

```bash
docker compose restart backend
```

开发环境：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml restart backend
```

---

### Task 5: 完整验证

**Files:**
- Verify all files changed in Tasks 1-4

- [ ] **Step 1: 运行后端纯工具测试**

```bash
PYTHONPATH=backend python3 backend/tests/test_chroma_settings.py && \
PYTHONPATH=backend python3 backend/tests/test_rag_query.py && \
PYTHONPATH=backend python3 backend/tests/test_related_notes.py && \
PYTHONPATH=backend python3 backend/tests/test_review_question.py && \
PYTHONPATH=backend python3 backend/tests/test_note_auto_tag.py && \
PYTHONPATH=backend python3 backend/tests/test_response_text.py
```

Expected: 退出码 `0`。

- [ ] **Step 2: 在 Docker 可用时运行依赖完整测试**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  sh -c "uv run python tests/test_file_handler.py && uv run python tests/test_factory.py && uv run python tests/test_agent_note_idempotency.py"
```

Expected: 退出码 `0`。若执行环境无法连接 Docker API，记录为未验证，不声称通过。

- [ ] **Step 3: 构建前端**

```bash
npm --prefix front run build
```

Expected: Vite 构建退出码 `0`。

- [ ] **Step 4: 校验 Compose**

```bash
docker compose config
docker compose -f docker-compose.yml -f docker-compose.dev.yml config
```

Expected: 两条命令都能输出完整配置且退出码 `0`。

- [ ] **Step 5: 检查残留引用与 IDE 诊断**

```bash
rg "report_prompt|reorder_prompt|agent_config|agent\.yaml" backend/app
```

Expected: 无匹配；修改文件无新增 IDE diagnostics。

---

## 执行约束

- 不运行数据删除命令。
- 不修改真实 `.env` 和 `.env.docker`。
- 不创建 Git commit。
- 如发现设计外的部署问题，只记录，不在本计划中顺手修改。
