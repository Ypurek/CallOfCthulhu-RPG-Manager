from django.urls import path
from . import views

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='list'),
    path('<int:character_id>/', views.character_detail, name='detail'),
    path('<int:character_id>/edit/', views.character_edit, name='edit'),
    path('create/', views.character_create, name='create'),
    path('templates/', views.character_templates, name='templates'),
    path('cemetery/', views.character_cemetery, name='cemetery'),
]