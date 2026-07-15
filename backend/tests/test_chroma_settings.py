from app.utils.chroma_settings import chroma_collection_metadata, distance_to_similarity


def test_chroma_collection_metadata_defaults_to_cosine():
    assert chroma_collection_metadata({}) == {"hnsw:space": "cosine"}


def test_chroma_collection_metadata_uses_configured_space():
    assert chroma_collection_metadata({"hnsw_space": "l2"}) == {"hnsw:space": "l2"}


def test_cosine_distance_is_converted_with_one_minus_distance():
    assert distance_to_similarity(0.25, space="cosine") == 0.75


def test_l2_distance_keeps_inverse_distance_conversion():
    assert distance_to_similarity(1.0, space="l2") == 0.5


if __name__ == "__main__":
    test_chroma_collection_metadata_defaults_to_cosine()
    test_chroma_collection_metadata_uses_configured_space()
    test_cosine_distance_is_converted_with_one_minus_distance()
    test_l2_distance_keeps_inverse_distance_conversion()
