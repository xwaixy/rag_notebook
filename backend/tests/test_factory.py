import importlib
import sys
import types


def test_aliyun_embed_factory_uses_openai_compatible_dashscope_endpoint(monkeypatch):
    calls = {}

    class FakeOpenAIEmbeddings:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

        def embed_documents(self, texts):
            calls["documents"] = texts
            return [[1.0, 2.0, 3.0]]

        def embed_query(self, text):
            calls["query"] = text
            return [1.0, 2.0, 3.0]

    fake_module = types.ModuleType("langchain_openai")
    fake_module.OpenAIEmbeddings = FakeOpenAIEmbeddings

    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)
    monkeypatch.setenv("EMBED_MODEL_TYPE", "ALIYUN")
    monkeypatch.setenv("ALIYUN_EMBED_MODEL_NAME", "text-embedding-v4")
    monkeypatch.setenv("ALIYUN_ACCESS_KEY_SECRET", "sk-test")
    monkeypatch.setenv("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

    import app.utils.factory as factory

    importlib.reload(factory)

    embedder = factory.EmbedModelFactory().generator()

    assert calls["kwargs"] == {
        "model": "text-embedding-v4",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "check_embedding_ctx_length": False,
        "api_key": "sk-test",
    }
    assert embedder.embed_documents(["hello"]) == [[1.0, 2.0, 3.0]]
    assert calls["documents"] == ["hello"]
    assert embedder.embed_query("hello") == [1.0, 2.0, 3.0]
    assert calls["query"] == "hello"


def test_vision_factory_returns_none_when_disabled(monkeypatch):
    monkeypatch.setenv("VISION_MODEL_TYPE", "DISABLED")

    import app.utils.factory as factory

    importlib.reload(factory)

    assert factory.VisionModelFactory().generator() is None


def test_create_openai_chat_model_uses_openai_env(monkeypatch):
    calls = {}

    class FakeChatOpenAI:
        def __init__(self, **kwargs):
            calls["kwargs"] = kwargs

    class FakeHttpClient:
        def __init__(self, **kwargs):
            calls["http_client_kwargs"] = kwargs

    class FakeAsyncHttpClient:
        def __init__(self, **kwargs):
            calls["http_async_client_kwargs"] = kwargs

    fake_module = types.ModuleType("langchain_openai")
    fake_module.ChatOpenAI = FakeChatOpenAI
    fake_module.OpenAIEmbeddings = object

    fake_httpx_module = types.ModuleType("httpx")
    fake_httpx_module.Client = FakeHttpClient
    fake_httpx_module.AsyncClient = FakeAsyncHttpClient

    monkeypatch.setitem(sys.modules, "langchain_openai", fake_module)
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx_module)
    monkeypatch.setenv("OPENAI_MODEL_NAME", "gpt-5.5")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.example/v1")
    monkeypatch.setenv("OPENAI_USE_RESPONSES_API", "true")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "xhigh")
    monkeypatch.setenv("OPENAI_DISABLE_RESPONSE_STORAGE", "true")
    monkeypatch.setenv("OPENAI_USER_AGENT", "curl/8.0.0")
    monkeypatch.setenv("OPENAI_TRUST_ENV", "false")

    import app.utils.factory as factory

    importlib.reload(factory)

    chat_model = factory.create_openai_chat_model(streaming=True)

    assert isinstance(chat_model, FakeChatOpenAI)
    assert calls["kwargs"] == {
        "model": "gpt-5.5",
        "api_key": "sk-openai-test",
        "base_url": "https://api.openai.example/v1",
        "streaming": True,
        "use_responses_api": True,
        "reasoning_effort": "xhigh",
        "store": False,
        "default_headers": {"User-Agent": "curl/8.0.0"},
        "http_client": calls["kwargs"]["http_client"],
        "http_async_client": calls["kwargs"]["http_async_client"],
    }
    assert isinstance(calls["kwargs"]["http_client"], FakeHttpClient)
    assert isinstance(calls["kwargs"]["http_async_client"], FakeAsyncHttpClient)
    assert calls["http_client_kwargs"] == {"trust_env": False}
    assert calls["http_async_client_kwargs"] == {"trust_env": False}
