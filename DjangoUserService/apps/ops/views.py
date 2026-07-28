import time
from collections import deque
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.contrib import admin
from django.core.cache import cache
from django.db import connections
from django.shortcuts import render
from django.urls import reverse

from apps.user.models import User

from .models import ChatMessage, ChatSession, Note, ReviewRecord


def _database_status(alias: str, label: str) -> dict:
    started_at = time.monotonic()
    try:
        with connections[alias].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return {
            "label": label,
            "ok": True,
            "detail": f"连接正常，{(time.monotonic() - started_at) * 1000:.0f} ms",
        }
    except Exception as exc:
        return {"label": label, "ok": False, "detail": str(exc)[:200]}


def _redis_status() -> dict:
    started_at = time.monotonic()
    key = "ops:health-check"
    try:
        cache.set(key, "ok", timeout=10)
        if cache.get(key) != "ok":
            raise RuntimeError("缓存写入后无法读取")
        return {
            "label": "Redis",
            "ok": True,
            "detail": f"连接正常，{(time.monotonic() - started_at) * 1000:.0f} ms",
        }
    except Exception as exc:
        return {"label": "Redis", "ok": False, "detail": str(exc)[:200]}


def _fastapi_status() -> dict:
    url = f"{settings.BACKEND_API_URL.rstrip('/')}/health/ready"
    started_at = time.monotonic()
    try:
        request = Request(url, headers={"Accept": "application/json"})
        with urlopen(request, timeout=settings.BACKEND_STATUS_TIMEOUT) as response:
            status_code = response.getcode()
        return {
            "label": "FastAPI",
            "ok": 200 <= status_code < 300,
            "detail": f"HTTP {status_code}，{(time.monotonic() - started_at) * 1000:.0f} ms",
        }
    except HTTPError as exc:
        return {"label": "FastAPI", "ok": False, "detail": f"HTTP {exc.code}"}
    except (URLError, TimeoutError, OSError) as exc:
        return {"label": "FastAPI", "ok": False, "detail": str(exc.reason if isinstance(exc, URLError) else exc)[:200]}


def _safe_count(queryset) -> int | None:
    try:
        return queryset.count()
    except Exception:
        return None


def system_status(request):
    cards = [
        {"label": "用户", "value": _safe_count(User.objects.all()), "url": reverse("admin:user_user_changelist")},
        {
            "label": "会话",
            "value": _safe_count(ChatSession.objects.using("backend").all()),
            "url": reverse("admin:ops_chatsession_changelist"),
        },
        {
            "label": "消息",
            "value": _safe_count(ChatMessage.objects.using("backend").all()),
            "url": reverse("admin:ops_chatmessage_changelist"),
        },
        {
            "label": "笔记",
            "value": _safe_count(Note.objects.using("backend").all()),
            "url": reverse("admin:ops_note_changelist"),
        },
        {
            "label": "回顾记录",
            "value": _safe_count(ReviewRecord.objects.using("backend").all()),
            "url": reverse("admin:ops_reviewrecord_changelist"),
        },
    ]
    context = {
        **admin.site.each_context(request),
        "title": "系统状态",
        "cards": cards,
        "checks": [
            _database_status("default", "用户数据库"),
            _database_status("backend", "业务数据库"),
            _redis_status(),
            _fastapi_status(),
        ],
    }
    return render(request, "admin/ops/system_status.html", context)


def backend_logs(request):
    log_root = Path(settings.BACKEND_LOG_DIR).resolve()
    files = []
    if log_root.is_dir():
        files = sorted(log_root.glob("*.log"), key=lambda item: item.stat().st_mtime, reverse=True)

    selected_name = request.GET.get("file", "")
    selected_file = None
    if selected_name and Path(selected_name).name == selected_name:
        candidate = (log_root / selected_name).resolve()
        if candidate.parent == log_root and candidate.is_file() and candidate.suffix == ".log":
            selected_file = candidate
    elif files:
        selected_file = files[0]

    content = ""
    if selected_file:
        with selected_file.open("r", encoding="utf-8", errors="replace") as handle:
            content = "".join(deque(handle, maxlen=settings.BACKEND_LOG_MAX_LINES))

    context = {
        **admin.site.each_context(request),
        "title": "后端日志",
        "log_files": [
            {"name": item.name, "size": item.stat().st_size, "selected": item == selected_file}
            for item in files
        ],
        "selected_name": selected_file.name if selected_file else "",
        "content": content,
        "log_root": str(log_root),
        "max_lines": settings.BACKEND_LOG_MAX_LINES,
    }
    return render(request, "admin/ops/backend_logs.html", context)
