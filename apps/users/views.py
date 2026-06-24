from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer
from .services import UserService


class UserCreateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = UserService.create_user(**serializer.validated_data)
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)
