import secrets

import bleach
from django.utils.text import slugify

SANITIZE_ALLOWED_TAGS = ["a", "b", "em", "i", "strong", "u", "p", "br"]
SANITIZE_ALLOWED_ATTRIBUTES = {"a": ["href", "title", "rel"]}


def generate_unique_slug(model_class, value, slug_field="slug"):
    base = slugify(value)
    candidate = base
    while model_class.objects.filter(**{slug_field: candidate}).exists():
        # Random suffix avoids TOCTOU: two concurrent requests get different candidates.
        candidate = f"{base}-{secrets.token_hex(3)}"
    return candidate


def get_client_ip(request):
    # X-Real-IP ustawia nginx z $remote_addr — klient nie może go podrobić.
    # Pierwszy wpis X-Forwarded-For pochodzi od klienta, więc nie nadaje się do limitów.
    return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


def sanitize_html(value):
    return bleach.clean(value, tags=SANITIZE_ALLOWED_TAGS, attributes=SANITIZE_ALLOWED_ATTRIBUTES, strip=True)
