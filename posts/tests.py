from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from .models import Post, Group, Follow
from django.contrib.auth import get_user_model
from django.urls import reverse


User = get_user_model()


class AppTest(TestCase):

    def setUp(self):
        # создание тестового клиента
        self.client = Client()
        # создаём авторизованного пользователя
        self.auth_user = User.objects.create_user(
            username='luke', email='skywalker.l@force.com', password='12345'
        )
        # создаём неавторизованного пользователя
        self.guest_user = User.objects.create_user(
            username='darth_vader', email='skywalker.a@force.com', password='54321'
        )
        # создаём группу постов
        self.group = Group.objects.create(
            title='StarWars',
            slug='may4',
            description='Group for posts about StarWars universe',
        )
        # создаём содержание формы поста от имени авторизованного пользователя
        self.post_ctx = {
            'text': 'May the Force be with you!',
            'group': self.group.id,
            'author': self.auth_user.id,
        }

    def test_profile(self):
        """После регистрации пользователя создается
        его персональная страница (profile)
        """
        response = self.client.get(reverse('profile', kwargs={'username': self.auth_user.username}))
        self.assertEqual(response.status_code, 200)

    def test_creating_post(self):
        """Авторизованный пользователь может опубликовать пост (new)"""
        self.client.force_login(self.auth_user)
        response = self.client.post(
            reverse('new_post'),
            {'text': 'May the Force be with you!', 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('index'))
        paginator = response.context.get('paginator')
        if paginator is not None:
            self.assertEqual(paginator.count, 1)
            post = response.context['page'][0]
            self.assertEqual(post.text, self.post_ctx['text'])
            self.assertEqual(post.author.id, self.post_ctx['author'])
            self.assertEqual(post.group.id, self.post_ctx['group'])
        else:
            self.assertTrue(False, msg='В контекст шаблона '
                                       'ничего не передаётся')

    def test_guest(self):
        """Неавторизованный посетитель не может опубликовать пост
        (его редиректит на страницу входа)
        """
        response = self.client.post(
            reverse('new_post'),
            {'text': 'Luke, Im your father', 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        login_url = reverse('login')
        new_post_url = reverse('new_post')
        target_url = f'{login_url}?next={new_post_url}'
        self.assertRedirects(response, target_url)

    def test_post_availability(self):
        """После публикации поста новая запись появляется
        на главной странице сайта(index),
        на персональной странице пользователя (profile),
        и на отдельной странице поста (post)
        """
        self.post = Post.objects.create(
            text='New hope',
            group=self.group,
            author=self.auth_user,
        )
        username = self.auth_user.username
        post_id = self.post.id
        url_list = (
            reverse('index'),
            reverse('profile', kwargs={'username': self.auth_user.username}),
            reverse('post', kwargs={'username': username, 'post_id': post_id})
        )
        cache.clear()
        for url in url_list:
            response = self.client.get(url)
            self.assertContains(response, self.post.text)

    def test_editing_post(self):
        """Авторизованный пользователь может отредактировать свой пост
        и его содержимое изменится на всех связанных страницах
        """
        self.client.force_login(self.auth_user)
        self.post = Post.objects.create(
            text='Post for editing',
            group=self.group,
            author=self.auth_user,
        )
        username = self.auth_user.username
        post_id = self.post.id
        response = self.client.post(
            reverse('post_edit',
                    kwargs={'username': username, 'post_id': post_id}),
            {'text': 'Edited post', 'group': self.group.id},
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        ed_post = Post.objects.get(author=self.auth_user.id)
        url_list = (
            reverse('index'),
            reverse('profile', kwargs={'username': username}),
            reverse('post', kwargs={'username': username, 'post_id': post_id})
        )
        cache.clear()
        for url in url_list:
            response = self.client.get(url)
            self.assertContains(response, ed_post.text)

    def test_404(self):
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)

    def test_with_image(self):
        self.client.force_login(self.auth_user)
        with open('media/posts/bkvsk.jpg', 'rb') as img:
            self.client.post(
                reverse('new_post'),
                {
                    'text': 'Post for testing with image',
                    'group': self.group.id,
                    'author': self.auth_user,
                    'image': img,
                },
                follow=True,
            )
        post = Post.objects.get(id=1)
        urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.auth_user}),
            reverse('post', kwargs={'username': self.auth_user, 'post_id': post.id}),
            reverse('group', kwargs={'slug': self.group.slug}),
        ]
        cache.clear()
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, '<img')

    def test_with_not_image(self):
        self.client.force_login(self.auth_user)
        not_image = SimpleUploadedFile(
            name='some.txt',
            content=b'abc',
            content_type='text/plain',
        )

        url = reverse('new_post')
        response = self.client.post(
            url, {'text': 'some_text', 'image': not_image},
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
        self.post_1 = Post.objects.create(
            text='Post 1 for cache test ',
            group=self.group,
            author=self.auth_user,
        )
        response = self.client.get(reverse('index'))
        self.assertContains(response, self.post_1.text)
        self.post_2 = Post.objects.create(
            text='Post 2 for cache test ',
            group=self.group,
            author=self.auth_user,
        )
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, self.post_2.text)
        cache.clear()
        response = self.client.get(reverse('index'))
        self.assertContains(response, self.post_2.text)

    def test_comment(self):
        self.post = Post.objects.create(
            text='Post for comment',
            group=self.group,
            author=self.auth_user,
        )
        post_id = self.post.id
        author = self.auth_user.username
        response = self.client.post(
            reverse('add_comment', kwargs={'username': author, 'post_id': post_id}),
            {'text': 'Why?'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        login_url = reverse('login')
        comment_url = reverse('add_comment', kwargs={'username': author, 'post_id': post_id})
        target_url = f'{login_url}?next={comment_url}'
        self.assertRedirects(response, target_url)


class FollowTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(
            username="first_user",
            email="first_user@testmail.by",
            password="firstuserpass",
        )
        self.post1 = Post.objects.create(
            text="test message", author=self.user1,
        )
        self.user2 = User.objects.create_user(
            username="second_user",
            email="second_user@testmail.by",
            password="seconduserpass",
        )
        self.user3 = User.objects.create_user(
            username="third_user",
            email="third_user@testmail.by",
            password="thirduserpass",
        )

    def test_following_unfollowing_user(self):
        self.client.force_login(self.user1)
        user2_profile = self.client.get(
            reverse("profile", args=[self.user2.username]
                    ))
        self.assertContains(user2_profile, "Подписаться")
        follow_user2 = self.client.get(
            reverse("profile_follow", args=[self.user2.username]
                    ))
        self.assertEqual(len(Follow.objects.all()), 1)
        user2_profile = self.client.get(
            reverse("profile", args=[self.user2.username]
                    ))
        self.assertContains(user2_profile, "Отписаться")
        unfollow_user2 = self.client.get(
            reverse("profile_unfollow", args=[self.user2.username]
                    ))
        self.assertEqual(len(Follow.objects.all()), 0)

    def test_post_follow(self):
        self.client.force_login(self.user2)
        follow_user1 = self.client.get(
            reverse("profile_follow", args=[self.user1.username]
                    ))
        self.assertEqual(len(Follow.objects.all()), 1)
        response = self.client.get(reverse("follow_index"))
        self.assertContains(response, self.post1.text)
        self.client.force_login(self.user3)
        response = self.client.get(reverse("follow_index"))
        self.assertNotContains(response, self.post1.text)
