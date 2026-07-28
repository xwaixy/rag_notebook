from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import User, UserStatusChoice


class AdminUserTests(TestCase):
    def test_only_one_superuser_can_be_created(self):
        admin_user = User.objects.create_superuser(
            username="owner",
            email="owner@example.com",
            password="safe-test-password",
        )

        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        self.assertTrue(admin_user.is_active)
        self.assertEqual(admin_user.status, UserStatusChoice.ACTIVE)

        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                username="second-owner",
                email="second-owner@example.com",
                password="safe-test-password",
            )

    def test_model_save_also_rejects_second_superuser(self):
        User.objects.create_superuser(
            username="owner",
            email="owner@example.com",
            password="safe-test-password",
        )
        another_admin = User(
            username="second-owner",
            email="second-owner@example.com",
            is_superuser=True,
            is_staff=True,
        )

        with self.assertRaises(ValidationError):
            another_admin.save()

    def test_regular_user_cannot_gain_admin_access(self):
        user = User.objects.create_user(
            username="member",
            email="member@example.com",
            password="safe-test-password",
            is_staff=True,
            status=UserStatusChoice.ACTIVE,
            is_active=True,
        )

        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
