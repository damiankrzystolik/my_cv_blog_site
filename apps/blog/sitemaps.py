from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from taggit.models import Tag

from .models import Post


class PostSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.9

    def items(self):
        return Post.published.all()

    def lastmod(self, obj):
        return obj.updated_at


class TagSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # Tylko tagi użyte w opublikowanych postach — bez pustych stron.
        return Tag.objects.filter(post__in=Post.published.all()).distinct().order_by("slug")

    def location(self, obj):
        return reverse("blog:post_list_by_tag", args=[obj.slug])
