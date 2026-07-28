from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.user.models import User, UserStatusChoice

from .api_views import (
    AdminLogsView,
    AdminUserListView,
    AdminUserStatusView,
)


class AdminApiPermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.admin = User.objects.create_superuser(
            username="owner",
            email="owner@example.com",
            password="owner-password",
        )
        self.user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="member-password",
            status=UserStatusChoice.ACTIVE,
        )

    def request(self, view, method="get", user=None, data=None, **kwargs):
        request = getattr(self.factory, method)("/ops/test/", data=data, format="json")
        if user is not None:
            force_authenticate(request, user=user)
        return view.as_view()(request, **kwargs)

    def test_anonymous_user_receives_401(self):
        response = self.request(AdminUserListView)

        self.assertEqual(response.status_code, 401)

    def test_regular_user_receives_403(self):
        response = self.request(AdminUserListView, user=self.user)

        self.assertEqual(response.status_code, 403)

    def test_superuser_can_list_users(self):
        response = self.request(AdminUserListView, user=self.admin)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["total"], 2)

    def test_regular_user_cannot_update_user_status(self):
        response = self.request(
            AdminUserStatusView,
            method="patch",
            user=self.user,
            data={"status": UserStatusChoice.DISABLED},
            user_id=str(self.admin.uuid),
        )

        self.assertEqual(response.status_code, 403)

    @patch("apps.ops.api_views.clear_user_cache")
    def test_admin_can_update_regular_user_status(self, clear_cache):
        response = self.request(
            AdminUserStatusView,
            method="patch",
            user=self.admin,
            data={"status": UserStatusChoice.DISABLED},
            user_id=str(self.user.uuid),
        )

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.status, UserStatusChoice.DISABLED)
        self.assertFalse(self.user.is_active)
        clear_cache.assert_called_once_with(self.user.uuid)

    def test_admin_cannot_update_own_status(self):
        response = self.request(
            AdminUserStatusView,
            method="patch",
            user=self.admin,
            data={"status": UserStatusChoice.DISABLED},
            user_id=str(self.admin.uuid),
        )

        self.assertEqual(response.status_code, 400)

    def test_logs_reject_path_traversal(self):
        with TemporaryDirectory() as directory:
            Path(directory, "app.log").write_text("safe log\n", encoding="utf-8")
            with override_settings(BACKEND_LOG_DIR=directory):
                response = self.request(
                    AdminLogsView,
                    user=self.admin,
                    data={"file": "../secret.log"},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["selected"], "")
