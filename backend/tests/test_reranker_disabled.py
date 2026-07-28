import asyncio
import os
from app.core.background_init import _BackgroundInitManager
from app.rag.reorder_service import ReorderService


def _set_env(name: str, value: str):
    previous = os.environ.get(name)
    os.environ[name] = value
    return previous


def _restore_env(name: str, previous):
    if previous is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous


def test_background_init_skips_local_reranker_when_disabled():
    import app.rag.reorder_service as reorder_module

    previous_env = _set_env("RERANKER_ENABLED", "false")
    original_check = reorder_module.check_and_download_reranker_model
    original_constructor = reorder_module.ReorderService
    calls = []

    def record_if_called():
        calls.append("check")

    def fail_constructor():
        raise AssertionError("disabled reranker must not construct ReorderService")

    try:
        reorder_module.check_and_download_reranker_model = record_if_called
        reorder_module.ReorderService = fail_constructor
        manager = _BackgroundInitManager()

        asyncio.run(manager._init_reranker())

        assert calls == []
        assert manager.reorder_service is None
        assert manager.reranker_ready.is_set()
    finally:
        reorder_module.check_and_download_reranker_model = original_check
        reorder_module.ReorderService = original_constructor
        _restore_env("RERANKER_ENABLED", previous_env)


def test_reorder_service_preserves_order_when_reranker_disabled():
    previous_env = _set_env("RERANKER_ENABLED", "false")
    documents = ["first document", "second document"]
    service = ReorderService()

    async def fail_if_model_loaded():
        raise AssertionError("disabled reranker must not load the local model")

    service._get_model = fail_if_model_loaded

    try:
        result = asyncio.run(service.reorder_documents("query", documents))

        assert result == {
            "success": True,
            "documents": [
                {"document": "first document", "similarity": 0.0},
                {"document": "second document", "similarity": 0.0},
            ],
            "error": "",
        }
    finally:
        _restore_env("RERANKER_ENABLED", previous_env)


if __name__ == "__main__":
    test_background_init_skips_local_reranker_when_disabled()
    test_reorder_service_preserves_order_when_reranker_disabled()
