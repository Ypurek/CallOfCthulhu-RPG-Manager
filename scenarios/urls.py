from django.urls import path
from . import views

app_name = 'scenarios'

urlpatterns = [
    # List / archive
    path('', views.scenario_list, name='list'),
    path('archive/', views.scenario_archive, name='archive'),

    # CRUD
    path('create/', views.scenario_create, name='create'),
    path('<int:scenario_id>/edit/', views.scenario_edit, name='edit'),
    path('<int:scenario_id>/delete/', views.scenario_delete, name='delete'),

    # Player-facing
    path('<int:scenario_id>/', views.scenario_detail, name='detail'),
    path('<int:scenario_id>/snapshot/', views.scenario_player_snapshot, name='player_snapshot'),
    path('<int:scenario_id>/snapshot-json/', views.scenario_player_snapshot_json, name='player_snapshot_json'),
    path('<int:scenario_id>/private-notes/', views.scenario_player_save_private_notes, name='player_private_notes'),
    path('join/<str:invite_code>/', views.join_scenario, name='join'),

    # Keeper management
    path('<int:scenario_id>/manage/', views.scenario_manage, name='manage'),
    path('<int:scenario_id>/hints/keeper/', views.scenario_keeper_hints, name='keeper_hints'),
    path('<int:scenario_id>/fight/', views.fight_encounter, name='fight'),
    path('<int:scenario_id>/fight/state/', views.scenario_fight_state, name='fight_state'),
    path('<int:scenario_id>/fight/start/', views.scenario_fight_start, name='fight_start'),
    path('<int:scenario_id>/fight/end/', views.scenario_fight_end, name='fight_end'),
    path('<int:scenario_id>/fight/add/', views.scenario_fight_add_participant, name='fight_add_participant'),
    path('<int:scenario_id>/fight/participant/<int:participant_id>/remove/', views.scenario_fight_remove_participant, name='fight_remove_participant'),
    path('<int:scenario_id>/fight/participant/<int:participant_id>/prepared/', views.scenario_fight_set_prepared, name='fight_set_prepared'),
    path('<int:scenario_id>/fight/turn/next/', views.scenario_fight_advance_turn, name='fight_advance_turn'),
    path('<int:scenario_id>/fight/turn/reset/', views.scenario_fight_reset_turns, name='fight_reset_turns'),

    # Status
    path('<int:scenario_id>/status/', views.scenario_update_status, name='update_status'),

    # In-game time
    path('<int:scenario_id>/time/advance/', views.scenario_advance_time, name='advance_time'),
    path('<int:scenario_id>/time/set/', views.scenario_set_time, name='set_time'),

    # Notes
    path('<int:scenario_id>/notes/', views.scenario_save_notes, name='save_notes'),

    # Invitations
    path('<int:scenario_id>/invite/create/', views.scenario_invite_create, name='invite_create'),
    path('<int:scenario_id>/invite/<int:invite_id>/revoke/', views.scenario_invite_revoke, name='invite_revoke'),

    # Players
    path('<int:scenario_id>/player/<int:player_id>/remove/', views.scenario_player_remove, name='player_remove'),
    path('<int:scenario_id>/player/<int:player_id>/unassign/', views.scenario_player_unassign_character, name='player_unassign'),
    path('<int:scenario_id>/select-character/', views.scenario_player_select_character, name='select_character'),

    # In-session stat adjustment (AJAX)
    path('<int:scenario_id>/character/<int:character_id>/stats/', views.scenario_character_adjust_stats, name='character_adjust_stats'),
    path('<int:scenario_id>/character/<int:character_id>/toggle-alive/', views.scenario_character_toggle_alive, name='character_toggle_alive'),
    path('<int:scenario_id>/character/<int:character_id>/skill/<int:skill_id>/needs-update/', views.scenario_character_skill_needs_update, name='character_skill_needs_update'),

    # NPCs
    path('<int:scenario_id>/npc/create/', views.scenario_npc_create, name='npc_create'),
    path('<int:scenario_id>/npc/from-template/', views.scenario_npc_from_template, name='npc_from_template'),
    path('<int:scenario_id>/npc/<int:snpc_id>/clone/', views.scenario_npc_clone, name='npc_clone'),
    path('<int:scenario_id>/npc/<int:snpc_id>/remove/', views.scenario_npc_remove, name='npc_remove'),

    # Messaging
    path('<int:scenario_id>/message/send/', views.scenario_send_message, name='send_message'),
    path('<int:scenario_id>/messages/', views.scenario_get_messages, name='get_messages'),
    path('<int:scenario_id>/messages/read/', views.scenario_mark_messages_read, name='mark_messages_read'),

    # Status effects
    path('<int:scenario_id>/character/<int:character_id>/effect/add/', views.scenario_character_add_effect, name='character_add_effect'),
    path('<int:scenario_id>/character/<int:character_id>/effect/<int:effect_id>/remove/', views.scenario_character_remove_effect, name='character_remove_effect'),
    path('<int:scenario_id>/character/<int:character_id>/effects/', views.scenario_character_get_effects, name='character_get_effects'),
]