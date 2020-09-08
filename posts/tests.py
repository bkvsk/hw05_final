from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, TestCase
from .models import Follow, Group, Post


User = get_user_model()

# Параметры пользователя 1.
USERNAME_1 = 'luke'
EMAIL_1 = 'l.skywalker@force.com'
PASS_1 = '12345'

# Параметры пользователя 2.
USERNAME_2 = 'darth_vader'
EMAIL_2 = 'a.skywalker@force.com'
PASS_2 = '54321'

# Текст тестового поста.
POST_TEXT = 'May the Force be with you!'
COMMENT_TEXT = 'Why?'

# Параметры группы.
GROUP_TITLE = 'StarWars'
GROUP_SLUG = 'may4'
GROUP_DESC = 'Group for posts about StarWars universe'

# Перечень url-ов.
INDEX_URL = reverse('index')
LOGIN_URL = reverse('login')
NEW_POST_URL = reverse('new_post')
PROFILE1_URL = reverse('profile', kwargs={'username': USERNAME_1})
GROUP_URL = reverse('group', kwargs={'slug': GROUP_SLUG})

# Тестовое изображение.
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
POST_IMG = SimpleUploadedFile(
    name='some.gif',
    content=SMALL_GIF,
    content_type='small/gif',
)


def context_test(test_obj, response, text):
    paginator = response.context.get('paginator')
    if paginator is not None:
        test_obj.assertEqual(paginator.count, 1)
        checked_post = response.context['page'][0]
    else:
        checked_post = response.context['post']
    test_obj.assertEqual(checked_post.text, text)
    test_obj.assertEqual(checked_post.author, test_obj.user_1)
    test_obj.assertEqual(checked_post.group, test_obj.group)


