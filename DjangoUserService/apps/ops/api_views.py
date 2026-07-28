from collections import deque
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.user.authentications import JWTAuthentication
from apps.user.models import User, UserStatusChoice
from apps.utils.cache_utils import clear_user_cache
from .models import ChatMessage, ChatSession, Note, ReviewRecord
from .permissions import IsSuperUser
from .views import _database_status, _fastapi_status, _redis_status, _safe_count


class AdminAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsSuperUser]


def _iso(value):
    return value.isoformat() if value else None


def _user_payload(user):
    return {
        "id": str(user.uuid),
        "username": user.username,
        "email": user.email,
        "telephone": user.telephone,
        "status": user.status,
        "status_label": user.get_status_display(),
        "is_active": user.status == UserStatusChoice.ACTIVE,
        "is_superuser": user.is_superuser,
        "date_joined": _iso(user.date_joined),
        "last_login": _iso(user.last_login),
    }


def _page_number(value, default=1):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _page_size(value, default=20):
    try:
        return min(50, max(1, int(value)))
    except (TypeError, ValueError):
        return default


def _recent_rows(queryset, fields, limit=5):
    try:
        return [
            {field: _iso(getattr(row, field)) if field.endswith("_at") or field.endswith("_time") else getattr(row, field)
             for field in fields}
            for row in queryset[:limit]
        ]
    except Exception:
        return []


class AdminDashboardView(AdminAPIView):
    def get(self, request):
        business_sessions = ChatSession.objects.using("backend").order_by("-updated_at")
        business_messages = ChatMessage.objects.using("backend").order_by("-created_at")
        business_notes = Note.objects.using("backend").order_by("-updated_at")
        business_reviews = ReviewRecord.objects.using("backend").order_by("-created_at")

        data = {
            "stats": {
                "users": _safe_count(User.objects.all()),
                "active_users": _safe_count(User.objects.filter(status=UserStatusChoice.ACTIVE)),
                "sessions": _safe_count(business_sessions),
                "messages": _safe_count(business_messages),
                "notes": _safe_count(business_notes),
                "review_records": _safe_count(business_reviews),
            },
            "checks": [
                _database_status("default", "用户数据库"),
                _database_status("backend", "业务数据库"),
                _redis_status(),
                _fastapi_status(),
            ],
            "recent": {
                "users": [_user_payload(user) for user in User.objects.order_by("-date_joined")[:5]],
                "sessions": _recent_rows(business_sessions, ("id", "title", "user_id", "updated_at")),
                "notes": _recent_rows(business_notes, ("id", "title", "user_id", "updated_at")),
                "reviews": _recent_rows(business_reviews, ("id", "user_id", "note_id", "next_review_at")),
                "messages": _recent_rows(business_messages, ("id", "session_id", "role", "created_at")),
            },
        }
        return Response({"success": True, "data": data})


class AdminUserListView(AdminAPIView):
    def get(self, request):
        page = _page_number(request.query_params.get("page"))
        page_size = _page_size(request.query_params.get("page_size"))
        search = request.query_params.get("search", "").strip()
        queryset = User.objects.order_by("-date_joined")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(telephone__icontains=search)
            )

        status_value = request.query_params.get("status")
        if status_value not in (None, ""):
            try:
                queryset = queryset.filter(status=int(status_value))
            except ValueError:
                return Response({"detail": "status 参数无效"}, status=400)

        total = queryset.count()
        start = (page - 1) * page_size
        users = queryset[start:start + page_size]
        return Response({
            "success": True,
            "data": {
                "items": [_user_payload(user) for user in users],
                "total": total,
                "page": page,
                "page_size": page_size,
            },
        })


class AdminUserStatusView(AdminAPIView):
    def patch(self, request, user_id):
        try:
            user = User.objects.get(uuid=user_id)
        except User.DoesNotExist:
            return Response({"detail": "用户不存在"}, status=404)

        if user.is_superuser:
            return Response({"detail": "不能修改唯一管理员的状态"}, status=400)

        try:
            new_status = int(request.data.get("status"))
        except (TypeError, ValueError):
            return Response({"detail": "status 必须是 0、1 或 2"}, status=400)

        valid_statuses = {choice.value for choice in UserStatusChoice}
        if new_status not in valid_statuses:
            return Response({"detail": "status 必须是 0、1 或 2"}, status=400)

        user.status = new_status
        user.is_active = new_status == UserStatusChoice.ACTIVE
        user.save(update_fields=("status", "is_active", "is_staff"))
        clear_user_cache(user.uuid)
        return Response({"success": True, "data": _user_payload(user)})


class AdminBusinessDataView(AdminAPIView):
    resources = {
        "sessions": (ChatSession, ("id", "title", "user_id", "updated_at"), "-updated_at"),
        "messages": (ChatMessage, ("id", "session_id", "role", "created_at"), "-created_at"),
        "notes": (Note, ("id", "title", "user_id", "updated_at"), "-updated_at"),
        "reviews": (ReviewRecord, ("id", "user_id", "note_id", "next_review_at"), "-next_review_at"),
    }

    def get(self, request):
        resource = request.query_params.get("resource", "sessions")
        config = self.resources.get(resource)
        if not config:
            return Response({"detail": "resource 参数无效"}, status=400)

        model, fields, ordering = config
        page = _page_number(request.query_params.get("page"))
        page_size = _page_size(request.query_params.get("page_size"))
        queryset = model.objects.using("backend").order_by(ordering)
        search = request.query_params.get("search", "").strip()
        if search:
            searchable = [field for field in fields if field in {"id", "title", "user_id", "session_id", "note_id", "role"}]
            query = Q()
            for field_name in searchable:
                field = model._meta.get_field(field_name)
                if isinstance(field, (models.CharField, models.TextField)):
                    query |= Q(**{f"{field_name}__icontains": search})
                elif isinstance(field, models.IntegerField) and search.isdigit():
                    query |= Q(**{field_name: int(search)})
            if query.children:
                queryset = queryset.filter(query)
            else:
                queryset = queryset.none()

        total = _safe_count(queryset)
        start = (page - 1) * page_size
        items = _recent_rows(queryset[start:start + page_size], fields, limit=page_size)
        return Response({
            "success": True,
            "data": {"resource": resource, "items": items, "total": total, "page": page, "page_size": page_size},
        })


class AdminLogsView(AdminAPIView):
    def get(self, request):
        log_root = Path(settings.BACKEND_LOG_DIR).resolve()
        files = []
        if log_root.is_dir():
            files = sorted(log_root.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True)

        selected_name = request.query_params.get("file", "")
        selected_file = None
        if selected_name:
            if Path(selected_name).name == selected_name:
                candidate = (log_root / selected_name).resolve()
                if candidate.parent == log_root and candidate.is_file() and candidate.suffix == ".log":
                    selected_file = candidate
        elif files:
            selected_file = files[0]

        try:
            max_lines = min(500, max(50, int(request.query_params.get("max_lines", 200))))
        except ValueError:
            max_lines = 200

        content = ""
        if selected_file:
            with selected_file.open("r", encoding="utf-8", errors="replace") as handle:
                content = "".join(deque(handle, maxlen=max_lines))

        return Response({
            "success": True,
            "data": {
                "files": [{"name": item.name, "size": item.stat().st_size} for item in files],
                "selected": selected_file.name if selected_file else "",
                "content": content,
            },
        })
