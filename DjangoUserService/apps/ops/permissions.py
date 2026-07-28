from rest_framework.permissions import BasePermission


class IsSuperUser(BasePermission):
    """仅允许唯一的超级管理员访问管理接口。"""

    message = "只有管理员可以访问此功能"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and user.is_active
            and user.is_superuser
        )
