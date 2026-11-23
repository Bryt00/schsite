from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from donations import views as donation_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tinymce/', include('tinymce.urls')),
    path("", include("main.urls")),
    path('donations/', include('donations.urls')),
    path('wassce/', donation_views.wassce_registration, name='wassce_portal'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
