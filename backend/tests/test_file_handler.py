import os
import tempfile

from app.utils.file_handler import txt_loader_sync


def test_txt_loader_sync_loads_utf16_text_files():
    fd, path = tempfile.mkstemp(suffix=".txt")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-16") as f:
            f.write("我是小伍，喜欢吃面食，喜欢猫。")

        docs = txt_loader_sync(path)

        assert docs
        assert "喜欢吃面食" in docs[0].page_content
    finally:
        if os.path.exists(path):
            os.unlink(path)


if __name__ == "__main__":
    test_txt_loader_sync_loads_utf16_text_files()
