from app.utils import note_auto_tag
from app.utils.note_auto_tag import parse_auto_tag_response_content


def test_parse_auto_tag_response_content_accepts_responses_api_list_blocks():
    response_content = [
        {
            "type": "reasoning",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "Thinking about note tags",
                }
            ],
        },
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": '```json\n{"tags": ["AI", "学习"], "category": "study"}\n```',
                }
            ],
        },
    ]

    tags, category = parse_auto_tag_response_content(response_content)

    assert tags == ["AI", "学习"]
    assert category == "study"


def test_create_note_auto_tag_input_includes_title_when_content_is_empty():
    build_auto_tag_input = getattr(note_auto_tag, "build_auto_tag_input", None)

    assert build_auto_tag_input is not None
    assert "MCP 知识笔记" in build_auto_tag_input("MCP 知识笔记", "")


def test_normalize_manual_tags_strips_empty_duplicates_and_limits_to_five():
    normalize_manual_tags = getattr(note_auto_tag, "normalize_manual_tags", None)

    assert normalize_manual_tags is not None
    assert normalize_manual_tags([" AI ", "", "AI", "FastAPI", "RAG", "学习", "项目", "多余"]) == [
        "AI",
        "FastAPI",
        "RAG",
        "学习",
        "项目",
    ]


if __name__ == "__main__":
    test_parse_auto_tag_response_content_accepts_responses_api_list_blocks()
    test_create_note_auto_tag_input_includes_title_when_content_is_empty()
    test_normalize_manual_tags_strips_empty_duplicates_and_limits_to_five()
