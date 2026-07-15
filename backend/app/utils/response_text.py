def extract_response_text(value) -> str:
    """从 LangChain/OpenAI Responses API 的多形态输出中提取可展示文本。"""
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return "".join(part for item in value if (part := extract_response_text(item)))

    if isinstance(value, dict):
        block_type = value.get("type")

        # Responses API 的 reasoning/summary 块是模型思考过程，不应拼进最终回复。
        if block_type in {"reasoning", "summary_text"}:
            return ""

        if block_type in {"text", "output_text", "input_text"} and isinstance(value.get("text"), str):
            return value["text"]

        if "content" in value:
            return extract_response_text(value["content"])

        if "output" in value:
            return extract_response_text(value["output"])

        if isinstance(value.get("text"), str):
            return value["text"]

        return ""

    content = getattr(value, "content", None)
    if content is not None:
        return extract_response_text(content)

    return str(value)
