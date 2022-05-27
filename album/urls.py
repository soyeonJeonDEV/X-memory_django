from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

from django.conf import settings
from django.conf.urls.static import static
from . import views
urlpatterns = [
  path('',views.index,name='index'),
  path('login',
    auth_views.LoginView.as_view(template_name = 'login.html'),
    name = 'login'),
  path('logout/', auth_views.LogoutView.as_view(template_name='login.html'), name = 'logout'),
  path('signup/', views.signup, name = 'signup'),
  path('album/',views.index,name='album'),
  path('upload/',views.upload,name='upload')
    
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root = settings.STATIC_ROOT)

