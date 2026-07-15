import json
import re

from app.utils.response_text import extract_response_text

ALLOWED_NOTE_CATEGORIES = {"work", "study", "life", "project"}
CATEGORY_ALIASES = {
    "work": "work",
    "工作": "work",
    "study": "study",
    "学习": "study",
    "life": "life",
    "生活": "life",
    "project": "project",
    "项目": "project",
}
MAX_AUTO_TAGS = 5


def build_auto_tag_input(title: str, content: str) -> str:
    title_text = str(title or "").strip()
    content_text = str(content or "").strip()

    if title_text and content_text:
        return f"标题：{title_text}\n\n正文：\n{content_text}"
    return title_text or content_text


def extract_json_from_text(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text


def normalize_auto_tags(tags) -> list[str]:
    if isinstance(tags, str):
        candidates = tags.split(",")
    elif isinstance(tags, list):
        candidates = tags
    else:
        candidates = []

    normalized_tags = []
    for tag in candidates:
        text = str(tag).strip()
        if text and text not in normalized_tags:
            normalized_tags.append(text)
        if len(normalized_tags) >= MAX_AUTO_TAGS:
            break

    return normalized_tags


def normalize_manual_tags(tags) -> list[str]:
    return normalize_auto_tags(tags)


def normalize_note_category(category) -> str:
    normalized = str(category or "life").strip().lower()
    return CATEGORY_ALIASES.get(normalized, "life")


def parse_auto_tag_response_content(response_content) -> tuple[list[str], str]:
    raw_output = extract_response_text(response_content).strip()
    json_str = extract_json_from_text(raw_output)
    result = json.loads(json_str)

    tags = normalize_auto_tags(result.get("tags", []))
    category = normalize_note_category(result.get("category", "life"))

    return tags, category
