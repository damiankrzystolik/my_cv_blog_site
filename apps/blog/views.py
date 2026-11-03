from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from taggit.models import Tag

from apps.core.exceptions import BusinessLogicError
from apps.core.utils import get_client_ip

from .forms import CommentForm, SearchForm
from .models import Post
from .selectors import PostSelector
from .services import CommentService


def post_list(request, tag_slug=None):
    tag = get_object_or_404(Tag, slug=tag_slug) if tag_slug else None
    paginator = Paginator(PostSelector.published(tag=tag), settings.BLOG_POSTS_PER_PAGE)
    posts = paginator.get_page(request.GET.get("page"))
    return render(request, "blog/post/list.html", {"posts": posts, "tag": tag})


def post_detail(request, year, month, day, post):
    post = PostSelector.get_published(year, month, day, post)
    return _render_detail(request, post, CommentForm())


@require_POST
def post_comment(request, post_id):
    post = get_object_or_404(Post.published, id=post_id)
    form = CommentForm(data=request.POST)
    if not form.is_valid():
        return _render_detail(request, post, form, status=400)

    if not form.is_spam():
        try:
            CommentService.add_comment(
                post=post,
                ip=get_client_ip(request),
                admin_url_builder=request.build_absolute_uri,
                **{field: form.cleaned_data[field] for field in ("name", "email", "body")},
            )
        except BusinessLogicError as error:
            messages.error(request, str(error))
            return redirect(f"{post.get_absolute_url()}#comment-form")

    # Bot z wypełnionym polem-pułapką dostaje ten sam komunikat — nie wie, że go odrzucono.
    messages.success(request, "Dziękuję za komentarz!")
    return redirect(f"{post.get_absolute_url()}#comments")


def post_search(request):
    form = SearchForm(request.GET or None)
    query, results = None, []
    if form.is_valid():
        query = form.cleaned_data["query"]
        results = PostSelector.search(query)
    return render(request, "blog/post/search.html", {"form": form, "query": query, "results": results})


def _render_detail(request, post, form, status=200):
    context = {
        "post": post,
        "comments": post.comments.filter(active=True),
        "form": form,
        "similar_posts": PostSelector.similar(post),
        "share_url": request.build_absolute_uri(post.get_absolute_url()),
    }
    return render(request, "blog/post/detail.html", context, status=status)
