import json
import re

from app.utils.response_text import extract_response_text

SELF_ASSESSMENT_CHOICES = {"不太确定", "需要复习", "基本掌握", "完全理解"}
LETTER_TO_INDEX = {"A": 0, "B": 1, "C": 2, "D": 3}
MIN_REVIEW_QUESTION_COUNT = 5


def extract_json_from_text(text: str) -> str:
    match = re.search(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]

    return text


def _normalize_choices(choices) -> list[str]:
    if not isinstance(choices, list):
        raise ValueError("choices 必须是列表")

    normalized = []
    for choice in choices:
        text = str(choice or "").strip()
        if text and text not in normalized:
            normalized.append(text)

    if len(normalized) != 4:
        raise ValueError("回顾题必须有 4 个唯一选项")

    return normalized


def _reject_self_assessment_question(question: str, choices: list[str]) -> None:
    if len(SELF_ASSESSMENT_CHOICES.intersection(choices)) >= 2:
        raise ValueError("自评式回顾题没有客观正确答案")

    if "回顾这篇笔记" in question and any(choice in SELF_ASSESSMENT_CHOICES for choice in choices):
        raise ValueError("自评式回顾题没有客观正确答案")


def _load_json_payload(response_content):
    if isinstance(response_content, dict):
        return response_content

    if isinstance(response_content, list) and all(isinstance(item, dict) and "question" in item for item in response_content):
        return {"questions": response_content}

    raw_output = extract_response_text(response_content).strip()
    json_str = extract_json_from_text(raw_output)
    return json.loads(json_str)


def normalize_review_question_payload(response_content) -> dict:
    data = _load_json_payload(response_content)
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        if not data["questions"]:
            raise ValueError("questions 不能为空")
        data = data["questions"][0]

    question = str(data.get("question", "")).strip()
    choices = _normalize_choices(data.get("choices", []))
    answer = str(data.get("answer", "")).strip()

    if answer.upper() in LETTER_TO_INDEX:
        answer = choices[LETTER_TO_INDEX[answer.upper()]]

    _reject_self_assessment_question(question, choices)

    if not question:
        raise ValueError("问题不能为空")
    if answer not in choices:
        raise ValueError("答案必须是 4 个选项之一")

    return {
        "question": question,
        "choices": choices,
        "answer": answer,
    }


def normalize_review_questions_payload(response_content, min_count: int = MIN_REVIEW_QUESTION_COUNT) -> dict:
    data = _load_json_payload(response_content)

    if isinstance(data, list):
        items = data
    elif isinstance(data, dict) and isinstance(data.get("questions"), list):
        items = data["questions"]
    elif isinstance(data, dict) and "question" in data:
        items = [data]
    else:
        raise ValueError("回顾题响应必须包含 questions 数组")

    questions = [normalize_review_question_payload(item) for item in items]
    if len(questions) < min_count:
        raise ValueError(f"至少需要 {min_count} 道回顾题")

    return {"questions": questions}


def build_fallback_review_question(title: str, content: str) -> dict:
    title_text = str(title or "").strip()
    content_text = str(content or "").strip()
    answer = title_text or (content_text[:30].strip() if content_text else "这篇笔记的核心主题")

    choices = [
        answer,
        "用户登录认证流程",
        "页面样式与主题配置",
        "文件上传与下载操作",
    ]

    unique_choices = []
    for choice in choices:
        if choice and choice not in unique_choices:
            unique_choices.append(choice)

    while len(unique_choices) < 4:
        unique_choices.append(f"干扰选项 {len(unique_choices)}")

    return {
        "question": "这篇笔记主要围绕哪个主题？",
        "choices": unique_choices[:4],
        "answer": answer,
    }


def build_fallback_review_questions(title: str, content: str, min_count: int = MIN_REVIEW_QUESTION_COUNT) -> dict:
    title_text = str(title or "").strip()
    content_text = str(content or "").strip()
    answer = title_text or (content_text[:30].strip() if content_text else "这篇笔记的核心主题")
    distractors = ["用户登录认证流程", "页面样式与主题配置", "文件上传与下载操作"]
    question_texts = [
        "这篇笔记主要围绕哪个主题？",
        "根据笔记标题，以下哪项最符合核心内容？",
        "回顾这篇笔记时，应优先关联哪个知识主题？",
        "这篇笔记最可能帮助复习哪个知识点？",
        "以下哪个选项最贴近这篇笔记的主题？",
    ]

    questions = []
    for index in range(max(min_count, len(question_texts))):
        choices = [answer] + distractors
        questions.append({
            "question": question_texts[index] if index < len(question_texts) else f"这篇笔记的第 {index + 1} 个核心回顾点是什么？",
            "choices": choices,
            "answer": answer,
        })

    return {"questions": questions}
