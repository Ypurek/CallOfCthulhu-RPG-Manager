from django.contrib import admin
from .models import (
    Scenario, ScenarioPlayer, ScenarioNPC, Invitation,
    FightEncounter, FightParticipant, Message
)


class ScenarioPlayerInline(admin.TabularInline):
    model = ScenarioPlayer
    extra = 0


class ScenarioNPCInline(admin.TabularInline):
    model = ScenarioNPC
    extra = 0


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ['name', 'keeper', 'status', 'visibility', 'place', 'in_game_time', 'created_at']
    list_filter = ['status', 'visibility', 'keeper']
    search_fields = ['name', 'description', 'place']
    inlines = [ScenarioPlayerInline, ScenarioNPCInline]


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ['scenario', 'invited_by', 'invited_player', 'is_used', 'created_at']
    list_filter = ['is_used']
    search_fields = ['invite_code']


@admin.register(FightEncounter)
class FightEncounterAdmin(admin.ModelAdmin):
    list_display = ['scenario', 'round_number', 'is_active', 'started_at']
    list_filter = ['is_active']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['scenario', 'sender', 'recipient', 'message_type', 'is_read', 'sent_at']
    list_filter = ['message_type', 'is_read']