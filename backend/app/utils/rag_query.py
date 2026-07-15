import os
import re


EXACT_LOOKUP_KEYWORDS = ("标题", "标签", "文件名", "包含", "叫做", "搜索", "查找", "找")
SUMMARY_KEYWORDS = ("总结", "归纳", "整理", "概括")
SEMANTIC_REASONING_KEYWORDS = ("为什么", "怎么", "区别", "关系", "原理", "解释", "如何")
STOPWORDS = {"一下", "这个", "那个", "哪些", "什么", "关于", "帮我", "进行", "知识", "笔记", "总结"}


def _query_text(query: str | None) -> str:
    return str(query or "").strip()


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword.lower() in text.lower() for keyword in keywords)


def get_dynamic_retrieval_weights(query: str | None = None) -> list[float]:
    """根据查询意图动态调整 [向量检索权重, BM25 权重]。"""
    text = _query_text(query)
    if not text:
        return [0.5, 0.5]

    if _contains_any(text, SUMMARY_KEYWORDS):
        return [0.45, 0.55]
    if _contains_any(text, SEMANTIC_REASONING_KEYWORDS):
        return [0.7, 0.3]
    if _contains_any(text, EXACT_LOOKUP_KEYWORDS):
        return [0.3, 0.7]

    query_length = len(text)
    if query_length > 50:
        return [0.7, 0.3]
    if query_length < 20:
        return [0.4, 0.6]
    return [0.5, 0.5]


def extract_query_terms(query: str | None) -> list[str]:
    text = _query_text(query)
    if not text:
        return []

    terms = re.findall(r"[A-Za-z0-9]+|[\u4e00-\u9fff]{2,}", text)
    normalized = []
    for term in terms:
        value = term.strip()
        if not value or value in STOPWORDS:
            continue
        if len(value) > 8 and re.search(r"[\u4e00-\u9fff]", value):
            # 中文无空格时，保留原片段，同时拆出常见英文/数字术语。
            english_terms = re.findall(r"[A-Za-z0-9]+", value)
            normalized.extend(t for t in english_terms if t not in normalized)
        if value not in normalized:
            normalized.append(value)

    return normalized


def _metadata_text(document) -> str:
    metadata = getattr(document, "metadata", {}) or {}
    fields = [
        metadata.get("title", ""),
        metadata.get("original_filename", ""),
        metadata.get("source", ""),
        metadata.get("filename", ""),
        " ".join(str(tag) for tag in metadata.get("tags", []) if tag),
    ]
    return " ".join(str(field) for field in fields if field)


def _vector_similarity(document) -> float | None:
    metadata = getattr(document, "metadata", {}) or {}
    try:
        return float(metadata.get("vector_similarity"))
    except (TypeError, ValueError):
        return None


def _min_vector_similarity() -> float:
    try:
        return float(os.getenv("RAG_MIN_VECTOR_SIMILARITY", "0.35"))
    except ValueError:
        return 0.35


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def _combined_query_terms(query: str | None, auxiliary_query: str | None = None) -> list[str]:
    terms = extract_query_terms(query)
    for term in extract_query_terms(auxiliary_query):
        if term not in terms:
            terms.append(term)
    return terms


def document_relevance_components(query: str | None, document, auxiliary_query: str | None = None) -> dict[str, float]:
    """拆分文档相关性分数，避免把不同含义的分数混成一个“相似度”。"""
    terms = _combined_query_terms(query, auxiliary_query)
    vector_similarity = _vector_similarity(document)
    vector_score = _clamp_score(vector_similarity) if vector_similarity is not None else 0.0

    if not terms:
        return {
            "vector_score": vector_score,
            "lexical_score": 0.0,
            "metadata_score": 0.0,
            "literal_score": 0.0,
            "final_score": vector_score,
        }

    metadata_text = _metadata_text(document).lower()
    content = str(getattr(document, "page_content", "") or "").lower()

    metadata_hits = 0.0
    lexical_hits = 0.0
    for term in terms:
        lower_term = term.lower()
        if lower_term in metadata_text:
            metadata_hits += 1.0
        if lower_term in content:
            lexical_hits += 1.0

    term_count = max(1, len(terms))
    metadata_score = _clamp_score(metadata_hits / term_count)
    lexical_score = _clamp_score(lexical_hits / term_count)

    # literal_score 保留旧过滤语义：标题/标签/文件名命中更重要，正文命中也可通过过滤。
    literal_score = metadata_hits * 3.0 + lexical_hits
    final_score = _clamp_score(vector_score * 0.7 + metadata_score * 0.2 + lexical_score * 0.1)

    return {
        "vector_score": vector_score,
        "lexical_score": lexical_score,
        "metadata_score": metadata_score,
        "literal_score": literal_score,
        "final_score": final_score,
    }


def document_relevance_score(query: str | None, document, auxiliary_query: str | None = None) -> float:
    """返回最终排序分，分数范围为 0~1。"""
    return document_relevance_components(query, document, auxiliary_query=auxiliary_query)["final_score"]


def filter_documents_by_relevance(
    query: str | None,
    documents: list,
    min_score: float | None = None,
    auxiliary_query: str | None = None,
) -> list:
    if min_score is None:
        try:
            min_score = float(os.getenv("RAG_MIN_RULE_RELEVANCE_SCORE", "1"))
        except ValueError:
            min_score = 1.0
    min_vector_similarity = _min_vector_similarity()
    filtered = []
    for doc in documents:
        score_parts = document_relevance_components(query, doc, auxiliary_query=auxiliary_query)
        vector_similarity = _vector_similarity(doc)
        if score_parts["literal_score"] >= min_score or (vector_similarity is not None and vector_similarity >= min_vector_similarity):
            filtered.append(doc)
    return filtered


def rank_documents_by_query(query: str | None, documents: list, auxiliary_query: str | None = None) -> list:
    return sorted(
        documents,
        key=lambda doc: document_relevance_score(query, doc, auxiliary_query=auxiliary_query),
        reverse=True,
    )
