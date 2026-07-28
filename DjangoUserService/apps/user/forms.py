from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import User, UserStatusChoice


class AdminUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="密码", widget=forms.PasswordInput)
    password2 = forms.CharField(label="确认密码", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("email", "username", "telephone")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("两次输入的密码不一致")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        user.status = UserStatusChoice.ACTIVE
        user.is_active = True
        if commit:
            user.save()
        return user


class AdminUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="密码",
        help_text="密码不会以明文显示。如需修改，请使用后台用户页面中的修改密码功能。",
    )

    class Meta:
        model = User
        fields = "__all__"

    def clean_password(self):
        return self.initial["password"]
