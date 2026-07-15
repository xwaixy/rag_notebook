from app.utils.response_text import extract_response_text


def test_extract_response_text_from_responses_stream_blocks():
    output = [
        {
            "type": "reasoning",
            "summary": [
                {
                    "type": "summary_text",
                    "text": "**Preparing simple greeting response**",
                }
            ],
        },
        {
            "type": "text",
            "text": "Hello! 我可以帮你搜索笔记。",
        },
    ]

    assert extract_response_text(output) == "Hello! 我可以帮你搜索笔记。"


def test_extract_response_text_from_responses_message_payload():
    output = [
        {
            "type": "message",
            "content": [
                {
                    "type": "output_text",
                    "text": "Hello! How can I help you today?",
                }
            ],
        }
    ]

    assert extract_response_text(output) == "Hello! How can I help you today?"


def test_extract_response_text_keeps_plain_string():
    assert extract_response_text("plain answer") == "plain answer"


if __name__ == "__main__":
    test_extract_response_text_from_responses_stream_blocks()
    test_extract_response_text_from_responses_message_payload()
    test_extract_response_text_keeps_plain_string()
