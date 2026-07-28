import asyncio
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env.docker", override=False)
load_dotenv(BACKEND_DIR / ".env", override=False)

from app.rag.reorder_service import ReorderService  # noqa: E402


async def main() -> None:
    service = ReorderService()
    result = await service.reorder_documents(
        "什么是向量数据库？",
        [
            "向量数据库用于存储和检索向量数据。",
            "今天的天气很好。",
            "RAG 通常使用向量数据库进行语义检索。",
        ],
    )
    if not result["success"]:
        raise RuntimeError(result["error"])

    print("Qwen3-VL-Rerank API 调用成功：")
    for index, item in enumerate(result["documents"], 1):
        print(f"{index}. score={item['similarity']:.6f} document={item['document']}")


if __name__ == "__main__":
    asyncio.run(main())
