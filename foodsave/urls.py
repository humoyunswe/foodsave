from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from vendors.views import index

urlpatterns = [
    path('admin/', admin.site.urls),
     path('', index, name='home'),
    path('accounts/', include('users.urls')),
    path('catalog/', include('catalog.urls')),
    path('vendors/', include('vendors.urls')),
    path('orders/', include('booking.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
