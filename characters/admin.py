from django.contrib import admin
from .models import (
    Character, Skill, CharacterSkill, Weapon, CharacterWeapon,
    Item, CharacterItem, Spell, CharacterSpell, StatusEffect,
    CharacterStatusEffect, MentalDisorder, CharacterMentalDisorder
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
    list_display = ['name', 'mana_cost']
    search_fields = ['name']


@admin.register(StatusEffect)
class StatusEffectAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(MentalDisorder)
class MentalDisorderAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']