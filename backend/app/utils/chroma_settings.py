def chroma_hnsw_space(config: dict | None = None) -> str:
    """读取 Chroma HNSW 距离空间，默认使用更适合文本语义检索的 cosine。"""
    config = config or {}
    return str(config.get("hnsw_space") or "cosine").strip().lower()


def chroma_collection_metadata(config: dict | None = None) -> dict:
    return {"hnsw:space": chroma_hnsw_space(config)}


def distance_to_similarity(distance, space: str | None = None) -> float:
    """将 Chroma 返回的距离分数按 collection 距离类型转换成 0~1 展示相似度。"""
    try:
        value = float(distance)
    except (TypeError, ValueError):
        return 0.0

    normalized_space = str(space or "cosine").strip().lower()
    if normalized_space == "cosine":
        similarity = 1 - value
    elif normalized_space == "ip":
        similarity = value
    else:
        if value <= 0:
            return 1.0
        similarity = 1 / (1 + value)

    return round(max(0.0, min(1.0, similarity)), 4)
