from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    # Te same reguły co AUTH_PASSWORD_VALIDATORS (min. 12 znaków itd.), zamiast osobnego min_length.
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name", "date_joined", "password"]
        read_only_fields = ["id", "date_joined"]
