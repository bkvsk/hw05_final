from django.contrib import admin
from .models import Comment, Follow, Group, Post


class PostAdmin(admin.ModelAdmin):
    # перечисляем поля, которые должны отображаться в админке
    list_display = (
        "pk",
        "text",
        "pub_date",
        "author",
        "group",
    )
    # добавляем интерфейс для поиска по тексту постов
    search_fields = ("text",)
    # добавляем возможность фильтрации по дате
    list_filter = ("pub_date",)
    empty_value_display = "-пусто-"


class GroupAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "title",
        "slug",
        "description",
    )
    search_fields = ("title",)
    list_filter = ("slug",)
    empty_value_display = "-пусто-"
    prepopulated_fields = {"slug": ("title",)}


class FollowAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "user",
        "author",
    )
    search_fields = ("user",)
    list_filter = ("author",)
    empty_value_display = "-пусто-"


class CommentAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "text",
        "created",
        "author",
        "post",
    )
    search_fields = ("text",)
    list_filter = ("created", "author")
    empty_value_display = "-пусто-"


admin.site.register(Comment, CommentAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Group, GroupAdmin)
admin.site.register(Post, PostAdmin)
