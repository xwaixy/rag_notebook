from django.urls import path

from .api_views import (
    AdminBusinessDataView,
    AdminDashboardView,
    AdminLogsView,
    AdminUserListView,
    AdminUserStatusView,
)

app_name = "ops"

urlpatterns = [
    path("dashboard/", AdminDashboardView.as_view(), name="dashboard"),
    path("users/", AdminUserListView.as_view(), name="users"),
    path("users/<str:user_id>/status/", AdminUserStatusView.as_view(), name="user-status"),
    path("business/", AdminBusinessDataView.as_view(), name="business"),
    path("logs/", AdminLogsView.as_view(), name="logs"),
]
