from django.contrib import admin
from .models import (
    Character, Skill, CharacterSkill, Weapon, CharacterWeapon,
    Item, CharacterItem, Spell, CharacterSpell, StatusEffect,
    CharacterStatusEffect, MentalDisorder, CharacterMentalDisorder,
    CharacterChangeLog, CharacterTemplate, NPCTemplate
)


class CharacterSkillInline(admin.TabularInline):
    model = CharacterSkill
    extra = 0


class CharacterWeaponInline(admin.TabularInline):
    model = CharacterWeapon
    extra = 0


class CharacterItemInline(admin.TabularInline):
    model = CharacterItem
    extra = 0


class CharacterSpellInline(admin.TabularInline):
    model = CharacterSpell
    extra = 0


class CharacterStatusEffectInline(admin.TabularInline):
    model = CharacterStatusEffect
    extra = 0


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'character_type', 'is_alive', 'hp_current', 'hp_max', 'sanity_current']
    list_filter = ['character_type', 'is_alive', 'owner']
    search_fields = ['name', 'occupation']
    inlines = [CharacterSkillInline, CharacterWeaponInline, CharacterItemInline, CharacterSpellInline, CharacterStatusEffectInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'base_value']
    list_filter = ['category']
    search_fields = ['name']


@admin.register(Weapon)
class WeaponAdmin(admin.ModelAdmin):
    list_display = ['name', 'damage', 'attacks_per_round', 'range']
    search_fields = ['name']


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Spell)
class SpellAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'mana_cost', 'badge_color']
    search_fields = ['name']
    list_editable = ['badge_color']


@admin.register(StatusEffect)
class StatusEffectAdmin(admin.ModelAdmin):
    list_display = ['name', 'effect_type', 'badge_color', 'is_permanent', 'icon_class']
    list_filter = ['effect_type', 'is_permanent']
    search_fields = ['name', 'description']
    list_editable = ['badge_color', 'is_permanent']
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'description', 'effect_type')
        }),
        ('Display', {
            'fields': ('icon_class', 'badge_color')
        }),
        ('Rules', {
            'fields': ('is_permanent', 'game_rules_json')
        }),
    )


@admin.register(CharacterStatusEffect)
class CharacterStatusEffectAdmin(admin.ModelAdmin):
    list_display = ['character', 'status_effect', 'remaining_rounds', 'acquired_at']
    list_filter = ['acquired_at', 'status_effect__effect_type']
    search_fields = ['character__name', 'status_effect__name']
    readonly_fields = ['acquired_at']


@admin.register(MentalDisorder)
class MentalDisorderAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(CharacterChangeLog)
class CharacterChangeLogAdmin(admin.ModelAdmin):
    list_display = ['character', 'changed_by', 'created_at']
    list_filter = ['created_at', 'character']
    search_fields = ['character__name', 'changed_by__username']
    readonly_fields = ['created_at']


@admin.register(CharacterTemplate)
class CharacterTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'updated_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(NPCTemplate)
class NPCTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_by', 'created_at', 'updated_at']
    list_filter = ['created_at', 'created_by']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
