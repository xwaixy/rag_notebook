import asyncio
from types import SimpleNamespace

from app.agent import agent_tools


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class FakeNoteService:
    def __init__(self):
        self.created_payloads = []

    async def create_note(self, db, user_id, payload):
        note_id = f"note-{len(self.created_payloads) + 1}"
        self.created_payloads.append((user_id, payload.title, payload.content))
        return SimpleNamespace(id=note_id, title=payload.title)


def test_duplicate_create_note_tool_call_reuses_first_created_note():
    note_service = FakeNoteService()
    original_note_service = getattr(agent_tools.init_manager, "note_service", None)
    original_session_local = agent_tools.AsyncSessionLocal

    reset_idempotency_state = getattr(agent_tools, "_reset_note_create_idempotency_state", None)
    if reset_idempotency_state:
        reset_idempotency_state()

    try:
        agent_tools.init_manager.note_service = note_service
        agent_tools.AsyncSessionLocal = lambda: FakeSession()
        agent_tools.set_current_user_id("user-1")

        async def run_duplicate_calls():
            first = await agent_tools.create_note_tool.ainvoke(
                {"title": "MCP 知识笔记", "content": "# MCP\ncontent"}
            )
            second = await agent_tools.create_note_tool.ainvoke(
                {"title": "MCP 知识笔记", "content": "# MCP\ncontent"}
            )
            return first, second

        first_result, second_result = asyncio.run(run_duplicate_calls())
    finally:
        agent_tools.init_manager.note_service = original_note_service
        agent_tools.AsyncSessionLocal = original_session_local
        if reset_idempotency_state:
            reset_idempotency_state()

    assert note_service.created_payloads == [("user-1", "MCP 知识笔记", "# MCP\ncontent")]
    assert "- ID: note-1" in first_result
    assert "- ID: note-1" in second_result


if __name__ == "__main__":
    test_duplicate_create_note_tool_call_reuses_first_created_note()
