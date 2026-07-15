"""
回顾服务层 —— 艾宾浩斯间隔重复算法 + 回顾问题生成。
"""
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger_handler import logger
from app.models.note import Note
from app.models.review_record import ReviewRecord
from app.utils.review_question import build_fallback_review_questions, normalize_review_questions_payload

# 艾宾浩斯间隔重复数组（天）
INTERVALS = [1, 2, 4, 7, 15, 30]


def get_next_interval(review_count: int) -> int:
    """
    根据回顾次数返回下一次回顾间隔天数。
    超出预定义数组后固定使用 30 天间隔。
    """
    if review_count < len(INTERVALS):
        return INTERVALS[review_count]
    return INTERVALS[-1]


class ReviewService:
    """
    回顾服务 —— 负责今日回顾查询、标记已回顾、生成 LLM 回顾问题。
    """

    async def get_today_reviews(self, db: AsyncSession, user_id: str) -> list[dict]:
        """
        查询今日待回顾的笔记列表（next_review_at <= 当前时间）。
        同时关联查询笔记内容用于生成回顾问题。
        """
        now = datetime.now()

        # 查询待回顾的记录，关联笔记表获取标题和内容
        stmt = (
            select(ReviewRecord, Note.title, Note.content, Note.tags, Note.category)
            .join(Note, ReviewRecord.note_id == Note.id)
            .where(
                ReviewRecord.user_id == user_id,
                ReviewRecord.next_review_at <= now,
            )
            .order_by(ReviewRecord.next_review_at.asc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        reviews = []
        for record, title, content, tags, category in rows:
            reviews.append({
                "review_id": record.id,
                "note_id": record.note_id,
                "title": title,
                "content_preview": content[:200] if content else "",
                "tags": tags,
                "category": category,
                "review_count": record.review_count,
                "last_reviewed_at": str(record.last_reviewed_at) if record.last_reviewed_at else None,
                "interval_days": record.interval_days,
            })

        return reviews

    async def mark_reviewed(self, db: AsyncSession, note_id: str, user_id: str) -> dict:
        """
        标记笔记已回顾，更新 review_count 和 next_review_at。
        返回最新的间隔信息。
        """
        # 查询当前记录
        stmt = select(ReviewRecord).where(
            ReviewRecord.note_id == note_id,
            ReviewRecord.user_id == user_id,
        )
        result = await db.execute(stmt)
        record = result.scalar_one_or_none()

        if not record:
            return {"success": False, "message": "回顾记录不存在"}

        now = datetime.now()
        new_count = record.review_count + 1
        next_interval = get_next_interval(new_count)
        next_at = now + timedelta(days=next_interval)

        stmt = (
            update(ReviewRecord)
            .where(ReviewRecord.id == record.id)
            .values(
                review_count=new_count,
                interval_days=next_interval,
                last_reviewed_at=now,
                next_review_at=next_at,
            )
        )
        await db.execute(stmt)
        await db.commit()

        logger.info(f"标记回顾完成 note_id={note_id}, 第{new_count}次回顾, 下次间隔{next_interval}天")

        return {
            "success": True,
            "message": "已标记回顾",
            "review_count": new_count,
            "interval_days": next_interval,
            "next_review_at": str(next_at),
        }

    def _with_primary_question(self, payload: dict) -> dict:
        """
        多题接口兼容旧前端字段：保留 questions，同时展开第一题。
        """
        questions = payload.get("questions") or []
        if not questions:
            return {
                "questions": [],
                "question": "暂无可用回顾题",
                "choices": [],
                "answer": "",
            }

        first = questions[0]
        return {
            "questions": questions,
            "question": first["question"],
            "choices": first["choices"],
            "answer": first["answer"],
        }

    async def generate_review_question(self, content: str, title: str = "") -> dict:
        """
        调用 LLM 根据笔记内容生成至少 5 道回顾选择题。
        返回 {questions, question, choices, answer} 结构，其中单题字段用于兼容旧调用方。
        """
        raw = ""
        try:
            from langchain_core.messages import HumanMessage

            from app.core.background_init import init_manager
            from app.utils.prompt_loader import load_prompt

            chat_model = init_manager.chat_model
            prompt_template = load_prompt("review_question_prompt")
            prompt = prompt_template.format(title=title, content=content[:2000])
            response = await chat_model.ainvoke([HumanMessage(content=prompt)])
            raw = response.content
            logger.debug(f"LLM 原始响应: {str(raw)[:500]}")
            return self._with_primary_question(normalize_review_questions_payload(raw))
        except Exception as e:
            logger.error(f"生成回顾问题失败: {e} | raw={str(raw)[:300]}")
            return self._with_primary_question(build_fallback_review_questions(title, content))

    async def get_review_question_for_note(
        self, db: AsyncSession, note_id: str, user_id: str
    ) -> dict:
        """
        根据 note_id 查询笔记内容，生成回顾选择题。
        同时校验笔记归属。
        """
        stmt = select(Note).where(Note.id == note_id, Note.user_id == user_id)
        result = await db.execute(stmt)
        note = result.scalar_one_or_none()
        if not note:
            return {
                "questions": [],
                "question": "笔记不存在",
                "choices": [],
                "answer": "",
            }
        return await self.generate_review_question(note.content or "", note.title or "")


review_service = ReviewService()


def get_review_service() -> ReviewService:
    """依赖注入工厂函数。"""
    return review_service
