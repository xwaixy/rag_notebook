from app.utils.rag_query import (
    document_relevance_components,
    document_relevance_score,
    filter_documents_by_relevance,
    get_dynamic_retrieval_weights,
    rank_documents_by_query,
)


class FakeDocument:
    def __init__(self, content: str, metadata: dict | None = None):
        self.page_content = content
        self.metadata = metadata or {}


def test_dynamic_weights_use_query_intent_for_chinese_summary_queries():
    assert get_dynamic_retrieval_weights("总结一下RAG知识笔记") == [0.45, 0.55]


def test_dynamic_weights_boost_vector_for_semantic_reasoning_queries():
    assert get_dynamic_retrieval_weights("RAG 和传统关键词搜索有什么区别") == [0.7, 0.3]


def test_dynamic_weights_boost_bm25_for_exact_lookup_queries():
    assert get_dynamic_retrieval_weights("找标题包含 MCP 的笔记") == [0.3, 0.7]


def test_relevance_filter_removes_unrelated_forced_top_k_documents():
    rag_doc = FakeDocument("RAG 是 Retrieval-Augmented Generation，用于结合检索结果增强回答。", {"title": "RAG 知识笔记"})
    intro_doc = FakeDocument("我是一个智能助手，可以进行自我介绍。", {"source": "自我介绍.txt"})

    result = filter_documents_by_relevance("总结一下RAG知识笔记", [intro_doc, rag_doc])

    assert result == [rag_doc]


def test_relevance_filter_can_use_hyde_terms_for_identity_queries():
    intro_doc = FakeDocument("姓名：小伍。身份：智能笔记系统用户。", {"source": "自我介绍.txt"})

    result = filter_documents_by_relevance(
        "我是谁",
        [intro_doc],
        auxiliary_query="个人资料，姓名，身份信息，自我介绍，用户档案",
    )

    assert result == [intro_doc]


def test_relevance_filter_keeps_high_vector_similarity_documents_without_literal_match():
    intro_doc = FakeDocument(
        "姓名：小伍。平时喜欢吃面食，也爱吃甜品。",
        {"source": "自我介绍.txt", "vector_similarity": 0.72},
    )

    result = filter_documents_by_relevance(
        "我喜欢吃什么",
        [intro_doc],
        auxiliary_query="喜欢的食物，饮食偏好，口味偏好，爱吃的菜",
    )

    assert result == [intro_doc]


def test_relevance_filter_removes_low_vector_similarity_documents_without_literal_match():
    intro_doc = FakeDocument(
        "姓名：小伍。平时喜欢吃面食，也爱吃甜品。",
        {"source": "自我介绍.txt", "vector_similarity": 0.1},
    )

    result = filter_documents_by_relevance(
        "我喜欢吃什么",
        [intro_doc],
        auxiliary_query="喜欢的食物，饮食偏好，口味偏好，爱吃的菜",
    )

    assert result == []


def test_title_and_tag_matches_are_ranked_before_content_only_matches():
    title_doc = FakeDocument("这篇文章介绍检索增强生成的使用方式。", {"title": "RAG 知识笔记"})
    content_doc = FakeDocument("RAG 可以结合知识库内容回答问题。", {"title": "普通学习记录"})

    result = rank_documents_by_query("总结一下RAG知识笔记", [content_doc, title_doc])

    assert result[0] == title_doc
    assert document_relevance_score("总结一下RAG知识笔记", title_doc) > document_relevance_score("总结一下RAG知识笔记", content_doc)


def test_relevance_components_keep_vector_score_as_primary_signal():
    high_vector_doc = FakeDocument("这是一段语义相关但没有直接关键词的内容。", {"vector_similarity": 0.8})
    low_vector_doc = FakeDocument("这段内容提到了喜欢吃，但向量相似度很低。", {"vector_similarity": 0.1})

    high_parts = document_relevance_components("我喜欢吃什么", high_vector_doc)
    low_parts = document_relevance_components("我喜欢吃什么", low_vector_doc)

    assert high_parts["vector_score"] == 0.8
    assert high_parts["final_score"] > low_parts["final_score"]


if __name__ == "__main__":
    test_dynamic_weights_use_query_intent_for_chinese_summary_queries()
    test_dynamic_weights_boost_vector_for_semantic_reasoning_queries()
    test_dynamic_weights_boost_bm25_for_exact_lookup_queries()
    test_relevance_filter_removes_unrelated_forced_top_k_documents()
    test_relevance_filter_can_use_hyde_terms_for_identity_queries()
    test_relevance_filter_keeps_high_vector_similarity_documents_without_literal_match()
    test_relevance_filter_removes_low_vector_similarity_documents_without_literal_match()
    test_title_and_tag_matches_are_ranked_before_content_only_matches()
    test_relevance_components_keep_vector_score_as_primary_signal()
