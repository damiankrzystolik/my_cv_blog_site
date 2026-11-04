import hashlib
import hmac
from datetime import timedelta

import structlog
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.exceptions import BusinessLogicError

from .models import Comment

logger = structlog.get_logger(__name__)


def hash_ip(ip):
    if not ip:
        return ""
    return hmac.new(settings.SECRET_KEY.encode(), ip.encode(), hashlib.sha256).hexdigest()


class CommentService:
    @staticmethod
    @transaction.atomic
    def add_comment(post, name, email, body, ip, admin_url_builder=None) -> Comment:
        ip_hash = hash_ip(ip)
        CommentService._check_rate_limit(ip_hash)

        comment = Comment.objects.create(post=post, name=name, email=email, body=body, ip_hash=ip_hash)
        # Miejsce na automatyczną moderację (reguły, model AI) — na razie każdy komentarz jest widoczny od razu.
        logger.info("blog_comment_added", comment_id=comment.id, post_id=post.id)

        transaction.on_commit(lambda: CommentService._notify_owner(comment, admin_url_builder))
        return comment

    @staticmethod
    def _check_rate_limit(ip_hash):
        if not ip_hash:
            return
        since = timezone.now() - timedelta(hours=1)
        recent = Comment.objects.filter(ip_hash=ip_hash, created_at__gte=since).count()
        if recent >= settings.BLOG_COMMENT_RATE_LIMIT:
            logger.warning("blog_comment_rate_limited", ip_hash=ip_hash[:12])
            raise BusinessLogicError("Za dużo komentarzy w krótkim czasie. Spróbuj ponownie za godzinę.")

    @staticmethod
    def _notify_owner(comment, admin_url_builder):
        recipients = settings.BLOG_COMMENT_NOTIFY_EMAILS
        if not recipients:
            return
        admin_path = reverse("admin:blog_comment_change", args=[comment.id])
        admin_url = admin_url_builder(admin_path) if admin_url_builder else admin_path
        send_mail(
            subject=f"Nowy komentarz: {comment.post.title}",
            message=(
                f"{comment.name} <{comment.email}> skomentował(a) post „{comment.post.title}”:\n\n"
                f"{comment.body}\n\n"
                f"Komentarz jest już widoczny. Ukryj go w adminie, jeśli trzeba:\n{admin_url}"
            ),
            from_email=None,
            recipient_list=recipients,
            fail_silently=True,  # awaria SMTP nie może zablokować dodania komentarza
        )
