from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import LoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path('convert/', views.upload_statement, name='upload'),
    path('download/<int:pk>/', views.download_excel, name='download'),
    path('login/', auth_views.LoginView.as_view(authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('status/<int:pk>/', views.check_status, name='check_status'),
]
