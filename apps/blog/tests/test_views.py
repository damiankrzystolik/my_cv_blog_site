from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.blog.models import Post

from .factories import CommentFactory, PostFactory


@pytest.mark.django_db
class TestPostList:
    def test_shows_only_published_posts(self, client):
        PostFactory(title="Opublikowany")
        PostFactory(title="Szkic", status=Post.Status.DRAFT)
        PostFactory(title="Zaplanowany", publish=timezone.now() + timedelta(days=1))

        content = client.get(reverse("blog:post_list")).content.decode()

        assert "Opublikowany" in content
        assert "Szkic" not in content
        assert "Zaplanowany" not in content

    def test_filters_by_tag(self, client):
        PostFactory(title="O Django", tags=["django"])
        PostFactory(title="O Dockerze", tags=["docker"])

        content = client.get(reverse("blog:post_list_by_tag", args=["django"])).content.decode()

        assert "O Django" in content
        assert "O Dockerze" not in content

    def test_unknown_tag_returns_404(self, client):
        assert client.get(reverse("blog:post_list_by_tag", args=["nie-ma"])).status_code == 404

    def test_paginates(self, client, settings):
        settings.BLOG_POSTS_PER_PAGE = 2
        PostFactory.create_batch(3)

        response = client.get(reverse("blog:post_list"), {"page": 2})

        assert len(response.context["posts"]) == 1

    def test_query_count_does_not_grow_with_posts(self, client, django_assert_max_num_queries):
        PostFactory.create_batch(5, tags=["django"])
        with django_assert_max_num_queries(10):
            client.get(reverse("blog:post_list"))


@pytest.mark.django_db
class TestPostDetail:
    def test_renders_published_post(self, client):
        post = PostFactory(body="## Nagłówek", excerpt="Opis do SEO")

        response = client.get(post.get_absolute_url())

        assert response.status_code == 200
        assert "<h2>Nagłówek</h2>" in response.content.decode()
        assert '<meta name="description" content="Opis do SEO">' in response.content.decode()

    def test_draft_returns_404(self, client):
        post = PostFactory(status=Post.Status.DRAFT)
        assert client.get(post.get_absolute_url()).status_code == 404

    def test_shows_only_active_comments(self, client):
        post = PostFactory()
        CommentFactory(post=post, body="Widoczny komentarz")
        CommentFactory(post=post, body="Ukryty komentarz", active=False)

        content = client.get(post.get_absolute_url()).content.decode()

        assert "Widoczny komentarz" in content
        assert "Ukryty komentarz" not in content

    def test_share_links_contain_absolute_post_url(self, client):
        post = PostFactory()

        content = client.get(post.get_absolute_url()).content.decode()

        assert "linkedin.com/sharing/share-offsite/?url=http%3A%2F%2Ftestserver%2Fblog%2F" in content


@pytest.mark.django_db
class TestSearch:
    def test_finds_by_title_body_and_tag(self, client):
        PostFactory(title="Zabezpieczenie panelu admina")
        PostFactory(title="Inny", body="Konfiguracja nginx")
        PostFactory(title="Tagowany", tags=["security"])
        PostFactory(title="Nie pasuje")

        def titles(query):
            return {post.title for post in client.get(reverse("blog:post_search"), {"query": query}).context["results"]}

        assert titles("panelu") == {"Zabezpieczenie panelu admina"}
        assert titles("nginx") == {"Inny"}
        assert titles("security") == {"Tagowany"}

    def test_tolerates_typo_in_title(self, client):
        PostFactory(title="Konfiguracja Dockera")

        response = client.get(reverse("blog:post_search"), {"query": "Konfiguracja Dokera"})

        assert [post.title for post in response.context["results"]] == ["Konfiguracja Dockera"]

    def test_too_short_query_shows_error(self, client):
        response = client.get(reverse("blog:post_search"), {"query": "a"})
        assert response.context["query"] is None
        assert "co najmniej 2 znaki" in response.content.decode()


@pytest.mark.django_db
class TestFeedAndSitemap:
    def test_feed_lists_published_posts(self, client):
        PostFactory(title="W kanale RSS")
        PostFactory(title="Szkic poza RSS", status=Post.Status.DRAFT)

        content = client.get(reverse("blog:post_feed")).content.decode()

        assert "W kanale RSS" in content
        assert "Szkic poza RSS" not in content

    def test_sitemap_contains_post_and_used_tag(self, client):
        post = PostFactory(tags=["django"])

        content = client.get("/sitemap.xml").content.decode()

        assert post.get_absolute_url() in content
        assert reverse("blog:post_list_by_tag", args=["django"]) in content
