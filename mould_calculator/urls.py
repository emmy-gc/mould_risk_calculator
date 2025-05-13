from django.urls import path
from . import views 
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('',views.home,name='home'),
    path('about/', views.about, name='about'),
    path('uploadpage/', views.uploadpage, name='uploadpage'),
    path('result/', views.result, name='result'),
    path('login/', auth_views.LoginView.as_view(template_name='auth/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', views.register, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
  
]