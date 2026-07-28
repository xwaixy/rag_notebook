# 后端回归测试

## 纯工具测试

从项目根目录执行：

```bash
PYTHONPATH=backend python3 backend/tests/test_chroma_settings.py
PYTHONPATH=backend python3 backend/tests/test_rag_query.py
PYTHONPATH=backend python3 backend/tests/test_related_notes.py
PYTHONPATH=backend python3 backend/tests/test_review_question.py
PYTHONPATH=backend python3 backend/tests/test_note_auto_tag.py
PYTHONPATH=backend python3 backend/tests/test_response_text.py
PYTHONPATH=backend python3 backend/tests/test_reranker_api.py
PYTHONPATH=backend python3 backend/tests/test_reranker_disabled.py
```

## 阿里云 Reranker 真实调用

先在 `backend/.env.docker` 或 `backend/.env` 中启用并配置 Qwen3-VL-Rerank，然后从项目根目录执行：

```bash
PYTHONPATH=backend UV_CACHE_DIR=backend/.uv-cache uv run --project backend \
  python backend/tests/test_reranker_live.py
```

Docker 开发模式下执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_reranker_live.py
```

该测试会产生一次小额 API 调用费用；输出只包含测试文档和相关性分数，不会输出 API Key。

## 依赖完整后端环境的测试

在 Docker 开发容器中执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_file_handler.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_factory.py
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T backend \
  uv run python tests/test_agent_note_idempotency.py
```
