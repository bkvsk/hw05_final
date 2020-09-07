from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, TestCase
from .models import Follow, Group, Post


User = get_user_model()

# Параметры пользователя 1.
username_1 = 'luke'
email_1 = 'l.skywalker@force.com'
pass_1 = '12345'

# Параметры пользователя 2.
username_2 = 'darth_vader'
email_2 = 'a.skywalker@force.com'
pass_2 = '54321'

# Текст тестового поста.
post_text = 'May the Force be with you!'

# Параметры группы.
group_title = 'StarWars'
group_slug = 'may4'
group_desc = 'Group for posts about StarWars universe'

# Перечень url-ов.
index_url = reverse('index')
login_url = reverse('login')
new_post_url = reverse('new_post')
profile1_url = reverse('profile', kwargs={'username': username_1})
group_url = reverse('group', kwargs={'slug': group_slug})

# Тестовое изображение.
small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
post_img = SimpleUploadedFile(
    name='some.gif',
    content=small_gif,
    content_type='small/gif',
)


# Внутри класса данный метод не работает,
# т.к. внутриклассовые методы не знают о существовании друг друга.
def context_test(self, response, text):
    def equals_tests(checked_post):
        self.assertEqual(checked_post.text, text)
        self.assertEqual(checked_post.author, self.user_1)
        self.assertEqual(checked_post.group, self.group)

    paginator = response.context.get('paginator')
    if paginator is not None:
        self.assertEqual(paginator.count, 1)
        get_post = response.context['page'][0]
        equals_tests(get_post)
    else:
        get_post = response.context['post']
        equals_tests(get_post)


class PostTests(TestCase):

    def setUp(self):
        # Создание авторизованного тестового клиента.
        self.auth_client = Client()
        # Создаём пользователя 1.
        self.user_1 = User.objects.create_user(
            username=username_1,
            email=email_1,
            password=pass_1,
        )
        # Авторизуем пользователя 1.
        self.auth_client.force_login(self.user_1)
        # Создание неавторизованного тестового клиента.
        self.guest_client = Client()
        # Создаём группу постов.
        self.group = Group.objects.create(
            title=group_title,
            slug=group_slug,
            description=group_desc,
        )

    def test_creating_profile_after_signup(self):
        """После регистрации создается персональная страница пользователя."""
        response = self.auth_client.get(profile1_url)
        self.assertEqual(response.status_code, 200)

    def test_auth_user_post_creating(self):
        """Авторизованный пользователь может опубликовать пост."""
        response = self.auth_client.post(
            new_post_url,
            {'text': post_text, 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        context_test(self, response, post_text)

    def test_guest_user_post_creating(self):
        """Неавторизованный посетитель не может опубликовать пост."""
        response = self.guest_client.post(
            new_post_url,
            {'text': 'Luke, Im your father', 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        target_url = f'{login_url}?next={new_post_url}'
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
            index_url,
            profile1_url,
            group_url,
            reverse(
                'post',
                kwargs={'username': username_1, 'post_id': post.id}
            ),
        )
        cache.clear()
        for url in url_list:
            response = self.client.get(url)
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
                kwargs={'username': username_1, 'post_id': post.id},
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
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)

    # Проверить картинку через ORM у меня не получилось.
    def test_with_image(self):
        post = Post.objects.create(
            text='Post for testing with image',
            group=self.group,
            author=self.user_1,
            image=post_img,
        )
        url_list = (
            index_url,
            profile1_url,
            group_url,
            reverse(
                'post',
                kwargs={'username': username_1, 'post_id': post.id}
            ),
        )
        cache.clear()
        for url in url_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<img')

    def test_with_smth_instead_image(self):
        not_image = SimpleUploadedFile(
            name='some.txt',
            content=b'abc',
            content_type='text/plain',
        )
        response = self.auth_client.post(
            new_post_url, {'text': 'Some text', 'image': not_image},
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
        cache.clear()
        post_1 = Post.objects.create(
            text='Post 1 for cache test ',
            group=self.group,
            author=self.user_1,
        )
        response = self.client.get(reverse('index'))
        self.assertContains(response, post_1.text)
        post_2 = Post.objects.create(
            text='Post 2 for cache test ',
            group=self.group,
            author=self.user_1,
        )
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, post_2.text)
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, post_2.text)

    def test_comment(self):
        post = Post.objects.create(
            text='Post for comment',
            group=self.group,
            author=self.user_1,
        )
        response = self.client.post(
            reverse(
                'add_comment',
                kwargs={'username': username_1, 'post_id': post.id},
            ),
            {'text': 'Why?'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        comment_url = reverse(
            'add_comment',
            kwargs={'username': username_1, 'post_id': post.id},
        )
        target_url = f'{login_url}?next={comment_url}'
        self.assertRedirects(response, target_url)


profile2_url = reverse('profile', kwargs={'username': username_2})
profile2_follow_url = reverse(
    'profile_follow',
    kwargs={'username': username_2},
)
profile2_unfollow_url = reverse(
    'profile_unfollow',
    kwargs={'username': username_2},
)
follow_index_url = reverse('follow_index')


class FollowTest(TestCase):
    def setUp(self):
        self.group = Group.objects.create(
            title=group_title,
            slug=group_slug,
            description=group_desc,
        )

        self.auth_client1 = Client()
        self.user1 = User.objects.create_user(
            username=username_1,
            email=email_1,
            password=pass_1,
        )
        self.auth_client1.force_login(self.user1)
        self.post1 = Post.objects.create(
            text='Post 1 for following test',
            group=self.group,
            author=self.user1,
        )

        self.auth_client2 = Client()
        self.user2 = User.objects.create_user(
            username=username_2,
            email=email_2,
            password=pass_2,
        )
        self.auth_client2.force_login(self.user2)
        self.post2 = Post.objects.create(
            text='Post 2 for following test',
            group=self.group,
            author=self.user2,
        )

    def test_following_user(self):
        user2_profile = self.auth_client1.get(profile2_url)
        self.assertContains(user2_profile, 'Подписаться')
        self.auth_client1.get(profile2_follow_url)
        self.assertEqual(len(Follow.objects.all()), 1)

    def test_unfollowing_user(self):
        Follow.objects.create(
            user=self.user1,
            author=self.user2,
        )
        user2_profile = self.auth_client1.get(profile2_url)
        self.assertContains(user2_profile, 'Отписаться')
        self.auth_client1.get(profile2_unfollow_url)
        self.assertEqual(len(Follow.objects.all()), 0)

    def test_post_follow(self):
        self.auth_client1.get(profile2_follow_url)
        self.assertEqual(len(Follow.objects.all()), 1)
        response = self.auth_client1.get(follow_index_url)
        paginator = response.context.get('paginator')
        self.assertEqual(paginator.count, 1)
        response = self.auth_client2.get(follow_index_url)
        paginator = response.context.get('paginator')
        self.assertEqual(paginator.count, 0)
