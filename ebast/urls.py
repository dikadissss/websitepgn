from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from core.views import HomeView, RekapView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('rekap/', RekapView.as_view(), name='rekap'),
    path('core/', include('core.urls')),
    path('admin/', admin.site.urls),
    path('qc/', include('qc.urls')),
    path('cl_seiscomp/', include('cl_seiscomp.urls')),
    path('text-format-converter/', include('text_format_converter.urls')),
    path('bast/', include('bast.urls')),
    path('daily-report/', include('daily_report.urls')),
    path('qcfm/', include('qcfm.urls')),
    path('earthquake-decay/', include('earthquake_decay.urls')),
    path('api/v1/', include('core.api_urls')),
]

if settings.DEBUG:  # Only for development
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
