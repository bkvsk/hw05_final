from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'group': 'Название сообщества:',
            'text': 'Текст записи:',
            'image': 'Изображение:',
        }
        help_texts = {
            'group': 'Необязательное поле. '
                     'Можете выберать сообщество из уже существующих.',
            'text': 'Сюда можно ввести текст записи.',
            'image': 'Необязательное поле. '
                     'Загрузите изображение.',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {'text': 'Комментарий:'}
        help_texts = {'text': 'Сюда можно ввести текст комментария.'}
