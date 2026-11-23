import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_csp_header_allows_jsdelivr(client):
    # django-csp 4.0 ignoruje stare CSP_*: bez CONTENT_SECURITY_POLICY nagłówka nie ma wcale.
    csp = client.get(reverse("cookies:policy"))["Content-Security-Policy"]

    assert "script-src 'self' https://cdn.jsdelivr.net" in csp


@pytest.mark.django_db
class TestInternalEndpointsNotPublic:
    def test_user_registration_api_is_removed(self, client):
        # Strona nie ma kont użytkowników poza adminem — publiczny POST /api/users/ zakładał konta w bazie.
        response = client.post("/api/users/", {"email": "a@example.com", "password": "kM9#vT2qLx7p"})

        assert response.status_code == 404

    def test_metrics_not_served_by_django(self, client):
        # Prometheus zbiera z eksporterów web:9100–9103, nie przez URL-e Django za nginxem.
        assert client.get("/metrics").status_code == 404

    def test_health_check_hides_database_error_details(self, client, mocker):
        connection = mocker.patch("apps.core.views.connection")
        connection.cursor.side_effect = Exception('host "db" user "secret_user"')

        response = client.get(reverse("health_check"))

        assert response.status_code == 503
        assert response.json()["checks"]["database"] == {"status": "unhealthy"}
        assert "secret_user" not in response.content.decode()
