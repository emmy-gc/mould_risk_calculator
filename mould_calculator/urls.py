from django.urls import path
from . import views 

urlpatterns = [
    path('',views.home,name='home'),
    path('about/', views.about, name='about'),
    path('uploadpage/', views.uploadpage, name='uploadpage'),
    path('result/', views.result, name='result'),
  
]