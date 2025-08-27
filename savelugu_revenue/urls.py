from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from core.views import run_migrations
from core import views



urlpatterns = [
    path('', views.home, name='home'),   # 👈 Now root goes to home page
    path('admin/', admin.site.urls),
    path('run-migrations/', run_migrations), 
    path('', include('core.urls')),  # Core app URLs
    
]
urlpatterns += staticfiles_urlpatterns()


