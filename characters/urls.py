from django.urls import path
from . import views

app_name = 'characters'

urlpatterns = [
    path('', views.character_list, name='list'),
    path('<int:character_id>/', views.character_detail, name='detail'),
    path('<int:character_id>/delete/', views.character_delete, name='delete'),
    path('<int:character_id>/edit/', views.character_edit, name='edit'),
    path('<int:character_id>/wizard/', views.character_edit_wizard, name='edit_wizard'),
    path('<int:character_id>/wizard/export/', views.character_edit_wizard_export, name='edit_wizard_export'),
    path('<int:character_id>/wizard/import/', views.character_edit_wizard_import, name='edit_wizard_import'),
    path('npc/<int:character_id>/wizard/', views.character_edit_wizard, name='npc_edit_wizard'),
    path('npc/<int:character_id>/wizard/export/', views.character_edit_wizard_export, name='npc_edit_wizard_export'),
    path('npc/<int:character_id>/wizard/import/', views.character_edit_wizard_import, name='npc_edit_wizard_import'),
    path('create/', views.character_create, name='create'),
    path('create/import/', views.character_import_json, name='create_import_json'),
    path('create/export/', views.character_export_json, name='create_export_json'),
    path('templates/', views.character_templates, name='templates'),
    path('spells/', views.spell_admin, name='spell_admin'),
    path('templates/create/', views.template_create_wizard, name='template_create'),
    path('templates/<int:template_id>/edit/', views.template_edit_wizard, name='template_edit'),
    path('templates/<int:template_id>/delete/', views.template_delete, name='template_delete'),
    path('templates/<int:template_id>/use/', views.character_use_template, name='use_template'),
    path('cemetery/', views.character_cemetery, name='cemetery'),
    # NPC Templates
    path('npc/templates/', views.npc_templates, name='npc_templates'),
    path('npc/templates/create/', views.npc_template_create_wizard, name='npc_template_create'),
    path('npc/templates/<int:template_id>/edit/', views.npc_template_edit_wizard, name='npc_template_edit'),
    path('npc/templates/<int:template_id>/delete/', views.npc_template_delete, name='npc_template_delete'),
    path('npc/templates/<int:template_id>/use/', views.npc_use_template, name='npc_use_template'),
    path('npc/create/', views.npc_create, name='npc_create'),
    path('npc/create/import/', views.npc_import_json, name='npc_import_json'),
    path('npc/create/export/', views.npc_export_json, name='npc_export_json'),
]