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
```

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
