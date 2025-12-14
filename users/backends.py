# piano/users/backends.py

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            # Look up the user by their email instead of username
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            return None
        
        # Check if the password is correct for the found user
        if user.check_password(password):
            return user
        return None