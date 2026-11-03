from django import template

from ..models import Post
from ..selectors import PostSelector

register = template.Library()


@register.filter
def polish_pluralize(count, forms):
    """{{ n|polish_pluralize:"komentarz,komentarze,komentarzy" }} — 1 komentarz, 3 komentarze, 5 komentarzy, 22 komentarze."""
    one, few, many = forms.split(",")
    count = abs(int(count))
    if count == 1:
        return one
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return few
    return many


@register.simple_tag
def total_posts():
    return Post.published.count()


@register.simple_tag
def most_commented_posts(limit=3):
    return PostSelector.most_commented(limit)
