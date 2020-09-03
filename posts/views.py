from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from .models import Post, Group, Follow
from .forms import PostForm, CommentForm

User = get_user_model()


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)  # показывать по 10 записей на странице.
    page_number = request.GET.get('page')  # переменная в URL с номером запрошенной страницы
    page = paginator.get_page(page_number)  # получить записи с нужным смещением
    return render(
        request,
        'index.html',
        {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'group.html',
        {'group': group, 'page': page, 'paginator': paginator}
    )


@login_required
def new_post(request):
    if not request.method == 'POST':
        form = PostForm()
        return render(request, 'new.html', {'form': form})
    form = PostForm(request.POST, files=request.FILES or None)
    if not form.is_valid():
        return render(request, 'new.html', {'form': form})
    post_get = form.save(commit=False)
    post_get.author = request.user
    post_get.save()
    return redirect('index')


def profile(request, username):
    author = get_object_or_404(User, username=username)
    is_following = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(user__username=request.user,
                                          author=author)
    followers = Follow.objects.filter(author=author)
    followings = Follow.objects.filter(user=author)
    posts = author.posts.all()
    paginator = Paginator(posts, 5)
    page = paginator.get_page(request.GET.get('page'))
    return render(request, 'profile.html', {
        'author': author,
        'posts': posts,
        'paginator': paginator,
        'page': page,
        'is_following': is_following,
        'followers': followers,
        'followings': followings,
    })


def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    posts_count = author.posts.all().count()
    items = post.comments.all()
    form = CommentForm()
    return render(request, 'post.html', {
        'author': author,
        'post': post,
        'posts_count': posts_count,
        'form': form,
        'items': items,
    })


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    if not post.author == request.user:
        return redirect('post', username=post.author, post_id=post.id)

    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    form_content = {'form': form, 'post': post, 'is_edit': True}

    if not request.method == 'POST':
        return render(request, 'new.html', form_content)

    if not form.is_valid():
        return render(request, 'new.html', form_content)

    post = form.save(commit=False)
    post.save()
    return redirect('post', username=post.author, post_id=post.id)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    items = post.comments.all()
    if not request.method == 'POST':
        form = CommentForm()
        content = {'form': form, 'items': items, 'post': post}
        return render(request, 'comments.html', content)
    form = CommentForm(request.POST or None)
    content = {'form': form, 'items': items, 'post': post}
    if not form.is_valid():
        return render(request, 'comments.html', content)
    comment = form.save(commit=False)
    comment.author = request.user
    comment.post = post
    comment.save()
    return redirect('post', username=post.author, post_id=post.id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        'follow.html',
        {'page': page, 'paginator': paginator}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    unfollow = Follow.objects.get(author__username=username, user=request.user)
    if Follow.objects.filter(pk=unfollow.pk).exists():
        unfollow.delete()
    return redirect('profile', username=username)


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)
