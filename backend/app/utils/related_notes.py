from app.utils.chroma_settings import distance_to_similarity as _distance_to_similarity


def build_note_related_filter(user_id: str) -> dict:
    """Chroma 关联笔记检索必须限定当前用户的笔记向量。"""
    return {
        "user_id": user_id,
        "doc_type": "note",
    }


def distance_to_similarity(distance) -> float:
    """
    将 Chroma 返回的距离分数转换为 0~1 展示相似度。

    similarity_search_with_score 返回的是距离，值可能大于 1，不能直接乘 100 当百分比。
    """
    return _distance_to_similarity(distance)
