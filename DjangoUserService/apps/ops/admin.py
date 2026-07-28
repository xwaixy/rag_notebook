from django.contrib import admin

from .models import ChatMessage, ChatSession, Note, ReviewRecord


class ReadOnlyAdmin(admin.ModelAdmin):
    """业务数据由 FastAPI 维护，Django Admin 仅用于查看。"""

    actions = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff


@admin.register(ChatSession)
class ChatSessionAdmin(ReadOnlyAdmin):
    list_display = ("id", "title", "user_id", "created_at", "updated_at")
    search_fields = ("id", "title", "user_id")
    list_filter = ("created_at", "updated_at")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "user_id", "title", "metadata", "created_at", "updated_at")


@admin.register(ChatMessage)
class ChatMessageAdmin(ReadOnlyAdmin):
    list_display = ("id", "session_id", "role", "content_preview", "created_at")
    search_fields = ("session_id", "role", "content")
    list_filter = ("role", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("id", "session_id", "role", "content", "metadata", "created_at")

    @admin.display(description="内容")
    def content_preview(self, obj):
        compact = " ".join(obj.content.split())
        return compact[:100] + ("..." if len(compact) > 100 else "")


@admin.register(Note)
class NoteAdmin(ReadOnlyAdmin):
    list_display = ("title", "user_id", "category", "tags_display", "created_at", "updated_at")
    search_fields = ("id", "user_id", "title", "content", "category")
    list_filter = ("category", "created_at", "updated_at")
    ordering = ("-updated_at",)
    readonly_fields = ("id", "user_id", "title", "content", "tags", "category", "created_at", "updated_at")

    @admin.display(description="标签")
    def tags_display(self, obj):
        if isinstance(obj.tags, list):
            return ", ".join(str(tag) for tag in obj.tags)
        return obj.tags or "-"


@admin.register(ReviewRecord)
class ReviewRecordAdmin(ReadOnlyAdmin):
    list_display = (
        "id",
        "user_id",
        "note_id",
        "review_count",
        "interval_days",
        "last_reviewed_at",
        "next_review_at",
    )
    search_fields = ("id", "user_id", "note_id")
    list_filter = ("review_count", "interval_days", "last_reviewed_at", "next_review_at")
    ordering = ("next_review_at",)
    readonly_fields = (
        "id",
        "note_id",
        "user_id",
        "last_reviewed_at",
        "review_count",
        "next_review_at",
        "interval_days",
        "created_at",
    )
