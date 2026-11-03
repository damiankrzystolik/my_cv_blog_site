from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Count, Q, QuerySet
from django.shortcuts import get_object_or_404

from .models import Post

# Podobieństwo trigramowe tytułu, od którego wynik uznajemy za trafienie mimo literówki.
TITLE_SIMILARITY_THRESHOLD = 0.3


class PostSelector:
    @staticmethod
    def published(tag=None) -> QuerySet:
        posts = Post.published.select_related("author").prefetch_related("tags", "images")
        if tag is not None:
            posts = posts.filter(tags__in=[tag])
        return posts

    @staticmethod
    def get_published(year, month, day, slug) -> Post:
        return get_object_or_404(
            Post.published.select_related("author").prefetch_related("tags", "images"),
            slug=slug,
            publish__year=year,
            publish__month=month,
            publish__day=day,
        )

    @staticmethod
    def similar(post, limit=4) -> QuerySet:
        tag_ids = post.tags.values_list("id", flat=True)
        return (
            Post.published.filter(tags__in=tag_ids)
            .exclude(id=post.id)
            .annotate(same_tags=Count("tags"))
            .order_by("-same_tags", "-publish")[:limit]
        )

    @staticmethod
    def search(query) -> QuerySet:
        # Trafienie = fraza w tytule/treści/tagu albo tytuł podobny mimo literówki (pg_trgm).
        return (
            Post.published.annotate(similarity=TrigramSimilarity("title", query))
            .filter(
                Q(similarity__gte=TITLE_SIMILARITY_THRESHOLD)
                | Q(title__icontains=query)
                | Q(body__icontains=query)
                | Q(tags__name__iexact=query)
            )
            .distinct()
            .select_related("author")
            .prefetch_related("tags", "images")
            .order_by("-similarity", "-publish")
        )

    @staticmethod
    def most_commented(limit=3) -> QuerySet:
        return (
            Post.published.annotate(total_comments=Count("comments", filter=Q(comments__active=True)))
            .filter(total_comments__gt=0)
            .order_by("-total_comments", "-publish")[:limit]
        )
