from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

urlpatterns = [
    # Authentication (django-allauth)
    path('accounts/', include('allauth.urls')),
    
    # Dashboard admin
    path('dashboard/', include('dashboard.urls')),
    
    # Core app (main e-commerce functionality)
    path('', include(('core.urls', 'core'), namespace='core')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
