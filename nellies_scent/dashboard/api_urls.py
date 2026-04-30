from django.urls import include, path
from rest_framework import routers

from .api import SocialAccountViewSet, SocialAppViewSet, SocialTokenViewSet

router = routers.DefaultRouter()
router.register(r'apps', SocialAppViewSet, basename='socialapp')
router.register(r'accounts', SocialAccountViewSet, basename='socialaccount')
router.register(r'tokens', SocialTokenViewSet, basename='socialtoken')

urlpatterns = [
    path('', include(router.urls)),
]
