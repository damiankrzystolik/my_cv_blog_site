import pytest
from django.core import mail
from django.urls import reverse

from apps.blog.models import Comment

from .factories import CommentFactory, PostFactory

COMMENT = {"name": "Anna", "email": "anna@example.com", "body": "Świetny wpis!"}


def _post_comment(client, post, data=None, ip="203.0.113.5"):
    return client.post(reverse("blog:post_comment", args=[post.id]), data or COMMENT, REMOTE_ADDR=ip)


@pytest.mark.django_db(transaction=True)  # on_commit (wysyłka maila) wymaga prawdziwego commita
class TestAddComment:
    def test_comment_is_visible_immediately_and_redirects(self, client):
        post = PostFactory()

        response = _post_comment(client, post)

        assert response.status_code == 302
        assert response["Location"] == f"{post.get_absolute_url()}#comments"
        assert Comment.objects.get().active is True

    def test_owner_gets_notification_with_admin_link(self, client):
        post = PostFactory(title="Wpis o axes")

        _post_comment(client, post)

        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == ["owner@example.com"]
        assert "Wpis o axes" in message.subject
        assert f"/blog/comment/{Comment.objects.get().id}/change/" in message.body

    def test_ip_is_stored_only_as_hash(self, client):
        _post_comment(client, PostFactory(), ip="203.0.113.5")

        ip_hash = Comment.objects.get().ip_hash
        assert len(ip_hash) == 64
        assert "203.0.113.5" not in ip_hash

    def test_rate_limit_per_ip(self, client, settings):
        settings.BLOG_COMMENT_RATE_LIMIT = 2
        post = PostFactory()

        _post_comment(client, post)
        _post_comment(client, post)
        response = _post_comment(client, post)

        assert Comment.objects.count() == 2
        assert response["Location"].endswith("#comment-form")

    def test_rate_limit_does_not_affect_other_ips(self, client, settings):
        settings.BLOG_COMMENT_RATE_LIMIT = 1
        post = PostFactory()

        _post_comment(client, post, ip="203.0.113.5")
        _post_comment(client, post, ip="198.51.100.7")

        assert Comment.objects.count() == 2

    def test_honeypot_silently_drops_bot_comment(self, client):
        response = _post_comment(client, PostFactory(), {**COMMENT, "website": "http://spam.example"})

        assert response.status_code == 302
        assert Comment.objects.count() == 0
        assert len(mail.outbox) == 0

    def test_invalid_form_rerenders_post_with_errors(self, client):
        response = _post_comment(client, PostFactory(), {**COMMENT, "email": "to-nie-email"})

        assert response.status_code == 400
        assert "email" in response.context["form"].errors
        assert Comment.objects.count() == 0

    def test_cannot_comment_draft(self, client):
        post = PostFactory(status="DF")
        assert _post_comment(client, post).status_code == 404

    def test_get_is_not_allowed(self, client):
        assert client.get(reverse("blog:post_comment", args=[PostFactory().id])).status_code == 405


@pytest.mark.django_db
class TestCommentDisplay:
    def test_comment_html_is_escaped(self, client):
        post = PostFactory()
        CommentFactory(post=post, body="<script>alert(1)</script>")

        content = client.get(post.get_absolute_url()).content.decode()

        assert "<script>alert(1)</script>" not in content
        assert "&lt;script&gt;" in content
