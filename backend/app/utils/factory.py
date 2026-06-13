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


def normalize_openai_proxy_env() -> None:
    """兼容部分代理软件导出的 socks:// 地址格式。"""
    proxy_keys = (
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    )
    for key in proxy_keys:
        value = os.getenv(key)
        if value and value.lower().startswith("socks://"):
            os.environ[key] = f"socks5://{value[len('socks://'):]}"


def _env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _apply_openai_compat_headers(request) -> None:
    request.headers["User-Agent"] = os.getenv("OPENAI_USER_AGENT", "curl/8.0.0")


async def _async_apply_openai_compat_headers(request) -> None:
    _apply_openai_compat_headers(request)


def create_openai_chat_model(model_name: str, streaming: bool = True) -> BaseChatModel:
    """根据项目环境变量创建 OpenAI 兼容聊天模型。"""
    import httpx
    from langchain_openai import ChatOpenAI

    normalize_openai_proxy_env()
    trust_env = _env_bool("OPENAI_TRUST_ENV", False)

    kwargs = {
        "model": model_name,
        "api_key": os.getenv("OPENAI_API_KEY"),
        "base_url": os.getenv("OPENAI_BASE_URL") or None,
        "streaming": streaming,
        "http_client": httpx.Client(
            event_hooks={"request": [_apply_openai_compat_headers]},
            trust_env=trust_env,
        ),
        "http_async_client": httpx.AsyncClient(
            event_hooks={"request": [_async_apply_openai_compat_headers]},
            trust_env=trust_env,
        ),
    }

    use_responses_api = _env_bool("OPENAI_USE_RESPONSES_API")
    if use_responses_api:
        kwargs["use_responses_api"] = True

        reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT")
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        if _env_bool("OPENAI_DISABLE_RESPONSE_STORAGE"):
            kwargs["store"] = False

    return ChatOpenAI(**kwargs)


class DashScopeEmbeddingsWrapper(Embeddings):
    """阿里云DashScope嵌入模型封装"""

    def __init__(self, model_name: str = "qwen3-embedding", api_key: str = None):
        try:
            import dashscope
            self.dashscope = dashscope
            self.dashscope.api_key = api_key or os.getenv("ALIYUN_ACCESS_KEY_SECRET")
            self.model_name = model_name
        except ImportError:
            raise ImportError("需要安装 dashscope 库: pip install dashscope")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档"""
        results = []
        for text in texts:
            resp = self.dashscope.TextEmbedding.call(
                model=self.model_name,
                input=text
            )
            if resp.status_code == 200:
                results.append(resp.output['embeddings'][0]['embedding'])
            else:
                logger.error(f"阿里云嵌入调用失败: {resp.message}")
                results.append([])
        return results

    def embed_query(self, text: str) -> list[float]:
        """嵌入单个查询"""
        resp = self.dashscope.TextEmbedding.call(
            model=self.model_name,
            input=text
        )
        if resp.status_code == 200:
            return resp.output['embeddings'][0]['embedding']
        else:
            logger.error(f"阿里云嵌入调用失败: {resp.message}")
            return []


class LocalQwenEmbeddingsWrapper(Embeddings):
    """本地 Qwen3 Embedding 模型封装"""

    def __init__(self, model_path: str, device: str | None = None):
        try:
            from sentence_transformers import SentenceTransformer

            if device == "cuda":
                try:
                    import torch

                    if not torch.cuda.is_available():
                        logger.warning("本地Qwen嵌入模型请求使用cuda，但当前环境不可用，自动降级为cpu")
                        device = "cpu"
                except ImportError:
                    logger.warning("未安装torch，无法检查cuda状态，本地Qwen嵌入模型自动降级为cpu")
                    device = "cpu"

            kwargs = {}
            if device:
                kwargs["device"] = device

            try:
                self.model = SentenceTransformer(model_path, **kwargs)
            except RuntimeError as e:
                if device == "cuda" and "out of memory" in str(e).lower():
                    logger.warning("本地Qwen嵌入模型加载到cuda时显存不足，自动降级为cpu")
                    self.model = SentenceTransformer(model_path, device="cpu")
                else:
                    raise
        except ImportError:
            raise ImportError("需要安装 sentence-transformers 库: pip install sentence-transformers")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档"""
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """嵌入单个查询"""
        return self.embed_documents([text])[0]


class BaseModelFactory(ABC):
    """基础模型工厂"""

    @abstractmethod
    def generator(self) -> Embeddings | BaseChatModel | None:
        """生成模型"""
        pass


class ChatModelFactory(BaseModelFactory):
    """聊天模型工厂 - 支持阿里云百炼、Ollama 和 OpenAI"""

    def generator(self) -> Embeddings | BaseChatModel | None:
        """根据LLM_TYPE生成对应的聊天模型"""
        llm_type = os.getenv("LLM_TYPE", "ALIYUN").upper()

        if llm_type == "OLLAMA":
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

            return create_openai_chat_model(model_name=model_name, streaming=True)

        else:
            raise ValueError(f"不支持的LLM_TYPE: {llm_type}，可选值: ALIYUN, OLLAMA, OPENAI")


class EmbedModelFactory(BaseModelFactory):
    """嵌入模型工厂 - 支持Ollama、阿里云百炼和本地Qwen"""
    def generator(self) -> Embeddings | BaseChatModel | None:
        """根据EMBED_MODEL_TYPE生成对应的嵌入模型"""
        embed_type = os.getenv("EMBED_MODEL_TYPE", "OLLAMA").upper()

        if embed_type == "OLLAMA":
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

            logger.info(f"📦 EmbedModel 使用阿里云嵌入模型: {model_name}")

            return DashScopeEmbeddingsWrapper(
                model_name=model_name,
                api_key=api_key
            )

        elif embed_type == "LOCAL_QWEN":
            model_path = os.getenv("LOCAL_EMBED_MODEL_PATH", "/home/wyl/models/Qwen3-Embedding-0.6B")
            device = os.getenv("LOCAL_EMBED_DEVICE") or None

            logger.info(f"📦 EmbedModel 使用本地Qwen嵌入模型: {model_path}, 设备: {device or 'auto'}")

            return LocalQwenEmbeddingsWrapper(
                model_path=model_path,
                device=device
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

        if vision_type in {"DISABLED", "NONE", "OFF"}:
            logger.info("🎨 VisionModel 已禁用")
            return None

        if vision_type == "OLLAMA":
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
