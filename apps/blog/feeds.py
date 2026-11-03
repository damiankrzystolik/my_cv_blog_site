from django.contrib.syndication.views import Feed
from django.template.defaultfilters import truncatewords_html
from django.urls import reverse_lazy

from .models import Post


class LatestPostsFeed(Feed):
    title = "Blog — Damian Krzystolik"
    link = reverse_lazy("blog:post_list")
    description = "Nowe wpisy na blogu."

    def items(self):
        return Post.published.prefetch_related("images")[:10]

    def item_title(self, item):
        return item.title

    def item_description(self, item):
        return item.excerpt or truncatewords_html(item.rendered_body(), 30)

    def item_pubdate(self, item):
        return item.publish

    def item_updateddate(self, item):
        return item.updated_at
