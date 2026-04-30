from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth.models import User
from django.utils.text import slugify
import random
import string


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        """
        Populate user with data from social provider.
        """
        user = sociallogin.user

        # Extract email
        email = data.get('email')
        if email:
            user.email = email

        # Extract username
        username = data.get('username') or data.get('name') or data.get('given_name')
        if not username and email:
            # Use email prefix as username
            username = email.split('@')[0]

        if username:
            # Clean and slugify username
            username = slugify(username)
            # Ensure uniqueness
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}_{counter}"
                counter += 1
            user.username = username
        else:
            # Generate a random username if nothing available
            user.username = self._generate_unique_username()

        return user

    def _generate_unique_username(self):
        """Generate a unique username"""
        while True:
            username = 'user_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            if not User.objects.filter(username=username).exists():
                return username