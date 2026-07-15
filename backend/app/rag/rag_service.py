import asyncio
import os

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langsmith import traceable

from app.core.background_init import init_manager
from app.core.logger_handler import logger
from app.rag.vector_store import VectorStoreService
from app.utils.prompt_loader import load_prompt
from app.utils.rag_query import (
    document_relevance_components,
    document_relevance_score,
    filter_documents_by_relevance,
    rank_documents_by_query,
)
from app.utils.related_notes import distance_to_similarity


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


class RagService:
    def __init__(self, user_id: str = None, thinking_callback=None):
        self.vector_store = VectorStoreService()
        self.note_service = init_manager.note_service
        self.retriever = None
        self.user_id = user_id
        self.prompt_text = load_prompt(prompt_type="rag_summary_prompt")
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.chat_model = init_manager.chat_model
        self.chain = self._init_chain()
        self.hyde_prompt_template = PromptTemplate.from_template(
            "基于用户问题，生成用于向量检索的简短检索文本。\n"
            "要求：\n"
            "1. 不要正式回答问题，不要编造用户身份、账号、权限或背景。\n"
            "2. 只写可能出现在用户资料、笔记或知识库里的关键词和短句。\n"
            "3. 最多80个中文字符，逗号分隔。\n\n"
            "用户问题：{query}\n\n"
            "检索文本："
        )
        self.thinking_callback = thinking_callback
        self.hyde_timeout = _env_float("HYDE_TIMEOUT_SECONDS", 8.0)
        self.hyde_max_chars = _env_int("HYDE_MAX_CHARS", 160)
        self.original_vector_k = _env_int("RAG_ORIGINAL_VECTOR_K", 10)
        self.note_k = _env_int("RAG_NOTE_K", 5)
        self.hyde_k = _env_int("RAG_HYDE_K", 10)
        self.summary_mode = os.getenv("RAG_SUMMARY_MODE", "fast").lower()
        self.summary_doc_count = _env_int("RAG_SUMMARY_DOC_COUNT", 3)
        self.summary_doc_chars = _env_int("RAG_SUMMARY_DOC_CHARS", 700)
        self.summary_timeout = _env_float("RAG_SUMMARY_TIMEOUT_SECONDS", 12.0)

    async def initialize_retriever(self, query: str = None):
        """
        初始化检索器
        :param query: 查询语句，用于动态调整权重
        """
        if self.retriever is None:
            # 获取动态权重信息
            weights = await self.vector_store.get_dynamic_weights(query)

            if self.thinking_callback:
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "retrieval",
                    "content": f"初始化检索器（向量权重: {weights[0]:.1f}, BM25权重: {weights[1]:.1f}）",
                    "details": {
                        "vector_weight": weights[0],
                        "bm25_weight": weights[1]
                    }
                })

            self.retriever = await self.vector_store.get_retriever(query, self.user_id)


    def _init_chain(self):
        """初始化链"""
        chain = (
                self.prompt_template
                | self.chat_model
                | StrOutputParser()
        )
        return chain

    @traceable
    async def generate_hypothetical_document(self, query: str) -> str:
        """
        使用HyDE技术生成假设性文档
        :param query: 用户查询
        :return: 假设性文档内容
        """
        try:
            hyde_chain = (
                self.hyde_prompt_template
                | self.chat_model
                | StrOutputParser()
            )
            hypothetical_doc = await asyncio.wait_for(
                hyde_chain.ainvoke({"query": query}),
                timeout=self.hyde_timeout
            )
            hypothetical_doc = " ".join(hypothetical_doc.split())
            if len(hypothetical_doc) > self.hyde_max_chars:
                hypothetical_doc = hypothetical_doc[:self.hyde_max_chars]
            logger.info(f"【HyDE】生成的假设性文档:\n{hypothetical_doc}")
            return hypothetical_doc
        except TimeoutError:
            logger.warning("【HyDE】生成假设性文档超时，回退为原始问题")
            return query
        except Exception as e:
            logger.error(f"【HyDE】生成假设性文档失败: {e}")
            return query

    @traceable
    async def retrieve_document(self, query: str) -> list:
        """使用HyDE技术 从向量数据库里检索文档"""
        if not self.user_id:
            logger.warning("【HyDE】user_id为空，不进行任何检索")
            return []

        try:
            # 确保检索器已初始化，传递query参数
            if self.retriever is None:
                await self.initialize_retriever(query)

            # 使用HyDE技术生成假设性文档
            logger.info(f"【HyDE】开始处理查询: {query}")

            if self.thinking_callback:
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "hyde",
                    "content": f"正在基于查询「{query}」生成简短检索文本..."
                })

            hypothetical_doc = await self.generate_hypothetical_document(query)

            if self.thinking_callback:
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "hyde",
                    "content": "HyDE 检索文本生成完成",
                    "details": {
                        "hypothetical_doc_preview": hypothetical_doc[:200] + "..." if len(hypothetical_doc) > 200 else hypothetical_doc
                    }
                })

            # 同时使用原始问题和假设性文档检索。
            # 只用 HyDE 容易在假设回答猜错时发生查询漂移，例如把“喜欢什么动物”猜成“喜欢猫”，
            # 从而错过原始问题能直接命中的用户资料。
            logger.info("【HyDE】使用原始问题进行检索")
            original_vector_results = await asyncio.to_thread(
                self.vector_store.vectors_store.similarity_search_with_score,
                query, k=self.original_vector_k,
                filter={"user_id": self.user_id}
            )
            original_documents = (await self.retriever.ainvoke(query))[:self.original_vector_k]

            original_note_docs = []
            try:
                original_note_results = await asyncio.to_thread(
                    self.note_service.notes_store.similarity_search_with_score,
                    query, k=self.note_k,
                    filter={"user_id": self.user_id}
                )
                for doc, score in original_note_results:
                    doc.metadata["vector_distance"] = score
                    doc.metadata["vector_similarity"] = distance_to_similarity(score)
                    original_note_docs.append(doc)
            except Exception as e:
                logger.error(f"【RAG】使用原始问题检索笔记失败: {e}")

            original_vector_documents = []
            for doc, score in original_vector_results:
                doc.metadata["source_type"] = "knowledge_base"
                doc.metadata["retrieval_source"] = "original_vector_query"
                doc.metadata["vector_distance"] = score
                doc.metadata["vector_similarity"] = distance_to_similarity(score)
                original_vector_documents.append(doc)
            for doc in original_documents:
                doc.metadata["source_type"] = "knowledge_base"
                doc.metadata["retrieval_source"] = "original_query"
            for doc in original_note_docs:
                doc.metadata["source_type"] = "note"
                doc.metadata["retrieval_source"] = "original_query"

            original_all_documents = original_vector_documents + original_documents + original_note_docs

            # 使用假设性文档进行检索
            logger.info("【HyDE】使用假设性文档进行检索")

            if self.thinking_callback:
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "retrieval",
                    "content": "正在向量数据库中检索相关文档..."
                })

            hyde_vector_results = await asyncio.to_thread(
                self.vector_store.vectors_store.similarity_search_with_score,
                hypothetical_doc,
                k=self.hyde_k,
                filter={"user_id": self.user_id}
            )
            hyde_vector_documents = []
            documents = (await self.retriever.ainvoke(hypothetical_doc))[:self.hyde_k]

            # 同时检索笔记库
            note_docs = []
            try:
                note_results = await asyncio.to_thread(
                    self.note_service.notes_store.similarity_search_with_score,
                    hypothetical_doc, k=self.note_k,
                    filter={"user_id": self.user_id}
                )
                for doc, score in note_results:
                    doc.metadata["vector_distance"] = score
                    doc.metadata["vector_similarity"] = distance_to_similarity(score)
                    note_docs.append(doc)
            except Exception as e:
                logger.error(f"【RAG】检索笔记失败: {e}")

            # 标记来源并合并（笔记在前，知识库在后）
            for doc, score in hyde_vector_results:
                doc.metadata["source_type"] = "knowledge_base"
                doc.metadata["retrieval_source"] = "hyde_vector_query"
                doc.metadata["vector_distance"] = score
                doc.metadata["vector_similarity"] = distance_to_similarity(score)
                hyde_vector_documents.append(doc)
            for doc in documents:
                doc.metadata["source_type"] = "knowledge_base"
                doc.metadata["retrieval_source"] = "hyde"
            for doc in note_docs:
                doc.metadata["source_type"] = "note"
                doc.metadata["retrieval_source"] = "hyde"

            # 原始问题命中的文档优先，HyDE 结果补充召回；同一文档重复命中时保留更高相关分。
            best_documents = {}
            for doc in original_all_documents + note_docs + hyde_vector_documents + documents:
                key = (
                    doc.metadata.get("source_type"),
                    doc.metadata.get("original_filename") or doc.metadata.get("title") or doc.metadata.get("source"),
                    doc.page_content[:200],
                )
                retrieval_source = doc.metadata.get("retrieval_source")
                existing = best_documents.get(key)
                if existing is None:
                    doc.metadata["retrieval_sources"] = [retrieval_source] if retrieval_source else []
                    best_documents[key] = doc
                    continue

                sources = set(existing.metadata.get("retrieval_sources") or [])
                if existing.metadata.get("retrieval_source"):
                    sources.add(existing.metadata["retrieval_source"])
                if retrieval_source:
                    sources.add(retrieval_source)

                existing_score = document_relevance_score(query, existing, auxiliary_query=hypothetical_doc)
                candidate_score = document_relevance_score(query, doc, auxiliary_query=hypothetical_doc)
                chosen = doc if candidate_score > existing_score else existing
                chosen.metadata["retrieval_sources"] = sorted(sources)
                best_documents[key] = chosen

            all_documents = list(best_documents.values())

            filtered_documents = filter_documents_by_relevance(query, all_documents, auxiliary_query=hypothetical_doc)
            ranked_documents = rank_documents_by_query(query, filtered_documents, auxiliary_query=hypothetical_doc)

            logger.info(
                f"【HyDE】原始问题检索到 {len(original_documents)} 个知识库文档, {len(original_note_docs)} 个笔记文档；"
                f"假设性文档检索到 {len(documents)} 个知识库文档, {len(note_docs)} 个笔记文档；"
                f"合并后 {len(all_documents)} 个文档，规则过滤后 {len(ranked_documents)} 个文档"
            )

            if self.thinking_callback:
                doc_previews = []
                for i, doc in enumerate(ranked_documents, 1):
                    preview = doc.page_content[:150] + "..." if len(doc.page_content) > 150 else doc.page_content
                    if doc.metadata.get("source_type") == "note":
                        source = f"笔记《{doc.metadata.get('title', '无标题')}》"
                    else:
                        source = doc.metadata.get("original_filename", doc.metadata.get("source", "unknown"))
                    score_parts = document_relevance_components(query, doc, auxiliary_query=hypothetical_doc)
                    final_score = score_parts["final_score"]
                    doc_previews.append({
                        "index": i,
                        "preview": preview,
                        "source": source,
                        "vector_distance": doc.metadata.get("vector_distance"),
                        "vector_similarity": doc.metadata.get("vector_similarity"),
                        "vector_score": score_parts["vector_score"],
                        "lexical_score": score_parts["lexical_score"],
                        "metadata_score": score_parts["metadata_score"],
                        "literal_score": score_parts["literal_score"],
                        "final_score": final_score,
                        "score": final_score,
                        "retrieval_source": doc.metadata.get("retrieval_source"),
                        "retrieval_sources": doc.metadata.get("retrieval_sources"),
                    })
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "retrieval",
                    "content": f"检索到 {len(ranked_documents)} 个通过相关性过滤的文档",
                    "details": {
                        "documents": doc_previews
                    }
                })

            return ranked_documents
        except Exception as e:
            logger.error(f"【HyDE】检索文档失败: {e}")
            return []

    @traceable
    async def reorder_documents(self, query: str, documents: list) -> list:
        """
        对文档进行重排序
        :param query: 查询语句
        :param documents: 文档列表
        :return: 重排序后的文档列表
        """
        if self.thinking_callback:
            await self.thinking_callback({
                "type": "thinking",
                "stage": "reorder",
                "content": f"正在对 {len(documents)} 个文档进行重排序..."
            })

        if os.getenv("RERANKER_ENABLED", "false").lower() != "true":
            logger.info("【RAG】重排序已禁用，保留检索原始顺序")
            if self.thinking_callback:
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "reorder",
                    "content": "重排序已禁用，保留检索原始顺序"
                })
            return documents

        result = await init_manager.reorder_service.reorder_documents(query, documents, thinking_callback=self.thinking_callback)
        if result["success"]:
            # 提取重排序后的文档内容
            reordered_documents = [doc.get("document", "") for doc in result["documents"]]
            logger.info(f"【RAG】文档重排序成功，返回 {len(reordered_documents)} 个文档")

            if self.thinking_callback:
                score_details = []
                for i, doc in enumerate(result["documents"], 1):
                    score_details.append({
                        "rank": i,
                        "score": round(doc.get("similarity", 0), 4),
                        "preview": doc.get("document", "")[:100] + "..." if len(doc.get("document", "")) > 100 else doc.get("document", "")
                    })
                await self.thinking_callback({
                    "type": "thinking",
                    "stage": "reorder",
                    "content": f"重排序完成，返回 {len(reordered_documents)} 个文档",
                    "details": {
                        "scores": score_details
                    }
                })

            return reordered_documents
        else:
            logger.warning(f"【RAG】重排序失败: {result['error']}")
            return documents

    @traceable
    async def get_documents_and_summary(self, query: str) -> dict:
        """
        获取文档列表和摘要
        :param query: 查询语句
        :return: 包含文档列表和摘要的字典
        """
        if not self.user_id:
            logger.warning("【RAG】user_id为空，不返回任何文档")
            return {
                "documents": [],
                "summary": "抱歉，我没有找到相关的信息。"
            }

        try:
            documents = await self.retrieve_document(query)

            # 提取文档内容列表，附上来源标记供 LLM 引用
            def _format_doc(doc):
                if doc.metadata.get("source_type") == "note":
                    title = doc.metadata.get("title", "无标题")
                    return f"[来源：笔记《{title}》]\n{doc.page_content}"
                else:
                    filename = doc.metadata.get("original_filename", "知识库文档")
                    return f"[来源：知识库《{filename}》]\n{doc.page_content}"

            document_contents = [_format_doc(doc) for doc in documents]

            # 对文档进行重排序
            reordered_documents = await self.reorder_documents(query, document_contents)

            # 如果没有检索到文档
            if not reordered_documents:
                return {
                    "documents": [],
                    "summary": "抱歉，我没有找到相关的信息。"
                }

            def build_fast_summary(docs: list[str]) -> str:
                selected_docs = docs[:self.summary_doc_count]
                snippets = []
                for i, doc in enumerate(selected_docs, 1):
                    compact = " ".join(str(doc).split())
                    if len(compact) > self.summary_doc_chars:
                        compact = compact[:self.summary_doc_chars] + "..."
                    snippets.append(f"{i}. {compact}")
                return (
                    "已检索到以下相关资料片段，请结合这些资料回答用户问题：\n"
                    + "\n".join(snippets)
                )

            if self.summary_mode in {"fast", "none", "off", "disabled"}:
                logger.info("【RAG】使用快速摘要模式，跳过LLM分批总结")
                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "summarize",
                        "content": f"已启用快速模式，直接使用前 {min(self.summary_doc_count, len(reordered_documents))} 个相关资料片段"
                    })
                return {
                    "documents": reordered_documents,
                    "summary": build_fast_summary(reordered_documents)
                }

            # 使用分批总结策略
            try:
                # 对每个文档单独总结（使用线程池并发处理）
                individual_summaries = []
                max_documents = self.summary_doc_count

                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "summarize",
                        "content": f"正在对前 {min(max_documents, len(reordered_documents))} 个最相关文档进行总结..."
                    })

                # 定义单个文档总结函数
                async def summarize_document(i, doc):
                    logger.info(f"【RAG】正在总结第{i}个文档")
                    if self.thinking_callback:
                        await self.thinking_callback({
                            "type": "thinking",
                            "stage": "summarize",
                            "content": f"正在总结第 {i} 个文档..."
                        })
                    # 为单个文档构建上下文
                    single_context = f"【参考资料{i}】:{doc}\n"
                    # 生成单个文档的摘要
                    import time
                    start_time = time.time()
                    single_summary = await asyncio.wait_for(
                        self.chain.ainvoke({"input": query, "context": single_context}),
                        timeout=self.summary_timeout
                    )
                    end_time = time.time()
                    logger.info(f"【RAG】第{i}个文档总结耗时: {end_time - start_time:.2f}秒")
                    return single_summary

                # 使用线程池并发处理文档总结
                tasks = []
                for i, doc in enumerate(reordered_documents[:max_documents], 1):
                    tasks.append(summarize_document(i, doc))

                # 并发执行所有总结任务，最多5个线程
                import time
                start_time = time.time()
                individual_summaries = await asyncio.gather(*tasks)
                end_time = time.time()
                logger.info(f"【RAG】所有文档总结完成，总耗时: {end_time - start_time:.2f}秒")

                # 如果只有一个文档，直接返回其摘要
                if len(individual_summaries) == 1:
                    logger.info("【RAG】生成摘要成功")
                    return {
                        "documents": reordered_documents,
                        "summary": individual_summaries[0]
                    }

                # 合并多个文档的摘要，生成最终总结
                combined_context = "以下是多个文档的摘要，请综合这些信息生成最终的回答：\n\n"
                for i, summary in enumerate(individual_summaries, 1):
                    combined_context += f"【文档{i}摘要】:{summary}\n\n"

                logger.info("【RAG】合并摘要完成，开始生成最终总结")

                if self.thinking_callback:
                    await self.thinking_callback({
                        "type": "thinking",
                        "stage": "summarize",
                        "content": "正在综合多个文档生成最终回答..."
                    })

                # 生成最终总结
                final_summary = await asyncio.wait_for(
                    self.chain.ainvoke({"input": query, "context": combined_context}),
                    timeout=self.summary_timeout
                )

                logger.info("【RAG】生成摘要成功")
                return {
                    "documents": reordered_documents,
                    "summary": final_summary
                }
            except TimeoutError:
                logger.error("【RAG】生成摘要超时")
                if individual_summaries:
                    fallback_summary = "\n".join(summary for summary in individual_summaries if summary).strip()
                    if fallback_summary:
                        logger.info("【RAG】使用已生成的单文档摘要作为超时兜底结果")
                        return {
                            "documents": reordered_documents,
                            "summary": fallback_summary
                        }
                return {
                    "documents": reordered_documents,
                    "summary": "抱歉，生成摘要超时，请稍后再试。"
                }
        except Exception as e:
            logger.error(f"【RAG】生成摘要失败: {e}", exc_info=True)
            return {
                "documents": [],
                "summary": "抱歉，处理您的请求时出现了错误。"
            }

    @traceable
    async def rag_summary(self, query: str) -> str:
        """RAG 摘要"""
        result = await self.get_documents_and_summary(query)
        return result.get("summary", "抱歉，处理您的请求时出现了错误。")

if __name__ == '__main__':
    import asyncio

    async def main():
        service = RagService()
        await service.initialize_retriever()
        result = await service.rag_summary("小户型适合什么扫地机器人")
        print(result)

    asyncio.run(main())