class PostTests(TestCase):

    def setUp(self):
        # Создание авторизованного тестового клиента.
        self.auth_client = Client()
        # Создаём пользователя 1.
        self.user_1 = User.objects.create_user(
            username=USERNAME_1,
            email=EMAIL_1,
            password=PASS_1,
        )
        # Авторизуем пользователя 1.
        self.auth_client.force_login(self.user_1)
        # Создание неавторизованного тестового клиента.
        self.guest_client = Client()
        # Создаём группу постов.
        self.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESC,
        )

    def test_creating_profile_after_signup(self):
        """После регистрации создается персональная страница пользователя."""
        response = self.auth_client.get(PROFILE1_URL)
        self.assertEqual(response.status_code, 200)

    def test_auth_user_post_creating(self):
        """Авторизованный пользователь может опубликовать пост."""
        response = self.auth_client.post(
            NEW_POST_URL,
            {'text': POST_TEXT, 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        context_test(self, response, POST_TEXT)

    def test_guest_user_post_creating(self):
        """Неавторизованный посетитель не может опубликовать пост."""
        response = self.guest_client.post(
            NEW_POST_URL,
            {'text': 'Luke, Im your father', 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        target_url = f'{LOGIN_URL}?next={NEW_POST_URL}'
        self.assertRedirects(response, target_url)

    def test_post_availability(self):
        """После публикации поста новая запись появляется
        на главной странице сайта(index),
        на персональной странице пользователя (profile),
        и на отдельной странице поста (post).
        """
        post = Post.objects.create(
            text='Post for checking',
            group=self.group,
            author=self.user_1,
        )
        url_list = (
            INDEX_URL,
            PROFILE1_URL,
            GROUP_URL,
            reverse(
                'post',
                kwargs={'username': USERNAME_1, 'post_id': post.id}
            ),
        )
        cache.clear()
        for url in url_list:
            response = self.guest_client.get(url)
            context_test(self, response, post.text)

    def test_auth_user_post_editing(self):
        """Авторизованный пользователь может отредактировать свой пост
        и его содержимое изменится на всех связанных страницах.
        """
        post = Post.objects.create(
            text='Post for editing',
            group=self.group,
            author=self.user_1,
        )
        edited_text = 'You underestimate the power of the Dark Side'
        response = self.auth_client.post(
            reverse(
                'post_edit',
                kwargs={'username': USERNAME_1, 'post_id': post.id},
            ),
            {'text': edited_text, 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        context_test(self, response, edited_text)
        # Проверка через ORM.
        edited_post = Post.objects.get(pk=post.id)
        self.assertEqual(edited_post.text, edited_text)

    def test_404(self):
        """Тест на код ошибки 404."""
        response = self.guest_client.get('/404/')
        self.assertEqual(response.status_code, 404)

    def test_with_image(self):
        """Изображение можно добавить к посту."""
        post = Post.objects.create(
            text='Post for testing with image',
            group=self.group,
            author=self.user_1,
            image=POST_IMG,
        )
        url_list = (
            INDEX_URL,
            PROFILE1_URL,
            GROUP_URL,
            reverse(
                'post',
                kwargs={'username': USERNAME_1, 'post_id': post.id}
            ),
        )
        cache.clear()
        for url in url_list:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertContains(response, '<img')

    def test_with_smth_instead_image(self):
        """Неизображение нельзя добавить к посту."""
        not_image = SimpleUploadedFile(
            name='some.txt',
            content=b'abc',
            content_type='text/plain',
        )
        response = self.auth_client.post(
            NEW_POST_URL, {'text': 'Some text', 'image': not_image},
        )
        self.assertFormError(
            response,
            'form',
            'image',
            errors='Загрузите правильное изображение. '
                   'Файл, который вы загрузили, '
                   'поврежден или не является изображением.',
        )

    def test_cache(self):
        """Тест кеширования главной страницы."""
        cache.clear()
        post_1 = Post.objects.create(
            text='Post 1 for cache test ',
            group=self.group,
            author=self.user_1,
        )
        response = self.guest_client.get(INDEX_URL)
        self.assertContains(response, post_1.text)
        post_2 = Post.objects.create(
            text='Post 2 for cache test ',
            group=self.group,
            author=self.user_1,
        )
        response = self.guest_client.get(INDEX_URL)
        self.assertNotContains(response, post_2.text)
        cache.clear()
        response = self.guest_client.get(INDEX_URL)
        self.assertContains(response, post_2.text)

    def test_guest_user_comment_sending(self):
        """Неавторизованный посетитель не может оставить комментарий."""
        post = Post.objects.create(
            text='Post for comment',
            group=self.group,
            author=self.user_1,
        )
        response = self.guest_client.post(
            reverse(
                'add_comment',
                kwargs={'username': USERNAME_2, 'post_id': post.id},
            ),
            {'text': COMMENT_TEXT},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        comment_url = reverse(
            'add_comment',
            kwargs={'username': USERNAME_2, 'post_id': post.id},
        )
        target_url = f'{LOGIN_URL}?next={comment_url}'
        self.assertRedirects(response, target_url)

    def test_auth_user_comment_sending(self):
        """Авторизованный посетитель не может оставить комментарий."""
        post = Post.objects.create(
            text='Post for comment',
            group=self.group,
            author=self.user_1,
        )
        response = self.auth_client.post(
            reverse(
                'add_comment',
                kwargs={'username': USERNAME_1, 'post_id': post.id},
            ),
            {'text': COMMENT_TEXT},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        checked_comment = response.context['items'][0]
        self.assertEqual(checked_comment.text, COMMENT_TEXT)


PROFILE2_URL = reverse('profile', kwargs={'username': USERNAME_2})
PROFILE2_FOLLOW_URL = reverse(
    'profile_follow',
    kwargs={'username': USERNAME_2},
)
PROFILE2_UNFOLLOW_URL = reverse(
    'profile_unfollow',
    kwargs={'username': USERNAME_2},
)
FOLLOW_INDEX_URL = reverse('follow_index')


class FollowTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(
            title=GROUP_TITLE,
            slug=GROUP_SLUG,
            description=GROUP_DESC,
        )

        self.auth_client1 = Client()
        self.user1 = User.objects.create_user(
            username=USERNAME_1,
            email=EMAIL_1,
            password=PASS_1,
        )
        self.auth_client1.force_login(self.user1)
        self.post1 = Post.objects.create(
            text='Post 1 for following test',
            group=self.group,
            author=self.user1,
        )

        self.auth_client2 = Client()
        self.user2 = User.objects.create_user(
            username=USERNAME_2,
            email=EMAIL_2,
            password=PASS_2,
        )
        self.auth_client2.force_login(self.user2)
        self.post2 = Post.objects.create(
            text='Post 2 for following test',
            group=self.group,
            author=self.user2,
        )

    def test_follow_button(self):
        user2_profile = self.auth_client1.get(PROFILE2_URL)
        self.assertContains(user2_profile, 'Подписаться')

    def test_following_user(self):
        self.auth_client1.get(PROFILE2_FOLLOW_URL)
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unfollow_button(self):
        Follow.objects.create(
            user=self.user1,
            author=self.user2,
        )
        user2_profile = self.auth_client1.get(PROFILE2_URL)
        self.assertContains(user2_profile, 'Отписаться')

    def test_unfollowing_user(self):
        Follow.objects.create(
            user=self.user1,
            author=self.user2,
        )
        self.auth_client1.get(PROFILE2_UNFOLLOW_URL)
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_follow_index(self):
        Follow.objects.create(
            user=self.user1,
            author=self.user2,
        )
        self.assertEqual(Follow.objects.all().count(), 1)
        response = self.auth_client1.get(FOLLOW_INDEX_URL)
        paginator = response.context.get('paginator')
        self.assertEqual(paginator.count, 1)

    def test_unfollow_index(self):
        response = self.auth_client2.get(FOLLOW_INDEX_URL)
        paginator = response.context.get('paginator')
        self.assertEqual(paginator.count, 0)
