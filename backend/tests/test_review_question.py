from app.utils.review_question import (
    build_fallback_review_question,
    build_fallback_review_questions,
    normalize_review_question_payload,
    normalize_review_questions_payload,
)


def test_normalize_review_question_accepts_responses_api_blocks_and_maps_letter_answer():
    response_content = [
        {"type": "reasoning", "summary": [{"type": "summary_text", "text": "drafting"}]},
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": '```json\n{"question":"RAG 的核心作用是什么？","choices":["增强生成","图片压缩","登录认证","样式美化"],"answer":"A"}\n```',
                }
            ],
        },
    ]

    result = normalize_review_question_payload(response_content)

    assert result == {
        "question": "RAG 的核心作用是什么？",
        "choices": ["增强生成", "图片压缩", "登录认证", "样式美化"],
        "answer": "增强生成",
    }


def test_normalize_review_question_rejects_self_assessment_choices():
    try:
        normalize_review_question_payload(
            '{"question":"请回顾这篇笔记的主要内容","choices":["不太确定","需要复习","基本掌握","完全理解"],"answer":"基本掌握"}'
        )
    except ValueError as exc:
        assert "自评" in str(exc)
    else:
        raise AssertionError("自评式回顾题应该被拒绝")


def test_fallback_review_question_uses_note_title_and_avoids_self_assessment_choices():
    result = build_fallback_review_question("RAG（检索增强生成）学习笔记", "")

    assert result["question"] == "这篇笔记主要围绕哪个主题？"
    assert result["answer"] == "RAG（检索增强生成）学习笔记"
    assert result["answer"] in result["choices"]
    assert "基本掌握" not in result["choices"]


def test_normalize_review_questions_requires_at_least_five_questions():
    payload = {
        "questions": [
            {"question": f"第 {i} 道题？", "choices": ["正确", "干扰1", "干扰2", "干扰3"], "answer": "正确"}
            for i in range(1, 6)
        ]
    }

    result = normalize_review_questions_payload(payload)

    assert len(result["questions"]) == 5
    assert result["questions"][0]["question"] == "第 1 道题？"


def test_fallback_review_questions_returns_at_least_five_objective_questions():
    result = build_fallback_review_questions("RAG（检索增强生成）学习笔记", "")

    assert len(result["questions"]) >= 5
    for question in result["questions"]:
        assert question["answer"] in question["choices"]
        assert "基本掌握" not in question["choices"]


if __name__ == "__main__":
    test_normalize_review_question_accepts_responses_api_blocks_and_maps_letter_answer()
    test_normalize_review_question_rejects_self_assessment_choices()
    test_fallback_review_question_uses_note_title_and_avoids_self_assessment_choices()
    test_normalize_review_questions_requires_at_least_five_questions()
    test_fallback_review_questions_returns_at_least_five_objective_questions()
