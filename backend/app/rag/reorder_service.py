import asyncio
import os
from typing import Any

import requests
from dotenv import load_dotenv

from app.core.logger_handler import logger

# 加载环境变量
load_dotenv()


_QWEN3_VL_RERANK_PATH = "/api/v1/services/rerank/text-rerank/text-rerank"
_MAX_TEXT_DOCUMENTS = 100


def _positive_int(name: str, default: int, maximum: int | None = None) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        value = default

    value = max(1, value)
    return min(value, maximum) if maximum is not None else value


def _positive_float(name: str, default: float) -> float:
    try:
        return max(0.1, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def check_and_download_reranker_model() -> None:
    """保留原初始化入口；云端 Reranker 不需要下载模型。"""
    logger.info("✅ 重排序使用阿里云百炼 API，无需下载本地模型")


class ReorderService:
    """通过阿里云百炼 Qwen3-VL-Rerank API 对文本候选项重排序。"""

    def __init__(self):
        self.enabled = os.getenv("RERANKER_ENABLED", "false").lower() == "true"
        self.provider = os.getenv("RERANKER_PROVIDER", "ALIYUN").upper()
        self.api_key = (
            os.getenv("RERANKER_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        )
        self.model_name = os.getenv("RERANKER_MODEL_NAME", "qwen3-vl-rerank")
        self.base_url = self._resolve_base_url()
        self.top_n = _positive_int("RERANKER_TOP_N", 8)
        self.timeout = _positive_float("RERANKER_TIMEOUT", 30.0)
        self.max_documents = _positive_int(
            "RERANKER_MAX_DOCUMENTS",
            _MAX_TEXT_DOCUMENTS,
            maximum=_MAX_TEXT_DOCUMENTS,
        )
        self._model = None

    @staticmethod
    def _resolve_base_url() -> str:
        base_url = os.getenv("RERANKER_BASE_URL", "").strip()
        if base_url:
            return base_url.rstrip("/")

        workspace_id = os.getenv("RERANKER_WORKSPACE_ID", "").strip()
        if not workspace_id:
            return ""

        region = os.getenv("RERANKER_REGION", "cn-beijing").strip() or "cn-beijing"
        return f"https://{workspace_id}.{region}.maas.aliyuncs.com{_QWEN3_VL_RERANK_PATH}"

    def _configuration_error(self) -> str:
        if self.provider != "ALIYUN":
            return f"不支持的 RERANKER_PROVIDER: {self.provider}"
        if not self.api_key:
            return "未配置 RERANKER_API_KEY、DASHSCOPE_API_KEY 或 ALIYUN_ACCESS_KEY_SECRET"
        if not self.base_url:
            return "未配置 RERANKER_BASE_URL 或 RERANKER_WORKSPACE_ID"
        return ""

    def _request_rerank(self, query: str, documents: list[str]) -> list[dict[str, Any]]:
        response = requests.post(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self.model_name,
                "input": {
                    "query": {"text": query},
                    "documents": [{"text": document} for document in documents],
                },
                "parameters": {
                    "return_documents": False,
                    "top_n": min(self.top_n, len(documents)),
                },
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        body = response.json()
        results = body.get("output", {}).get("results")
        if not isinstance(results, list):
            request_id = body.get("request_id", "unknown")
            raise ValueError(f"阿里云 Reranker 响应缺少 output.results，request_id={request_id}")

        ranked_documents: list[dict[str, Any]] = []
        seen_indices: set[int] = set()
        for item in results:
            index = item.get("index") if isinstance(item, dict) else None
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(documents):
                raise ValueError(f"阿里云 Reranker 返回无效文档索引: {index}")
            if index in seen_indices:
                continue

            try:
                score = float(item.get("relevance_score", 0.0))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"阿里云 Reranker 返回无效相关性分数: {item.get('relevance_score')}") from exc

            seen_indices.add(index)
            ranked_documents.append({"document": documents[index], "similarity": score})

        if documents and not ranked_documents:
            raise ValueError("阿里云 Reranker 未返回任何有效结果")
        return ranked_documents

    async def reorder_documents(self, query: str, documents: list[str], thinking_callback=None) -> dict[str, Any]:
        """
        对文档进行重排序
        :param query: 查询语句
        :param documents: 文档列表
        :param thinking_callback: 思考过程回调函数
        :return: 包含重排序结果的字典，格式为：
                 {"success": bool, "documents": List[Dict], "error": str}
        """
        if not documents:
            return {
                "success": True,
                "documents": [],
                "error": "",
            }

        if not self.enabled:
            logger.info("【重排序服务】重排序已禁用，保留检索原始顺序")
            return {
                "success": True,
                "documents": [{"document": doc, "similarity": 0.0} for doc in documents],
                "error": "",
            }

        configuration_error = self._configuration_error()
        if configuration_error:
            logger.error(f"【重排序服务】配置错误: {configuration_error}")
            return {"success": False, "documents": [], "error": configuration_error}

        candidates = documents[: self.max_documents]
        if len(candidates) < len(documents):
            logger.warning(
                f"【重排序服务】候选文档数 {len(documents)} 超过限制，仅发送前 {len(candidates)} 条"
            )

        if thinking_callback:
            await thinking_callback(
                {
                    "type": "thinking",
                    "stage": "reorder",
                    "content": f"正在调用 {self.model_name} 对 {len(candidates)} 个文档进行重排序",
                }
            )

        try:
            ranked_documents = await asyncio.to_thread(self._request_rerank, query, candidates)
            logger.info(
                f"【重排序服务】{self.model_name} 重排序完成，返回 {len(ranked_documents)} 个文档"
            )
            return {"success": True, "documents": ranked_documents, "error": ""}
        except Exception as e:
            error_msg = str(e)
            logger.error(f"【重排序服务】阿里云 API 调用失败: {error_msg}")
            return {
                "success": False,
                "documents": [],
                "error": error_msg,
            }

    @staticmethod
    async def format_reorder_result(sorted_docs: list[dict]) -> str:
        """
        格式化重排序结果
        :param sorted_docs: 重排序后的文档列表
        :return: 格式化后的字符串
        """
        formatted_result = "重排序后的文档列表：\n"
        for i, doc in enumerate(sorted_docs, 1):
            formatted_result += f"{i}. 相似度: {doc.get('similarity', 0):.4f}\n"
            formatted_result += f"   内容: {doc.get('document', '')}\n\n"
        return formatted_result


# 全局重排序服务实例
reorder_service = ReorderService()
