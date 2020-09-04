from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from .forms import CommentForm, PostForm
from .models import Follow, Group, Post


User = get_user_model()


def index(request):
    post_list = Post.objects.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
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
        is_following = Follow.objects.filter(user=request.user, author=author)
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
    post = get_object_or_404(Post, pk=post_id, author=author)
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
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author=author)
    if not post.author == request.user:
        return redirect('post', username=username, post_id=post.id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )
    if not form.is_valid():
        return render(
            request,
            'new.html',
            {'form': form, 'post': post, 'is_edit': True}
        )
    post = form.save(commit=False)
    post.save()
    return redirect('post', username=username, post_id=post.id)


@login_required
def add_comment(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post = get_object_or_404(Post, pk=post_id, author=author)
    items = post.comments.all()
    form = CommentForm(request.POST or None)
    if not form.is_valid():
        return render(
            request,
            'comments.html',
            {'form': form, 'items': items, 'post': post},
        )
    comment = form.save(commit=False)
    comment.author = request.user
    comment.post = post
    comment.save()
    return redirect('post', username=username, post_id=post.id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, 10)
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
    is_exist = Follow.objects.filter(author=author, user=request.user).exists()
    if author != request.user and not is_exist:
        Follow.objects.create(author=author, user=request.user)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if Follow.objects.filter(author=author, user=request.user).exists():
        Follow.objects.get(author=author, user=request.user).delete()
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
