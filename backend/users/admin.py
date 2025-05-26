from django.contrib import admin

from .models import Subscription, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name')
    list_filter = ('username', 'email')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_per_page = 20
    ordering = ('username',)
    fieldsets = (
        ('Основное', {
            'fields': ('username', 'email', 'password')
        }),
        ('Имя и фамилия', {
            'fields': ('first_name', 'last_name')
        }),
        ('Права доступа', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups')
        }),
        ('Даты', {
            'fields': ('last_login', 'date_joined')
        }),
    )
    readonly_fields = ('last_login', 'date_joined')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'subscriber', 'author')
    search_fields = ('subscriber__username', 'author__username')
    list_filter = ('author', 'subscriber')
    list_per_page = 20
