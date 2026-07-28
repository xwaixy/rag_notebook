from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import AdminUserChangeForm, AdminUserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Django Admin 中的用户管理。系统只允许一个超级管理员。"""

    form = AdminUserChangeForm
    add_form = AdminUserCreationForm
    list_display = (
        "email",
        "username",
        "status",
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined",
        "last_login",
    )
    list_filter = ("status", "is_active", "is_staff", "is_superuser")
    search_fields = ("email", "username", "telephone")
    ordering = ("-date_joined",)
    readonly_fields = ("uuid", "date_joined", "last_login", "is_staff", "is_superuser")
    filter_horizontal = ("groups", "user_permissions")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("个人信息", {"fields": ("username", "telephone", "gender", "bio", "avatar")}),
        ("账号状态", {"fields": ("status", "is_active", "is_staff", "is_superuser")}),
        ("权限", {"fields": ("groups", "user_permissions")}),
        ("时间信息", {"fields": ("uuid", "date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "username", "telephone", "password1", "password2")}),
    )

    def get_form(self, request, obj=None, **kwargs):
        if obj is None:
            kwargs["form"] = self.add_form
        return super().get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def has_delete_permission(self, request, obj=None):
        # 避免从后台误删唯一的超级管理员。
        if obj is not None and obj.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


admin.site.site_header = "RAG NoteBook 管理后台"
admin.site.site_title = "RAG NoteBook 管理后台"
admin.site.index_title = "系统管理"

# Register your models here.
