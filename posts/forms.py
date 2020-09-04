from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'group': 'Название группы:',
            'text': 'Текст поста:',
            'image': 'Изображение:',
        }
        help_texts = {
            'group': 'Необязательное поле. '
                     'Выберите группу из уже существующих.',
            'text': 'Сюда можно ввести текст поста.',
            'image': 'Необязательное поле. '
                     'Загрузите изображение.',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {'text': 'Комментарий:'}
        help_texts = {'text': 'Сюда можно ввести текст комментария.'}
