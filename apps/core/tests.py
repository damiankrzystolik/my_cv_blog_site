import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_csp_header_allows_jsdelivr(client):
    # django-csp 4.0 ignoruje stare CSP_*: bez CONTENT_SECURITY_POLICY nagłówka nie ma wcale.
    csp = client.get(reverse("cookies:policy"))["Content-Security-Policy"]

    assert "script-src 'self' https://cdn.jsdelivr.net" in csp
