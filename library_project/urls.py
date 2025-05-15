"""
URL configuration for library_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# library_project/urls.py

from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from django.views.generic.base import RedirectView

# API документациясы үчүн URL'дерди өзүнчө топтойлу (милдеттүү эмес, бирок иреттүү)
spectacular_urlpatterns = [
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

urlpatterns = [
    path('admin/', admin.site.urls),

    # 1. API endpoint'тери (мисалы, /api-v1/books/, /api-v1/borrowers/ ж.б.)
    # Бул эң спецификалык URL'дердин бири катары жогору турганы жакшы.
    path('api-v1/', include('api.urls')),  # 'api.urls' DRF роутерлерин жана API view'лерин камтыйт

    # 2. API Документациясы (мисалы, /api-docs/swagger-ui/)
    path('api-docs/', include(spectacular_urlpatterns)),

    # 3. Колдонуучу интерфейси үчүн HTML баракчалар (мисалы, /app/books/, /app/borrowers/ ж.б.)
    path('app/', include('api.urls_html')), # 'api.urls_html' TemplateView'лерди камтыйт

    # 4. Башкы бетке багыттоо (мисалы, /app/books/ барагына)
    # Бул эң жалпы URL ('') болгондуктан, тизменин аягында турганы жакшы.
    path('', RedirectView.as_view(url=reverse_lazy('page_book_list'), permanent=False), name='home'),
]

# DEBUG режиминде MEDIA файлдарын тейлөө үчүн
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # STATIC файлдарды DEBUG режиминде Django өзү тейлейт, эгер 'django.contrib.staticfiles'
    # INSTALLED_APPS'та болсо жана STATIC_URL аныкталса.
    # Бирок, эгер сиз development сервери менен иштеп жатсаңыз жана staticfiles_dirs
    # иштебей жатса, төмөнкү сапты кошсоңуз болот, бирок бул көбүнчө кереги жок:
    # urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Бул көбүнчө production үчүн