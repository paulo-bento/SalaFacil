
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações pessoais", {
            "fields": ("first_name", "last_name"),
        }),
        ("Permissões", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Datas importantes", {
            "fields": ("last_login", "date_joined"),
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "usable_password",
                "password1",
                "password2",
            ),
        }),
    )

    search_fields = ("email", "first_name", "last_name")
