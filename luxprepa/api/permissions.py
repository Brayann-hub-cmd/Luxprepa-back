import jwt
from rest_framework.permissions import BasePermission,SAFE_METHODS
from .models import User
from django.conf import settings
SECRET_KEY = settings.SECRET_KEY

class IsAdminRole(BasePermission):

    def has_permission(self, request, view):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return False
        
        try:
            parts = auth_header.split(" ")

            if len(parts) == 2:
                token = parts[1]
            else:
                token = parts[0]

        except IndexError:
            raise False

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return False
        except jwt.InvalidTokenError:
            return False

        user_id = payload.get("id")
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return False
        
        request.user = user

        if user.role == "admin":
            return True
        return False

class IsAdminOrProfReadOnly(BasePermission):
    def has_permission(self, request, view):
        if request.method == 'GET':
            return request.user.is_authenticated  # prof peut lire
        return request.user.is_authenticated and request.user.role == 'admin'


