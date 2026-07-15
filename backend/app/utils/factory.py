import os
from abc import ABC, abstractmethod

from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.logger_handler import logger

# 加载环境变量
load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """读取布尔环境变量，兼容 true/1/yes/on。"""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class LocalQwenEmbeddingsWrapper(Embeddings):
    """本地 Qwen3 Embedding 模型封装"""

    def __init__(self, model_path: str, device: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer

            kwargs = {}
            if device:
                kwargs["device"] = device

            self.model = SentenceTransformer(model_path, **kwargs)
        except ImportError:
            raise ImportError("需要安装 sentence-transformers: pip install sentence-transformers")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class DashScopeEmbeddingsWrapper(Embeddings):
    """阿里云 DashScope OpenAI 兼容 Embedding 模型封装"""

    def __init__(self, model_name: str, api_key: str | None = None, base_url: str | None = None):
        try:
            from langchain_openai import OpenAIEmbeddings
        except ImportError as exc:
            raise ImportError("需要安装 langchain-openai: pip install langchain-openai") from exc

        kwargs = {
            "model": model_name,
            "base_url": base_url or os.getenv("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "check_embedding_ctx_length": False,
        }
        if api_key:
            kwargs["api_key"] = api_key

        self.model = OpenAIEmbeddings(**kwargs)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.model.embed_query(text)


class BaseModelFactory(ABC):
    """基础模型工厂"""

    @abstractmethod
    def generator(self) -> Embeddings | BaseChatModel | None:
        """生成模型"""
        pass


def create_openai_chat_model(
        model_name: str | None = None,
        streaming: bool = True,
        **kwargs,
) -> BaseChatModel:
    """创建 OpenAI 兼容聊天模型，供后台初始化和 Agent 复用。"""
    try:
        from langchain_openai import ChatOpenAI
    except ImportError as exc:
        raise ImportError("需要安装 langchain-openai: pip install langchain-openai") from exc

    resolved_model_name = model_name or os.getenv("OPENAI_MODEL_NAME", "gpt-5.5")
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    use_responses_api = _env_bool("OPENAI_USE_RESPONSES_API", False)
    reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT") or None
    disable_response_storage = _env_bool("OPENAI_DISABLE_RESPONSE_STORAGE", False)
    user_agent = os.getenv("OPENAI_USER_AGENT") or None
    trust_env = _env_bool("OPENAI_TRUST_ENV", True)

    model_kwargs = {
        "model": resolved_model_name,
        "api_key": api_key,
        "base_url": base_url,
        "streaming": streaming,
        "use_responses_api": use_responses_api,
    }
    if reasoning_effort:
        model_kwargs["reasoning_effort"] = reasoning_effort
    if disable_response_storage:
        model_kwargs["store"] = False
    if user_agent:
        model_kwargs["default_headers"] = {"User-Agent": user_agent}
    if not trust_env and "http_client" not in kwargs and "http_async_client" not in kwargs:
        import httpx

        model_kwargs["http_client"] = httpx.Client(trust_env=False)
        model_kwargs["http_async_client"] = httpx.AsyncClient(trust_env=False)
    model_kwargs.update(kwargs)

    return ChatOpenAI(**model_kwargs)


class ChatModelFactory(BaseModelFactory):
    """聊天模型工厂 - 支持阿里云百炼和Ollama"""

    def generator(self) -> Embeddings | BaseChatModel | None:
        """根据LLM_TYPE生成对应的聊天模型"""
        llm_type = os.getenv("LLM_TYPE", "ALIYUN").upper()

        if llm_type == "OLLAMA":
            from langchain_ollama import ChatOllama

            model_name = os.getenv("OLLAMA_MODEL_NAME", os.getenv("OLLAMA_CHAT_MODEL_NAME", "qwen3:7b"))
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

            logger.info(f"📦 ChatModel 使用Ollama模型: {model_name}, 地址: {base_url}")

            return ChatOllama(
                model=model_name,
                base_url=base_url,
                streaming=True,
                top_p=0.7,
            )

        elif llm_type == "ALIYUN":
            model_name = os.getenv("ALIYUN_MODEL_NAME", os.getenv("CHAT_MODEL_NAME", "qwen3-max"))
            api_key = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
            base_url = os.getenv("ALIYUN_BASE_URL")

            logger.info(f"📦 ChatModel 使用阿里云百炼模型: {model_name}")

            return ChatTongyi(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                streaming=True,
                top_p=0.7,
            )
        
        elif llm_type == "OPENAI":
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-5.5")

            logger.info(f"📦 ChatModel 使用OpenAI模型: {model_name}")

            return create_openai_chat_model(
                model_name=model_name,
                streaming=True,
            )

        else:
            raise ValueError(f"不支持的LLM_TYPE: {llm_type}，可选值: ALIYUN, OLLAMA, OPENAI")


class EmbedModelFactory(BaseModelFactory):
    """嵌入模型工厂 - 支持Ollama和阿里云百炼"""
    def generator(self) -> Embeddings | BaseChatModel | None:
        """根据EMBED_MODEL_TYPE生成对应的嵌入模型"""
        embed_type = os.getenv("EMBED_MODEL_TYPE", "OLLAMA").upper()

        if embed_type == "OLLAMA":
            from langchain_ollama import OllamaEmbeddings

            model_name = os.getenv("TEXT_EMBEDDING_MODEL_NAME", "qwen3-embedding:0.6b")
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

            logger.info(f"📦 EmbedModel 使用Ollama嵌入模型: {model_name}, 地址: {base_url}")

            return OllamaEmbeddings(
                model=model_name,
                base_url=base_url
            )

        elif embed_type == "ALIYUN":
            model_name = os.getenv("ALIYUN_EMBED_MODEL_NAME", "qwen3-embedding")
            api_key = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
            base_url = os.getenv("ALIYUN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

            logger.info(f"📦 EmbedModel 使用阿里云嵌入模型: {model_name}")

            return DashScopeEmbeddingsWrapper(
                model_name=model_name,
                api_key=api_key,
                base_url=base_url,
            )

        elif embed_type == "LOCAL_QWEN":
            model_path = os.getenv("LOCAL_EMBED_MODEL_PATH", "/home/wyl/models/Qwen3-Embedding-0.6B")
            device = os.getenv("LOCAL_EMBED_DEVICE") or None

            logger.info(f"📦 EmbedModel 使用本地Qwen嵌入模型: {model_path}, 设备: {device or 'auto'}")

            return LocalQwenEmbeddingsWrapper(
                model_path=model_path,
                device=device,
            )

        else:
            raise ValueError(f"不支持的EMBED_MODEL_TYPE: {embed_type}，可选值: OLLAMA, ALIYUN, LOCAL_QWEN")


class VisionModelFactory(BaseModelFactory):
    """
    视觉模型工厂 - 支持阿里云百炼和Ollama多模态模型。
    用于 PDF 多模态加载场景：将 PDF 页面渲染为图片，然后调用视觉模型进行图片理解，
    提取纯文本提取难以获取的图表、表格、流程图等视觉信息。

    之所以单独为一个视觉模型工厂而不是复用 ChatModelFactory，是因为：
    1. ChatModel 使用 streaming=True（流式输出），而视觉模型只能用 streaming=False
       （图片理解不适合流式）
    2. 视觉模型可能有独立的模型配置（如 VISION_OLLAMA_MODEL_NAME 区分于 OLLAMA_MODEL_NAME）
    3. 部分用户可能希望视觉模型使用更大的参数量或专门的多模态模型（如 qwen-vl 系列）
    """

    def generator(self) -> BaseChatModel | None:
        """根据VISION_MODEL_TYPE生成对应的视觉模型"""
        # 未设置 VISION_MODEL_TYPE 时，默认跟随 LLM_TYPE（保持向后兼容）
        vision_type = os.getenv("VISION_MODEL_TYPE", "").upper() or os.getenv("LLM_TYPE", "ALIYUN").upper()

        if vision_type in {"DISABLED", "NONE", "OFF", "FALSE"}:
            logger.info("🎨 VisionModel 已禁用")
            return None

        if vision_type == "OLLAMA":
            from langchain_ollama import ChatOllama

            model_name = os.getenv("VISION_OLLAMA_MODEL_NAME") or os.getenv("OLLAMA_MODEL_NAME") or "qwen-vl:7b"
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

            logger.info(f"🎨 VisionModel 使用Ollama多模态模型: {model_name}, 地址: {base_url}")

            return ChatOllama(
                model=model_name,
                base_url=base_url,
                # 视觉模型禁用 streaming，因为图片理解需要在完整的上下文上做推理
                streaming=False,
                top_p=0.7,
            )

        elif vision_type == "ALIYUN":
            model_name = os.getenv("VISION_CHAT_MODEL_NAME") or os.getenv("CHAT_MODEL_NAME") or "qwen3-max"
            api_key = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
            base_url = os.getenv("ALIYUN_BASE_URL")

            logger.info(f"🎨 VisionModel 使用阿里云百炼多模态模型: {model_name}")

            return ChatTongyi(
                model=model_name,
                api_key=api_key,
                base_url=base_url,
                streaming=False,
                top_p=0.7,
            )

        else:
            raise ValueError(f"不支持的VISION_MODEL_TYPE: {vision_type}，可选值: ALIYUN, OLLAMA, DISABLED")


class RerankerModelFactory(BaseModelFactory):
    """重排序模型工厂 - 已废弃，使用CrossEncoder模型"""
    def generator(self) -> Embeddings | BaseChatModel | None:
        """生成模型"""
        return None


chat_model = None
embed_model = None
reranker_model = None
vision_model = None
