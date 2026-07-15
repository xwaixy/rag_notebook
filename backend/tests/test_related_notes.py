from app.utils.related_notes import build_note_related_filter, distance_to_similarity


def test_note_related_filter_limits_results_to_current_user_notes():
    assert build_note_related_filter("user-1") == {
        "user_id": "user-1",
        "doc_type": "note",
    }


def test_distance_to_similarity_is_clamped_percentage_source():
    assert distance_to_similarity(0) == 1.0
    assert distance_to_similarity(0.25) == 0.75
    assert 0 <= distance_to_similarity(10) <= 1


if __name__ == "__main__":
    test_note_related_filter_limits_results_to_current_user_notes()
    test_distance_to_similarity_is_clamped_percentage_source()
