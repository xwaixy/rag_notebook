from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from shortuuidfield import ShortUUIDField

class UserStatusChoice(models.IntegerChoices):
    """
    用户状态选择
    """
    LOCKED = 2, "已锁定"
    ACTIVE = 1, "已激活"
    DISABLED = 0, "未激活"

class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user_object(self, username, email, password, **extra_fields):
        """
        创建并返回一个新的用户对象，而不保存到数据库中。
        """
        if not username:
            raise ValueError("用户名不能为空")

        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.password = make_password(password)
        return user

    def _create_user(self, username, email, password, **extra_fields):
        """
        创建并保存一个普通用户，使用提供的用户名、电子邮件和密码。
        """
        user = self._create_user_object(username, email, password, **extra_fields)
        user.save(using=self._db)
        return user

    async def _acreate_user(self, username, email, password, **extra_fields):
        """
        异步创建并保存一个普通用户，使用提供的用户名、电子邮件和密码。
        """
        user = self._create_user_object(username, email, password, **extra_fields)
        await user.asave(using=self._db)
        return user

    def create_user(self, username, email=None, password=None, **extra_fields):
        return self._create_user(username, email, password, **extra_fields)

    create_user.alters_data = True

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        """创建唯一的 Django Admin 超级管理员。"""
        if self.model.objects.filter(is_superuser=True).exists():
            raise ValueError("系统只允许创建一个超级管理员")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("status", UserStatusChoice.ACTIVE)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("超级管理员必须设置 is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("超级管理员必须设置 is_superuser=True")

        return self._create_user(username, email, password, **extra_fields)

    create_superuser.alters_data = True

    async def acreate_user(self, username, email=None, password=None, **extra_fields):
        return await self._acreate_user(username, email, password, **extra_fields)

    acreate_user.alters_data = True

class GenderChoice(models.IntegerChoices):
    """
    性别选择
    """
    MALE = 1, "男"
    FEMALE = 2, "女"
    OTHER = 3, "其他"

class User(AbstractBaseUser, PermissionsMixin):
    """
    自定义用户模型，继承自AbstractBaseUser
    """
    uuid = ShortUUIDField(primary_key=True, unique=True, editable=False)
    username = models.CharField(
        max_length=150,
        unique=False,
    )
    email = models.EmailField(unique=True, blank=False)
    telephone = models.CharField(max_length=11, unique=True,null=True, blank=False)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    # 用户状态， 只需要关注status字段
    status = models.IntegerField(
        choices=UserStatusChoice,
        default=UserStatusChoice.DISABLED
    )
    # 性别
    gender = models.IntegerField(
        choices=GenderChoice,
        null=True, blank=True
    )
    # 个人简介
    bio = models.TextField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)
    avatar = models.CharField(max_length=255, null=True, blank=True)

    # 确保管理器引用正确
    objects = UserManager()

    EMAIL_FIELD = "email"
    # 这里的USERNAME_FIELD是用来鉴权的，在authenticate方法中会使用到
    USERNAME_FIELD = "email"
    # 这里的REQUIRED_FIELDS是用来创建用户时必填的字段，在create_user方法中会使用到
    REQUIRED_FIELDS = ["username"]

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def get_full_name(self):
        return self.username

    def get_short_name(self):
        return self.username

    def save(self, *args, **kwargs):
        """保证数据库中最多存在一个超级管理员。"""
        if self.is_superuser:
            existing_admins = type(self).objects.filter(is_superuser=True)
            if self.pk:
                existing_admins = existing_admins.exclude(pk=self.pk)
            if existing_admins.exists():
                raise ValidationError("系统只允许存在一个超级管理员")

            self.is_staff = True
            self.is_active = True
            self.status = UserStatusChoice.ACTIVE
        else:
            # 本项目只有一个管理员，普通用户不能获得 Django Admin 访问权。
            self.is_staff = False

        return super().save(*args, **kwargs)

    class Meta:
        db_table = 'user_service'
