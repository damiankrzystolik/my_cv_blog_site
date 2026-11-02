import pytest
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.users.serializers import UserSerializer


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
class TestAdminUrl:
    def test_admin_is_served_under_admin_url_setting(self, client):
        assert reverse("admin:index") == f"/{settings.ADMIN_URL}"

        response = client.get(f"/{settings.ADMIN_URL}")
        assert response.status_code == 302
        assert reverse("admin:login") in response["Location"]
