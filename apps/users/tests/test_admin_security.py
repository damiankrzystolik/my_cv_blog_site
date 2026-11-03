import pytest
from axes.handlers.proxy import AxesProxyHandler
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import RequestFactory
from django.urls import reverse

from apps.users.serializers import UserSerializer

ATTACKER_IP = "203.0.113.10"
OWNER_IP = "198.51.100.20"


class TestPasswordPolicy:
    def test_password_shorter_than_12_chars_is_rejected(self):
        with pytest.raises(ValidationError):
            validate_password("kM9#vT2qLx7")  # 11 znaków

    def test_password_with_12_chars_is_accepted(self):
        validate_password("kM9#vT2qLx7p")

    @pytest.mark.django_db  # is_valid() odpytuje bazę o unikalność email/username
    def test_api_serializer_uses_password_validators(self):
        serializer = UserSerializer(data={"email": "a@example.com", "username": "a", "password": "short1234"})
        assert not serializer.is_valid()
        assert "password" in serializer.errors


@pytest.mark.django_db
class TestAxesLockout:
    @pytest.fixture(autouse=True)
    def _enable_axes(self, settings):
        # testing.py wyłącza axes; tu włączamy go tylko dla tych testów (pytest-django przywraca po teście).
        settings.AXES_ENABLED = True

    @pytest.fixture(autouse=True)
    def _fail_from_attacker_ip(self, _enable_axes, client, admin_user):
        # 5 złych haseł przez prawdziwy formularz admina (middleware + widok), jak z przeglądarki.
        for _ in range(settings.AXES_FAILURE_LIMIT):
            client.post(
                reverse("admin:login"),
                {"username": admin_user.email, "password": "wrong-password"},
                REMOTE_ADDR=ATTACKER_IP,
            )

    def _is_allowed(self, ip, username):
        # Ta sama decyzja, którą AxesStandaloneBackend podejmuje przy każdej próbie logowania.
        request = RequestFactory().post("/", REMOTE_ADDR=ip)
        return AxesProxyHandler.is_allowed(request, {"username": username})

    def test_account_is_locked_for_attacker_ip(self, admin_user):
        assert not self._is_allowed(ATTACKER_IP, admin_user.email)

    def test_owner_is_not_locked_from_another_ip(self, admin_user):
        # Ktoś znający login nie może zablokować właściciela logującego się z innego adresu.
        assert self._is_allowed(OWNER_IP, admin_user.email)

    def test_lockout_is_per_username_not_whole_ip(self):
        # Wymaga AXES_USERNAME_FORM_FIELD = "username" — bez tego axes zapisuje login jako None
        # i blokada sprowadza się do samego IP.
        assert self._is_allowed(ATTACKER_IP, "someone-else@example.com")


@pytest.mark.django_db
class TestAdminUrl:
    def test_admin_is_served_under_admin_url_setting(self, client):
        assert reverse("admin:index") == f"/{settings.ADMIN_URL}"

        response = client.get(f"/{settings.ADMIN_URL}")
        assert response.status_code == 302
        assert reverse("admin:login") in response["Location"]
