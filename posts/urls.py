from django.urls import path
from . import views


urlpatterns = [
    # path('404/', views.page_not_found, {'exception': None}, name='404'),
    # path('500/', views.server_error, name='500'),
    path(
        '',
        views.index,
        name='index',
    ),
    # Сообщества
    path(
        'group/<slug:slug>/',
        views.group_posts,
        name='group',
    ),
    # Новая запись
    path(
        'new/',
        views.new_post,
        name='new_post',
    ),
    # Подписки
    path(
        'follow/',
        views.follow_index,
        name='follow_index',
    ),
    # Профайл пользователя
    path(
        '<str:username>/',
        views.profile,
        name='profile',
    ),
    # Просмотр записи
    path(
        '<str:username>/<int:post_id>/',
        views.post_view,
        name='post',
    ),
    # Редактирование записи
    path(
        '<str:username>/<int:post_id>/edit/',
        views.post_edit,
        name='post_edit',
    ),
    # Добавление комментария
    path(
        '<username>/<int:post_id>/comment',
        views.add_comment,
        name='add_comment',
    ),
    # Подписаться
    path(
        '<str:username>/follow/',
        views.profile_follow,
        name='profile_follow',
    ),
    # Отписаться
    path(
        '<str:username>/unfollow/',
        views.profile_unfollow,
        name='profile_unfollow',
    ),
]
