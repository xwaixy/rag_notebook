import asyncio
import os
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import requests

from app.rag.reorder_service import ReorderService


@contextmanager
def _environment(values: dict[str, str | None]) -> Iterator[None]:
    previous = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class _FakeResponse:
    def __init__(self, body: dict[str, Any], error: Exception | None = None):
        self._body = body
        self._error = error

    def raise_for_status(self) -> None:
        if self._error:
            raise self._error

    def json(self) -> dict[str, Any]:
        return self._body


def _enabled_environment() -> dict[str, str | None]:
    return {
        "RERANKER_ENABLED": "true",
        "RERANKER_PROVIDER": "ALIYUN",
        "RERANKER_API_KEY": "test-api-key",
        "DASHSCOPE_API_KEY": None,
        "ALIYUN_ACCESS_KEY_SECRET": None,
        "RERANKER_BASE_URL": "https://example.com/api/v1/services/rerank/text-rerank/text-rerank",
        "RERANKER_WORKSPACE_ID": None,
        "RERANKER_MODEL_NAME": "qwen3-vl-rerank",
        "RERANKER_TOP_N": "2",
        "RERANKER_TIMEOUT": "12.5",
        "RERANKER_MAX_DOCUMENTS": "100",
    }


def test_qwen3_vl_rerank_request_and_response_mapping():
    import app.rag.reorder_service as reorder_module

    captured: dict[str, Any] = {}
    original_post = reorder_module.requests.post

    def fake_post(url: str, **kwargs: Any) -> _FakeResponse:
        captured["url"] = url
        captured.update(kwargs)
        return _FakeResponse(
            {
                "output": {
                    "results": [
                        {"index": 2, "relevance_score": 0.97},
                        {"index": 0, "relevance_score": 0.81},
                    ]
                },
                "request_id": "test-request-id",
            }
        )

    try:
        reorder_module.requests.post = fake_post
        with _environment(_enabled_environment()):
            service = ReorderService()
            result = asyncio.run(service.reorder_documents("如何使用 RAG？", ["文档一", "文档二", "文档三"]))

        assert result == {
            "success": True,
            "documents": [
                {"document": "文档三", "similarity": 0.97},
                {"document": "文档一", "similarity": 0.81},
            ],
            "error": "",
        }
        assert captured["url"] == "https://example.com/api/v1/services/rerank/text-rerank/text-rerank"
        assert captured["headers"] == {
            "Authorization": "Bearer test-api-key",
            "Content-Type": "application/json",
        }
        assert captured["json"] == {
            "model": "qwen3-vl-rerank",
            "input": {
                "query": {"text": "如何使用 RAG？"},
                "documents": [{"text": "文档一"}, {"text": "文档二"}, {"text": "文档三"}],
            },
            "parameters": {"return_documents": False, "top_n": 2},
        }
        assert captured["timeout"] == 12.5
    finally:
        reorder_module.requests.post = original_post


def test_workspace_id_builds_official_endpoint():
    values = _enabled_environment()
    values.update(
        {
            "RERANKER_BASE_URL": None,
            "RERANKER_WORKSPACE_ID": "workspace-123",
            "RERANKER_REGION": "cn-beijing",
        }
    )

    with _environment(values):
        service = ReorderService()

    assert service.base_url == (
        "https://workspace-123.cn-beijing.maas.aliyuncs.com"
        "/api/v1/services/rerank/text-rerank/text-rerank"
    )


def test_missing_api_configuration_fails_without_network_call():
    values = _enabled_environment()
    values.update(
        {
            "RERANKER_API_KEY": None,
            "DASHSCOPE_API_KEY": None,
            "ALIYUN_ACCESS_KEY_SECRET": None,
            "RERANKER_BASE_URL": None,
            "RERANKER_WORKSPACE_ID": None,
        }
    )

    with _environment(values):
        result = asyncio.run(ReorderService().reorder_documents("query", ["document"]))

    assert result["success"] is False
    assert result["documents"] == []
    assert "API_KEY" in result["error"]


def test_http_error_returns_failure_for_caller_fallback():
    import app.rag.reorder_service as reorder_module

    original_post = reorder_module.requests.post

    def fake_post(*args: Any, **kwargs: Any) -> _FakeResponse:
        return _FakeResponse({}, requests.HTTPError("401 Client Error"))

    try:
        reorder_module.requests.post = fake_post
        with _environment(_enabled_environment()):
            result = asyncio.run(ReorderService().reorder_documents("query", ["document"]))

        assert result == {
            "success": False,
            "documents": [],
            "error": "401 Client Error",
        }
    finally:
        reorder_module.requests.post = original_post


if __name__ == "__main__":
    test_qwen3_vl_rerank_request_and_response_mapping()
    test_workspace_id_builds_official_endpoint()
    test_missing_api_configuration_fails_without_network_call()
    test_http_error_returns_failure_for_caller_fallback()
