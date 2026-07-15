# 部署导向的第二阶段项目整理设计

## 目标

在不改变现有业务行为、不删除运行数据的前提下，整理后端测试目录，移除已经确认无运行时引用的 Prompt 和配置，并补齐 Docker 部署所需的脱敏环境模板与操作说明，使仓库结构更清晰、更适合直接部署到服务器。

## 范围

本次整理包含：

1. 将 `backend/` 根目录下的 9 个 `test_*.py` 回归脚本迁移到 `backend/tests/`。
2. 删除未被生产代码使用的 `report_prompt`、`reorder_prompt` 及其配置项。
3. 删除未被业务代码使用的 `agent_config` 和 `agent.yaml`。
4. 移除 `config.py`、`prompt_loader.py` 中仅用于手工调试的 `__main__` 代码。
5. 新增 Docker 部署环境变量示例，不复制真实密钥。
6. 更新 `README.md`，明确开发与生产 Compose 命令、模型目录、持久化目录和危险清理命令。

本次整理不包含：

- 删除或修改 RAG、笔记、回顾、认证、上传等业务逻辑。
- 删除 Chroma、MySQL、Redis、媒体或日志中的实际运行数据。
- 删除回归测试。
- 更换包管理器或删除前端锁文件。
- 大规模拆分 Service 或调整架构。
- 自动创建 Git 提交。

## 文件变更设计

### 测试目录

把以下文件原样迁移到 `backend/tests/`：

- `test_agent_note_idempotency.py`
- `test_chroma_settings.py`
- `test_factory.py`
- `test_file_handler.py`
- `test_note_auto_tag.py`
- `test_rag_query.py`
- `test_related_notes.py`
- `test_response_text.py`
- `test_review_question.py`

新增 `backend/tests/README.md`，说明这些测试既可单独用 Python 执行，也可在 Docker 后端容器内执行。迁移不改变测试断言和业务代码。

### 未使用 Prompt 和配置

删除：

- `backend/app/prompt/report_prompt.txt`
- `backend/app/prompt/reorder_prompt.txt`
- `backend/app/config/agent.yaml`

同步更新：

- 从 `backend/app/config/prompt.yaml` 删除 `report_prompt` 和 `reorder_prompt`。
- 从 `backend/app/utils/config.py` 删除 `agent_config` 的加载及调试输出。
- 更新 `backend/app/utils/prompt_loader.py` 文档，删除过时 Prompt 描述和 `__main__` 调试入口。

保留仍在生产代码中使用的 Prompt：`main_prompt`、`rag_summary_prompt`、`auto_tag_prompt`、`review_question_prompt`、`autocomplete_prompt`、`write_assistant_prompt`。

### 部署环境模板

新增：

- 根目录 `.env.example`：只放 Compose 级变量，例如 `LOCAL_MODELS_DIR`。
- `backend/.env.docker.example`：使用 Docker 服务名 `mysql`、`redis`、`django`，模型路径使用容器内 `/models`；所有密钥使用占位值。
- `DjangoUserService/.env.docker.example`：使用 Docker 服务名 `mysql`、`redis`，所有密码与 JWT 密钥使用占位值。

真实的 `.env`、`.env.docker` 继续由 `.gitignore` 和 `.dockerignore` 排除。

### 部署文档

更新 `README.md` 的 Docker 部署章节，统一使用模板复制流程：

```bash
cp .env.example .env
cp backend/.env.docker.example backend/.env.docker
cp DjangoUserService/.env.docker.example DjangoUserService/.env.docker
docker compose config
docker compose up -d --build
```

文档明确：

- 生产环境只使用 `docker-compose.yml`。
- 开发环境使用 `docker-compose.yml` 与 `docker-compose.dev.yml` 叠加。
- `backend/data`、MySQL volume、Redis volume、Django media 是持久化数据。
- `docker compose down -v` 和删除 `backend/data/chromadb` 会丢数据。
- 服务器模型目录通过 `LOCAL_MODELS_DIR` 配置。

## 验证设计

1. 搜索确认删除的 Prompt 和 `agent_config` 不再存在引用。
2. 从新路径运行后端纯工具测试。
3. 在依赖完整的 Docker 后端环境中运行文件加载及模型工厂相关测试。
4. 运行前端生产构建。
5. 运行 `docker compose config` 验证 Compose 插值和语法。
6. 检查变更文件的 IDE 诊断。

若当前执行环境无法访问 Docker API，将明确报告容器内测试未执行，不以宿主机缺少依赖的结果代替容器验证。

## 风险控制

- 删除文件前再次搜索引用，避免删掉动态加载项。
- 测试只迁移路径，不改测试内容。
- 环境模板不包含真实 API Key、数据库密码或 JWT 密钥。
- 不运行 `docker compose down -v`、不清理运行数据。
- 不创建提交，保留用户当前工作区中的所有既有改动。
