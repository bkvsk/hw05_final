from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import Client, TestCase
from .models import Follow, Group, Post


User = get_user_model()


def context_test(self, response, text):
    paginator = response.context.get('paginator')
    if paginator is not None:
        self.assertEqual(paginator.count, 1)
        post = response.context['page'][0]
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
    else:
        post = response.context['post']
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
    #else:
    #    self.assertTrue(
    #        False,
    #        msg='В контекст шаблона ничего не передаётся!'
    #    )


class AppTests(TestCase):

    def setUp(self):
        # создание тестового клиента
        self.client = Client()
        # создаём авторизованного пользователя
        self.auth_user = User.objects.create_user(
            username='luke',
            email='l.skywalker@force.com',
            password='12345',
        )
        # создаём неавторизованного пользователя
        self.guest_user = User.objects.create_user(
            username='darth_vader',
            email='a.skywalker@force.com',
            password='54321',
        )
        # создаём группу постов
        self.group = Group.objects.create(
            title='StarWars',
            slug='may4',
            description='Group for posts about StarWars universe',
        )
        # создаём поста от имени авторизованного пользователя
        self.post = Post.objects.create(
            text='May the Force be with you!',
            group=self.group,
            author=self.auth_user,
        )

    def test_creating_profile_after_signup(self):
        """После регистрации создается персональная страница пользователя"""
        response = self.client.get(reverse(
            'profile',
            kwargs={'username': self.auth_user.username},
        ))
        self.assertEqual(response.status_code, 200)

    def test_auth_user_post_creating(self):
        """Авторизованный пользователь может опубликовать пост"""
        self.client.force_login(self.auth_user)
        response = self.client.post(
            reverse('new_post'),
            {'text': self.post.text, 'group': self.post.group},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('index'))
        context_test(self, response, self.post.text)

    def test_guest_user_post_creating(self):
        """Неавторизованный посетитель не может опубликовать пост"""
        response = self.client.post(
            reverse('new_post'),
            {'text': 'Luke, Im your father', 'group': self.post.group},
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
        username = self.auth_user.username
        post_id = self.post.id
        url_list = (
            reverse('index'),
            reverse('profile', kwargs={'username': username}),
            reverse('post', kwargs={'username': username, 'post_id': post_id})
        )
        cache.clear()
        for url in url_list:
            response = self.client.get(url)
            context_test(self, response, self.post.text)

    def test_auth_user_post_editing(self):
        """Авторизованный пользователь может отредактировать свой пост
        и его содержимое изменится на всех связанных страницах
        """
        self.client.force_login(self.auth_user)
        username = self.auth_user.username
        post_id = self.post.id
        edited_text = 'You underestimate the power of the Dark Side'
        response = self.client.post(
            reverse(
                'post_edit',
                kwargs={'username': username, 'post_id': post_id},
            ),
            {'text': edited_text, 'group': self.group.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        url_list = (
            reverse('index'),
            reverse('profile', kwargs={'username': username}),
            reverse('post', kwargs={'username': username, 'post_id': post_id})
        )
        cache.clear()
        for url in url_list:
            response = self.client.get(url)
            context_test(self, response, edited_text)

    def test_404(self):
        response = self.client.get('/404/')
        self.assertEqual(response.status_code, 404)

    def test_with_image(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile(
            name='some.gif',
            content=small_gif,
            content_type='small/gif',
        )
        self.client.force_login(self.auth_user)
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
        post = Post.objects.get(text='Post for testing with image')
        username = self.auth_user.username
        urls = [
            reverse('index'),
            reverse(
                'profile',
                kwargs={'username': username},
            ),
            reverse(
                'post',
                kwargs={'username': username, 'post_id': post.id},
            ),
            reverse(
                'group',
                kwargs={'slug': self.group.slug},
            ),
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
        cache.clear()
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
            reverse(
                'add_comment',
                kwargs={'username': author, 'post_id': post_id},
            ),
            {'text': 'Why?'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        login_url = reverse('login')
        comment_url = reverse(
            'add_comment',
            kwargs={'username': author, 'post_id': post_id},
        )
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
