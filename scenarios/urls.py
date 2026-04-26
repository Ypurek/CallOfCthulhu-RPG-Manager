from django.urls import path
from . import views

app_name = 'scenarios'

urlpatterns = [
    path('', views.scenario_list, name='list'),
    path('<int:scenario_id>/', views.scenario_detail, name='detail'),
    path('<int:scenario_id>/manage/', views.scenario_manage, name='manage'),
    path('<int:scenario_id>/fight/', views.fight_encounter, name='fight'),
    path('create/', views.scenario_create, name='create'),
    path('join/<str:invite_code>/', views.join_scenario, name='join'),
    path('archive/', views.scenario_archive, name='archive'),
]