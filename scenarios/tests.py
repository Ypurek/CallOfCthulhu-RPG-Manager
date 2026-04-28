"""
Comprehensive test suite for the scenarios app.

Coverage:
  - Model unit tests (Scenario, ScenarioPlayer, ScenarioNPC, Invitation)
  - Permission/access control (keeper-only, scenario-owner access)
  - CRUD views (create, edit, delete)
  - Scenario management: time advancement, notes, status updates
  - Player management: invitation creation/revocation, join via link, removal
  - NPC management: quick-create, from-template, clone, remove
  - Player-facing views: scenario detail, archive, list
"""

import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from characters.models import Character, CharacterStatusEffect, NPCTemplate, StatusEffect
from scenarios.models import (
    FightEncounter,
    FightParticipant,
    Invitation,
    Message,
    MessageReceipt,
    Scenario,
    ScenarioNPC,
    ScenarioPlayer,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_user(username, is_keeper=False, is_staff=False):
    u = User.objects.create_user(username=username, password='testpass123')
    if is_keeper:
        u.role = 'KEEPER'  # Must match User.Role.KEEPER
        u.save()
    if is_staff:
        u.is_staff = True
        u.save()
    return u


def make_scenario(keeper, **kwargs):
    defaults = dict(
        name='Test Scenario',
        place='Arkham',
        visibility='PRIVATE',
        status='PLANNING',
        in_game_time=timezone.now(),
    )
    defaults.update(kwargs)
    return Scenario.objects.create(keeper=keeper, **defaults)


def make_character(owner, character_type='PC', **kwargs):
    defaults = dict(
        character_type=character_type,
        name='Test Hero',
        is_alive=True,
        strength=50, constitution=50, dexterity=50,
        intelligence=50, power=50, size=50,
        appearance=50, education=50,
        hp_current=10, hp_max=10,
        mp_current=10, mp_max=10,
        sanity_current=50, sanity_max=99, sanity_start=50,
        luck=50, movement=8, build=0, damage_bonus='0', cash=0,
    )
    defaults.update(kwargs)
    return Character.objects.create(owner=owner, **defaults)


def make_npc_template(name='Zombie', **kwargs):
    payload = {
        'character_info': {'name': name, 'occupation': 'Undead'},
        'characteristics': {
            'STR': 60, 'CON': 60, 'DEX': 40, 'INT': 20,
            'POW': 30, 'SIZ': 65, 'APP': 10, 'EDU': 10,
        },
        'status': {
            'HP': {'max': 12, 'current': 12},
            'MP': {'max': 6, 'current': 6},
            'Sanity': {'max': 99, 'current': 30},
        },
        'description': 'A shambling undead creature.',
    }
    payload.update(kwargs)
    return NPCTemplate.objects.create(name=name, payload=payload)


# ===========================================================================
# I. MODEL UNIT TESTS
# ===========================================================================

class ScenarioModelTest(TestCase):

    def setUp(self):
        self.keeper = make_user('k1', is_keeper=True)

    def test_str(self):
        s = make_scenario(self.keeper, name='Edge of Darkness')
        self.assertIn('Edge of Darkness', str(s))
        self.assertIn(s.get_status_display(), str(s))

    def test_default_status_planning(self):
        s = make_scenario(self.keeper)
        self.assertEqual(s.status, 'PLANNING')

    def test_default_visibility_private(self):
        s = make_scenario(self.keeper)
        self.assertEqual(s.visibility, 'PRIVATE')

    def test_ordering_newest_first(self):
        s1 = make_scenario(self.keeper, name='A')
        s2 = make_scenario(self.keeper, name='B')
        qs = list(Scenario.objects.all())
        self.assertEqual(qs[0], s2)
        self.assertEqual(qs[1], s1)


class ScenarioPlayerModelTest(TestCase):

    def setUp(self):
        self.keeper = make_user('k2', is_keeper=True)
        self.player = make_user('p2')
        self.scenario = make_scenario(self.keeper)
        self.char = make_character(self.player)

    def test_str(self):
        sp = ScenarioPlayer.objects.create(
            scenario=self.scenario, player=self.player, character=self.char
        )
        self.assertIn(self.player.username, str(sp))

    def test_unique_player_per_scenario(self):
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player)
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player)


class ScenarioNPCModelTest(TestCase):

    def setUp(self):
        self.keeper = make_user('k3', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.npc_char = make_character(self.keeper, character_type='NPC', name='Bob')

    def test_get_display_name_uses_override(self):
        sn = ScenarioNPC.objects.create(
            scenario=self.scenario, npc=self.npc_char, display_name='Goblin'
        )
        self.assertEqual(sn.get_display_name(), 'Goblin')

    def test_get_display_name_falls_back_to_npc(self):
        sn = ScenarioNPC.objects.create(scenario=self.scenario, npc=self.npc_char)
        self.assertEqual(sn.get_display_name(), 'Bob')

    def test_str(self):
        sn = ScenarioNPC.objects.create(scenario=self.scenario, npc=self.npc_char)
        self.assertIn(self.scenario.name, str(sn))


class InvitationModelTest(TestCase):

    def setUp(self):
        self.keeper = make_user('k4', is_keeper=True)
        self.scenario = make_scenario(self.keeper)

    def test_invite_str(self):
        inv = Invitation.objects.create(
            scenario=self.scenario,
            invited_by=self.keeper,
            invite_code='abc123',
        )
        self.assertIn(self.scenario.name, str(inv))


# ===========================================================================
# II. PERMISSION / ACCESS CONTROL TESTS
# ===========================================================================

class PermissionTests(TestCase):
    """Non-keepers must not access keeper-only endpoints."""

    def setUp(self):
        self.keeper = make_user('keeper', is_keeper=True)
        self.player = make_user('player')
        self.scenario = make_scenario(self.keeper)

    def _post(self, url, data=None):
        self.client.force_login(self.player)
        return self.client.post(url, data or {})

    def test_player_cannot_create_scenario(self):
        self.client.force_login(self.player)
        r = self.client.post(reverse('scenarios:create'), {'name': 'Hack'})
        self.assertRedirects(r, reverse('dashboard'))

    def test_player_cannot_edit_scenario(self):
        url = reverse('scenarios:edit', kwargs={'scenario_id': self.scenario.id})
        r = self._post(url, {'name': 'Hack'})
        self.assertRedirects(r, reverse('dashboard'))

    def test_player_cannot_delete_scenario(self):
        url = reverse('scenarios:delete', kwargs={'scenario_id': self.scenario.id})
        r = self._post(url)
        self.assertRedirects(r, reverse('dashboard'))

    def test_other_keeper_cannot_manage_scenario(self):
        other = make_user('other_keeper', is_keeper=True)
        self.client.force_login(other)
        url = reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_admin_can_manage_any_scenario(self):
        admin = make_user('admin_u', is_staff=True)
        self.client.force_login(admin)
        url = reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)

    def test_unauthenticated_redirected_to_login(self):
        url = reverse('scenarios:list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 302)
        self.assertIn('login', r['Location'])


# ===========================================================================
# III. SCENARIO CRUD TESTS
# ===========================================================================

class ScenarioCreateViewTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kc', is_keeper=True)
        self.client.force_login(self.keeper)

    def test_get_create_page(self):
        r = self.client.get(reverse('scenarios:create'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Create New Scenario')

    def test_post_valid_creates_scenario(self):
        r = self.client.post(reverse('scenarios:create'), {
            'name': 'New Adventure',
            'place': 'Miskatonic',
            'visibility': 'PRIVATE',
            'status': 'PLANNING',
            'description': 'A test scenario',
        })
        self.assertEqual(Scenario.objects.filter(name='New Adventure').count(), 1)
        s = Scenario.objects.get(name='New Adventure')
        self.assertRedirects(r, reverse('scenarios:manage', kwargs={'scenario_id': s.id}))

    def test_post_missing_name_stays_on_form(self):
        r = self.client.post(reverse('scenarios:create'), {'name': ''})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Create New Scenario')

    def test_create_sets_keeper(self):
        self.client.post(reverse('scenarios:create'), {
            'name': 'Mine',
            'visibility': 'PRIVATE',
            'status': 'PLANNING',
        })
        s = Scenario.objects.get(name='Mine')
        self.assertEqual(s.keeper, self.keeper)


class ScenarioEditViewTest(TestCase):

    def setUp(self):
        self.keeper = make_user('ke', is_keeper=True)
        self.scenario = make_scenario(self.keeper, name='Old Name')
        self.client.force_login(self.keeper)

    def test_get_edit_page(self):
        url = reverse('scenarios:edit', kwargs={'scenario_id': self.scenario.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Old Name')

    def test_post_updates_name(self):
        url = reverse('scenarios:edit', kwargs={'scenario_id': self.scenario.id})
        self.client.post(url, {
            'name': 'New Name',
            'visibility': 'PUBLIC',
            'status': 'PLANNING',
        })
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.name, 'New Name')
        self.assertEqual(self.scenario.visibility, 'PUBLIC')

    def test_activating_scenario_sets_started_at(self):
        url = reverse('scenarios:edit', kwargs={'scenario_id': self.scenario.id})
        self.assertIsNone(self.scenario.started_at)
        self.client.post(url, {
            'name': self.scenario.name,
            'visibility': 'PRIVATE',
            'status': 'ACTIVE',
        })
        self.scenario.refresh_from_db()
        self.assertIsNotNone(self.scenario.started_at)

    def test_completing_scenario_sets_ended_at(self):
        url = reverse('scenarios:edit', kwargs={'scenario_id': self.scenario.id})
        self.client.post(url, {
            'name': self.scenario.name,
            'visibility': 'PRIVATE',
            'status': 'COMPLETED',
        })
        self.scenario.refresh_from_db()
        self.assertIsNotNone(self.scenario.ended_at)


class ScenarioDeleteViewTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kd', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def test_get_confirm_delete(self):
        url = reverse('scenarios:delete', kwargs={'scenario_id': self.scenario.id})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.scenario.name)

    def test_post_deletes_scenario(self):
        scenario_id = self.scenario.id
        url = reverse('scenarios:delete', kwargs={'scenario_id': scenario_id})
        r = self.client.post(url)
        self.assertRedirects(r, reverse('scenarios:list'))
        self.assertFalse(Scenario.objects.filter(id=scenario_id).exists())


# ===========================================================================
# IV. STATUS UPDATE TESTS
# ===========================================================================

class ScenarioStatusUpdateTest(TestCase):

    def setUp(self):
        self.keeper = make_user('ks', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def _post_status(self, status):
        return self.client.post(
            reverse('scenarios:update_status', kwargs={'scenario_id': self.scenario.id}),
            {'status': status}
        )

    def test_update_to_active(self):
        self._post_status('ACTIVE')
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.status, 'ACTIVE')
        self.assertIsNotNone(self.scenario.started_at)

    def test_update_to_completed(self):
        self._post_status('COMPLETED')
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.status, 'COMPLETED')
        self.assertIsNotNone(self.scenario.ended_at)

    def test_invalid_status_ignored(self):
        self._post_status('INVALID')
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.status, 'PLANNING')


# ===========================================================================
# V. IN-GAME TIME TESTS
# ===========================================================================

class ScenarioTimeTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kt', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def test_advance_time_30_mins(self):
        original = self.scenario.in_game_time
        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 30}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.in_game_time, original + timedelta(minutes=30))

    def test_advance_time_60_mins(self):
        original = self.scenario.in_game_time
        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 60}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.in_game_time, original + timedelta(minutes=60))

    def test_advance_time_ajax_returns_json(self):
        r = self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 120},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertIn('in_game_time', data)

    def test_advance_time_ajax_day_change_returns_updated_cards(self):
        player = make_user('ajax_day')
        character = make_character(player, hp_current=8, hp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_time = self.scenario.in_game_time.replace(hour=21, minute=0, second=0, microsecond=0)
        self.scenario.in_game_day = 1
        self.scenario.save(update_fields=['in_game_time', 'in_game_day'])

        r = self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 300},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['day_changed'])
        self.assertEqual(len(data['updated_cards']), 1)
        self.assertEqual(data['updated_cards'][0]['character_id'], character.id)
        self.assertEqual(data['updated_cards'][0]['resources']['hp']['current'], 9)

    def test_advance_time_zero_not_applied(self):
        original = self.scenario.in_game_time
        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 0}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(
            self.scenario.in_game_time.replace(microsecond=0),
            original.replace(microsecond=0)
        )

    def test_advance_time_day_rollover_restores_hp(self):
        player = make_user('tp')
        character = make_character(player, hp_current=8, hp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_time = self.scenario.in_game_time.replace(hour=21, minute=0, second=0, microsecond=0)
        self.scenario.in_game_day = 1
        self.scenario.save(update_fields=['in_game_time', 'in_game_day'])

        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 300}
        )

        self.scenario.refresh_from_db()
        character.refresh_from_db()
        self.assertEqual(self.scenario.in_game_day, 2)
        self.assertEqual(character.hp_current, 9)

    def test_advance_time_hourly_restore_mp(self):
        player = make_user('mp_hourly')
        character = make_character(player, mp_current=3, mp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )

        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 120}
        )

        character.refresh_from_db()
        self.assertEqual(character.mp_current, 5)

    def test_advance_time_ajax_hourly_restore_returns_updated_cards_without_day_change(self):
        player = make_user('mp_ajax')
        character = make_character(player, mp_current=4, mp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_time = self.scenario.in_game_time.replace(hour=10, minute=0, second=0, microsecond=0)
        self.scenario.in_game_day = 1
        self.scenario.save(update_fields=['in_game_time', 'in_game_day'])

        r = self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 60},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['day_changed'])
        self.assertEqual(len(data['updated_cards']), 1)
        self.assertEqual(data['updated_cards'][0]['resources']['mp']['current'], 5)

    def test_advance_time_two_half_hours_restores_mp_once(self):
        player = make_user('mp_half_steps')
        character = make_character(player, mp_current=4, mp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_time = self.scenario.in_game_time.replace(hour=10, minute=0, second=0, microsecond=0)
        self.scenario.in_game_day = 1
        self.scenario.save(update_fields=['in_game_time', 'in_game_day'])

        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 30}
        )
        character.refresh_from_db()
        self.assertEqual(character.mp_current, 4)

        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 30}
        )
        character.refresh_from_db()
        self.assertEqual(character.mp_current, 5)

    def test_advance_time_multiple_days_restore_multiple_hp(self):
        player = make_user('multi')
        character = make_character(player, hp_current=5, hp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )

        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 2880}
        )

        self.scenario.refresh_from_db()
        character.refresh_from_db()
        self.assertEqual(self.scenario.in_game_day, 3)
        self.assertEqual(character.hp_current, 7)

    def test_advance_time_skips_characters_with_deep_wound(self):
        player = make_user('wounded')
        character = make_character(player, hp_current=8, hp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        deep_wound, _ = StatusEffect.objects.get_or_create(
            name='Deep Wound',
            defaults={
                'description': 'Blocks natural healing.',
                'effect_type': 'DEEP_WOUND',
            },
        )
        CharacterStatusEffect.objects.create(
            character=character,
            status_effect=deep_wound,
            remaining_rounds=999999,
        )

        self.client.post(
            reverse('scenarios:advance_time', kwargs={'scenario_id': self.scenario.id}),
            {'minutes': 1440}
        )

        character.refresh_from_db()
        self.assertEqual(character.hp_current, 8)

    def test_set_time_updates_in_game_time(self):
        # New endpoint accepts time-only HH:MM; date stays unchanged
        self.client.post(
            reverse('scenarios:set_time', kwargs={'scenario_id': self.scenario.id}),
            {'in_game_time': '14:30'}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.in_game_time.hour, 14)
        self.assertEqual(self.scenario.in_game_time.minute, 30)

    def test_set_time_ajax_day_change_returns_updated_cards(self):
        player = make_user('set_day')
        character = make_character(player, hp_current=7, hp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_day = 1
        self.scenario.save(update_fields=['in_game_day'])

        r = self.client.post(
            reverse('scenarios:set_time', kwargs={'scenario_id': self.scenario.id}),
            {'in_game_day': 2},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['day_changed'])
        self.assertEqual(data['updated_cards'][0]['resources']['hp']['current'], 8)

    def test_set_time_forward_hours_restores_mp(self):
        player = make_user('set_mp')
        character = make_character(player, mp_current=2, mp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_time = self.scenario.in_game_time.replace(hour=10, minute=0, second=0, microsecond=0)
        self.scenario.save(update_fields=['in_game_time'])

        self.client.post(
            reverse('scenarios:set_time', kwargs={'scenario_id': self.scenario.id}),
            {'in_game_time': '13:00'}
        )

        character.refresh_from_db()
        self.assertEqual(character.mp_current, 5)

    def test_set_time_ajax_hourly_restore_returns_updated_cards_without_day_change(self):
        player = make_user('set_ajax_mp')
        character = make_character(player, mp_current=1, mp_max=10)
        ScenarioPlayer.objects.create(
            scenario=self.scenario,
            player=player,
            character=character,
        )
        self.scenario.in_game_time = self.scenario.in_game_time.replace(hour=9, minute=0, second=0, microsecond=0)
        self.scenario.in_game_day = 1
        self.scenario.save(update_fields=['in_game_time', 'in_game_day'])

        r = self.client.post(
            reverse('scenarios:set_time', kwargs={'scenario_id': self.scenario.id}),
            {'in_game_time': '11:00'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )

        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertFalse(data['day_changed'])
        self.assertEqual(len(data['updated_cards']), 1)
        self.assertEqual(data['updated_cards'][0]['resources']['mp']['current'], 3)

    def test_set_time_invalid_format_does_not_change_time(self):
        original = self.scenario.in_game_time
        self.client.post(
            reverse('scenarios:set_time', kwargs={'scenario_id': self.scenario.id}),
            {'in_game_time': 'not-a-time'}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(
            self.scenario.in_game_time.replace(microsecond=0),
            original.replace(microsecond=0)
        )


# ===========================================================================
# VI. NOTES TESTS
# ===========================================================================

class ScenarioNotesTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kn', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def test_save_public_notes(self):
        self.client.post(
            reverse('scenarios:save_notes', kwargs={'scenario_id': self.scenario.id}),
            {'public_notes': 'The mansion is haunted.', 'keeper_notes': ''}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.public_notes, 'The mansion is haunted.')

    def test_save_keeper_notes(self):
        self.client.post(
            reverse('scenarios:save_notes', kwargs={'scenario_id': self.scenario.id}),
            {'public_notes': '', 'keeper_notes': 'Secret: butler did it.'}
        )
        self.scenario.refresh_from_db()
        self.assertEqual(self.scenario.keeper_notes, 'Secret: butler did it.')

    def test_save_notes_ajax_returns_json(self):
        r = self.client.post(
            reverse('scenarios:save_notes', kwargs={'scenario_id': self.scenario.id}),
            {'public_notes': 'Public', 'keeper_notes': 'Private'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ok'])


# ===========================================================================
# VII. INVITATION TESTS
# ===========================================================================

class InvitationTests(TestCase):

    def setUp(self):
        self.keeper = make_user('ki', is_keeper=True)
        self.player = make_user('pi')
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def _make_invite(self):
        return Invitation.objects.create(
            scenario=self.scenario,
            invited_by=self.keeper,
            invite_code=secrets.token_urlsafe(16)
        )

    def test_create_invitation_via_endpoint(self):
        self.client.post(
            reverse('scenarios:invite_create', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(Invitation.objects.filter(scenario=self.scenario).count(), 1)

    def test_invitation_has_unique_code(self):
        self.client.post(
            reverse('scenarios:invite_create', kwargs={'scenario_id': self.scenario.id})
        )
        self.client.post(
            reverse('scenarios:invite_create', kwargs={'scenario_id': self.scenario.id})
        )
        codes = list(Invitation.objects.filter(scenario=self.scenario).values_list('invite_code', flat=True))
        self.assertEqual(len(codes), len(set(codes)))

    def test_invite_refresh_replaces_existing(self):
        """Refresh should delete old unused invitations and create exactly one new one."""
        self._make_invite()
        self._make_invite()
        self.assertEqual(Invitation.objects.filter(scenario=self.scenario, is_used=False).count(), 2)
        self.client.post(
            reverse('scenarios:invite_refresh', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(Invitation.objects.filter(scenario=self.scenario, is_used=False).count(), 1)

    def test_revoke_invitation(self):
        inv = self._make_invite()
        self.client.post(
            reverse('scenarios:invite_revoke', kwargs={
                'scenario_id': self.scenario.id,
                'invite_id': inv.id,
            })
        )
        self.assertFalse(Invitation.objects.filter(id=inv.id).exists())

    def test_scenario_created_via_view_auto_creates_invitation(self):
        self.client.post(reverse('scenarios:create'), {
            'name': 'Auto Invite Test',
            'visibility': 'PRIVATE',
            'status': 'PLANNING',
        })
        s = Scenario.objects.get(name='Auto Invite Test')
        self.assertEqual(Invitation.objects.filter(scenario=s).count(), 1)

    def test_join_via_valid_invite(self):
        inv = self._make_invite()
        char = make_character(self.player)
        self.client.force_login(self.player)
        self.client.post(
            reverse('scenarios:join', kwargs={'invite_code': inv.invite_code}),
            {'character_id': char.id}
        )
        self.assertTrue(
            ScenarioPlayer.objects.filter(scenario=self.scenario, player=self.player).exists()
        )
        inv.refresh_from_db()
        self.assertTrue(inv.is_used)

    def test_join_via_invalid_invite_redirects(self):
        self.client.force_login(self.player)
        r = self.client.post(
            reverse('scenarios:join', kwargs={'invite_code': 'invalid-code-xyz'}),
            {}
        )
        self.assertRedirects(r, reverse('dashboard'))

    def test_join_already_participant_redirects(self):
        inv = self._make_invite()
        char = make_character(self.player)
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player, character=char)
        self.client.force_login(self.player)
        r = self.client.get(
            reverse('scenarios:join', kwargs={'invite_code': inv.invite_code})
        )
        self.assertRedirects(r, reverse('scenarios:detail', kwargs={'scenario_id': self.scenario.id}))

    def test_join_get_shows_character_selection(self):
        inv = self._make_invite()
        char = make_character(self.player)
        self.client.force_login(self.player)
        r = self.client.get(
            reverse('scenarios:join', kwargs={'invite_code': inv.invite_code})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, char.name)


# ===========================================================================
# VIII. PLAYER MANAGEMENT TESTS
# ===========================================================================

class PlayerManagementTests(TestCase):

    def setUp(self):
        self.keeper = make_user('km', is_keeper=True)
        self.player = make_user('pm')
        self.scenario = make_scenario(self.keeper)
        self.char = make_character(self.player)
        self.sp = ScenarioPlayer.objects.create(
            scenario=self.scenario, player=self.player, character=self.char
        )
        self.client.force_login(self.keeper)

    def test_remove_player(self):
        self.client.post(
            reverse('scenarios:player_remove', kwargs={
                'scenario_id': self.scenario.id,
                'player_id': self.player.id,
            })
        )
        self.assertFalse(
            ScenarioPlayer.objects.filter(scenario=self.scenario, player=self.player).exists()
        )


# ===========================================================================
# IX. NPC MANAGEMENT TESTS
# ===========================================================================

class ScenarioNPCManagementTests(TestCase):

    def setUp(self):
        self.keeper = make_user('kn2', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def test_create_npc_quick(self):
        self.client.post(
            reverse('scenarios:npc_create', kwargs={'scenario_id': self.scenario.id}),
            {
                'npc_name': 'Quick Ghoul',
                'npc_hp': 8,
                'npc_occupation': 'Monster',
                'npc_str': 70, 'npc_con': 60, 'npc_dex': 50,
                'npc_int': 20, 'npc_pow': 20, 'npc_siz': 70,
                'npc_app': 10, 'npc_edu': 10,
            }
        )
        npc = Character.objects.filter(name='Quick Ghoul', character_type='NPC').first()
        self.assertIsNotNone(npc)
        self.assertTrue(ScenarioNPC.objects.filter(scenario=self.scenario, npc=npc).exists())

    def test_create_npc_missing_name_rejected(self):
        self.client.post(
            reverse('scenarios:npc_create', kwargs={'scenario_id': self.scenario.id}),
            {'npc_name': ''}
        )
        self.assertEqual(ScenarioNPC.objects.filter(scenario=self.scenario).count(), 0)

    def test_add_npc_from_template(self):
        tpl = make_npc_template('Zombie')
        self.client.post(
            reverse('scenarios:npc_from_template', kwargs={'scenario_id': self.scenario.id}),
            {'template_id': tpl.id, 'display_name': ''}
        )
        self.assertEqual(ScenarioNPC.objects.filter(scenario=self.scenario).count(), 1)
        snpc = ScenarioNPC.objects.get(scenario=self.scenario)
        self.assertEqual(snpc.source_template, tpl)
        self.assertEqual(snpc.npc.name, 'Zombie')

    def test_add_npc_from_template_with_display_name(self):
        tpl = make_npc_template('Skeleton')
        self.client.post(
            reverse('scenarios:npc_from_template', kwargs={'scenario_id': self.scenario.id}),
            {'template_id': tpl.id, 'display_name': 'Skeleton Guard'}
        )
        snpc = ScenarioNPC.objects.get(scenario=self.scenario)
        self.assertEqual(snpc.display_name, 'Skeleton Guard')
        self.assertEqual(snpc.npc.name, 'Skeleton Guard')

    def test_add_npc_from_template_uses_status_hp(self):
        tpl = make_npc_template('Ghoul')
        self.client.post(
            reverse('scenarios:npc_from_template', kwargs={'scenario_id': self.scenario.id}),
            {'template_id': tpl.id, 'display_name': ''}
        )
        npc = ScenarioNPC.objects.get(scenario=self.scenario).npc
        self.assertEqual(npc.hp_max, 12)
        self.assertEqual(npc.hp_current, 12)

    def test_clone_npc(self):
        tpl = make_npc_template('Cultist')
        self.client.post(
            reverse('scenarios:npc_from_template', kwargs={'scenario_id': self.scenario.id}),
            {'template_id': tpl.id, 'display_name': ''}
        )
        snpc = ScenarioNPC.objects.get(scenario=self.scenario)
        self.client.post(
            reverse('scenarios:npc_clone', kwargs={
                'scenario_id': self.scenario.id,
                'snpc_id': snpc.id,
            })
        )
        self.assertEqual(ScenarioNPC.objects.filter(scenario=self.scenario).count(), 2)
        clone_snpc = ScenarioNPC.objects.filter(scenario=self.scenario).exclude(id=snpc.id).first()
        self.assertIn('#', clone_snpc.npc.name)

    def test_clone_npc_creates_separate_character_record(self):
        tpl = make_npc_template('Vampire')
        self.client.post(
            reverse('scenarios:npc_from_template', kwargs={'scenario_id': self.scenario.id}),
            {'template_id': tpl.id, 'display_name': ''}
        )
        snpc = ScenarioNPC.objects.get(scenario=self.scenario)
        self.client.post(
            reverse('scenarios:npc_clone', kwargs={
                'scenario_id': self.scenario.id,
                'snpc_id': snpc.id,
            })
        )
        npcs = list(ScenarioNPC.objects.filter(scenario=self.scenario))
        self.assertNotEqual(npcs[0].npc_id, npcs[1].npc_id)

    def test_remove_npc(self):
        npc = make_character(self.keeper, character_type='NPC', name='Foo')
        snpc = ScenarioNPC.objects.create(scenario=self.scenario, npc=npc)
        self.client.post(
            reverse('scenarios:npc_remove', kwargs={
                'scenario_id': self.scenario.id,
                'snpc_id': snpc.id,
            })
        )
        self.assertFalse(ScenarioNPC.objects.filter(id=snpc.id).exists())

    def test_npc_wizard_link_contains_scenario_id(self):
        """The manage page should render an NPC wizard link with add_to_scenario param."""
        r = self.client.get(
            reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertContains(r, f'add_to_scenario={self.scenario.id}')


# ===========================================================================
# X. SCENARIO LIST / ARCHIVE TESTS
# ===========================================================================

class ScenarioListTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kl', is_keeper=True)
        self.player = make_user('pl')
        self.client.force_login(self.player)

    def test_list_shows_active_scenarios(self):
        s_active = make_scenario(self.keeper, name='Active S', status='ACTIVE')
        char = make_character(self.player)
        ScenarioPlayer.objects.create(scenario=s_active, player=self.player, character=char)
        r = self.client.get(reverse('scenarios:list'))
        self.assertContains(r, 'Active S')

    def test_list_does_not_show_completed(self):
        s_done = make_scenario(self.keeper, name='Done S', status='COMPLETED')
        char = make_character(self.player)
        ScenarioPlayer.objects.create(scenario=s_done, player=self.player, character=char)
        r = self.client.get(reverse('scenarios:list'))
        self.assertNotContains(r, 'Done S')

    def test_archive_shows_completed(self):
        s_done = make_scenario(self.keeper, name='Old Haunting', status='COMPLETED')
        char = make_character(self.player)
        ScenarioPlayer.objects.create(scenario=s_done, player=self.player, character=char)
        r = self.client.get(reverse('scenarios:archive'))
        self.assertContains(r, 'Old Haunting')


# ===========================================================================
# XI. SCENARIO DETAIL (PLAYER VIEW) TESTS
# ===========================================================================

class ScenarioDetailTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kdet', is_keeper=True)
        self.player = make_user('pdet')
        self.scenario = make_scenario(self.keeper)
        self.char = make_character(self.player)

    def test_player_can_view_own_scenario(self):
        ScenarioPlayer.objects.create(
            scenario=self.scenario, player=self.player, character=self.char
        )
        self.client.force_login(self.player)
        r = self.client.get(
            reverse('scenarios:detail', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.scenario.name)

    def test_non_participant_redirected(self):
        self.client.force_login(self.player)
        r = self.client.get(
            reverse('scenarios:detail', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertRedirects(r, reverse('scenarios:list'))

    def test_keeper_can_view_own_scenario(self):
        self.client.force_login(self.keeper)
        r = self.client.get(
            reverse('scenarios:detail', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(r.status_code, 200)

    def test_detail_shows_private_session_notes_area(self):
        ScenarioPlayer.objects.create(
            scenario=self.scenario, player=self.player, character=self.char
        )
        self.client.force_login(self.player)
        r = self.client.get(reverse('scenarios:detail', kwargs={'scenario_id': self.scenario.id}))
        self.assertContains(r, 'Your Private Session Notes')

    def test_snapshot_returns_time_and_structured_sheet_data(self):
        ScenarioPlayer.objects.create(
            scenario=self.scenario, player=self.player, character=self.char
        )
        self.client.force_login(self.player)
        r = self.client.get(reverse('scenarios:player_snapshot', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(r.status_code, 200)
        payload = r.json()
        self.assertTrue(payload['ok'])
        self.assertIn('day', payload)
        self.assertIn('time', payload)
        self.assertTrue(payload['has_alive_character'])
        self.assertIn('sheet', payload)
        self.assertEqual(payload['sheet']['summary']['name'], self.char.name)
        self.assertEqual(payload['sheet']['resources']['hp']['current'], self.char.hp_current)
        self.assertIn('skills', payload['sheet'])
        self.assertIn('default_skills', payload['sheet'])
        self.assertIn('combat_skills', payload['sheet'])
        self.assertIn('weapons', payload['sheet'])
        self.assertIn('items', payload['sheet'])
        self.assertIn('spells', payload['sheet'])
        self.assertNotIn('sections', payload['sheet'])

    def test_player_can_save_private_session_notes(self):
        sp = ScenarioPlayer.objects.create(
            scenario=self.scenario, player=self.player, character=self.char
        )
        self.client.force_login(self.player)
        r = self.client.post(
            reverse('scenarios:player_private_notes', kwargs={'scenario_id': self.scenario.id}),
            {'private_notes': 'My secret clue notes'},
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ok'])
        sp.refresh_from_db()
        self.assertEqual(sp.private_notes, 'My secret clue notes')


# ===========================================================================
# XII. STATUS EFFECTS TESTS
# ===========================================================================

class ScenarioStatusEffectsTest(TestCase):

    def setUp(self):
        self.keeper = make_user('keff', is_keeper=True)
        self.player = make_user('peff')
        self.scenario = make_scenario(self.keeper)
        self.character = make_character(self.player)
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player, character=self.character)
        self.client.force_login(self.keeper)

    def test_manage_page_renders_effects_ui_and_badge(self):
        deep_wound, _ = StatusEffect.objects.get_or_create(
            name='Deep Wound',
            defaults={'description': 'Serious injury', 'effect_type': 'DEEP_WOUND'},
        )
        CharacterStatusEffect.objects.create(
            character=self.character,
            status_effect=deep_wound,
            remaining_rounds=999999,
        )

        r = self.client.get(reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Manage effects')
        self.assertContains(r, 'Deep Wound')

    def test_get_effects_returns_status_effect_id_for_remove_flow(self):
        deep_wound, _ = StatusEffect.objects.get_or_create(
            name='Deep Wound',
            defaults={'description': 'Serious injury', 'effect_type': 'DEEP_WOUND'},
        )
        CharacterStatusEffect.objects.create(
            character=self.character,
            status_effect=deep_wound,
            remaining_rounds=999999,
        )

        r = self.client.get(
            reverse('scenarios:character_get_effects', kwargs={'scenario_id': self.scenario.id, 'character_id': self.character.id})
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['effects'][0]['id'], deep_wound.id)

        remove = self.client.post(
            reverse('scenarios:character_remove_effect', kwargs={
                'scenario_id': self.scenario.id,
                'character_id': self.character.id,
                'effect_id': deep_wound.id,
            })
        )
        self.assertEqual(remove.status_code, 200)
        self.assertTrue(remove.json()['ok'])
        self.assertFalse(
            CharacterStatusEffect.objects.filter(character=self.character, status_effect=deep_wound).exists()
        )


# ===========================================================================
# XIII. MESSAGING TESTS
# ===========================================================================

class ScenarioMessagingTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kmsg', is_keeper=True)
        self.player = make_user('pmsg')
        self.other_player = make_user('pmsg2')
        self.scenario = make_scenario(self.keeper)
        self.character = make_character(self.player)
        self.other_character = make_character(self.other_player, name='Other Hero')
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player, character=self.character)
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.other_player, character=self.other_character)
        self.client.force_login(self.keeper)

    def test_keeper_can_send_private_message_to_player(self):
        response = self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PRIVATE', 'recipient_id': self.player.id, 'content': 'Keep your head down.'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        message = Message.objects.get()
        self.assertEqual(message.recipient, self.player)
        self.assertEqual(message.message_type, 'PRIVATE')
        self.assertTrue(MessageReceipt.objects.filter(message=message, user=self.player, read_at__isnull=True).exists())

    def test_public_message_is_rejected(self):
        response = self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PUBLIC', 'content': 'Everyone roll spot hidden.'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_snapshot_reports_unread_messages_for_player(self):
        self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PRIVATE', 'recipient_id': self.player.id, 'content': 'Secret warning'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.client.force_login(self.player)
        response = self.client.get(reverse('scenarios:player_snapshot', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['unread_messages'], 1)

    def test_get_messages_does_not_auto_mark_read(self):
        self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PRIVATE', 'recipient_id': self.player.id, 'content': 'Do not panic.'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.client.force_login(self.player)
        messages_response = self.client.get(reverse('scenarios:get_messages', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(messages_response.status_code, 200)
        self.assertEqual(messages_response.json()['unread_count'], 1)

        snapshot_response = self.client.get(reverse('scenarios:player_snapshot', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(snapshot_response.json()['unread_messages'], 1)

    def test_mark_messages_read_clears_unread_count(self):
        self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PRIVATE', 'recipient_id': self.player.id, 'content': 'Read this now.'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.client.force_login(self.player)
        mark_response = self.client.post(
            reverse('scenarios:mark_messages_read', kwargs={'scenario_id': self.scenario.id}),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(mark_response.status_code, 200)
        self.assertTrue(mark_response.json()['ok'])

        snapshot_response = self.client.get(reverse('scenarios:player_snapshot', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(snapshot_response.json()['unread_messages'], 0)

    def test_keeper_cannot_send_private_message_to_nonparticipant(self):
        outsider = make_user('outsider')
        response = self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PRIVATE', 'recipient_id': outsider.id, 'content': 'Nope'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 404)

    def test_private_message_requires_recipient(self):
        response = self.client.post(
            reverse('scenarios:send_message', kwargs={'scenario_id': self.scenario.id}),
            {'message_type': 'PRIVATE', 'content': 'Missing target'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)

    def test_manage_page_renders_messages_tab(self):
        response = self.client.get(reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages')
        self.assertContains(response, 'Send Message')


# ===========================================================================
# XIV. MANAGE PAGE TESTS
# ===========================================================================

class ScenarioManageTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kmng', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def test_manage_page_loads(self):
        r = self.client.get(
            reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, self.scenario.name)
        self.assertContains(r, 'Characters and NPCs in Session')
        self.assertContains(r, 'NPCs')
        self.assertContains(r, 'Notes')

    def test_manage_page_shows_npc_templates(self):
        tpl = make_npc_template('Shoggoth')
        r = self.client.get(
            reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertContains(r, 'Shoggoth')

    def test_manage_page_shows_players(self):
        player = make_user('player_in')
        char = make_character(player)
        ScenarioPlayer.objects.create(scenario=self.scenario, player=player, character=char)
        r = self.client.get(
            reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertContains(r, player.username)


# ===========================================================================
# XV. FIGHT TAB MODE TESTS
# ===========================================================================

class ScenarioFightModeTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kfight', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

        self.player_a = make_user('fight_a')
        self.player_b = make_user('fight_b')
        self.char_a = make_character(self.player_a, name='Alice', dexterity=40)
        self.char_b = make_character(self.player_b, name='Bob', dexterity=70)
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player_a, character=self.char_a)
        ScenarioPlayer.objects.create(scenario=self.scenario, player=self.player_b, character=self.char_b)

        self.npc = make_character(self.keeper, character_type='NPC', name='Ghoul', dexterity=55)
        self.snpc = ScenarioNPC.objects.create(scenario=self.scenario, npc=self.npc, display_name='Ghoul #1')

    def _state(self):
        return self.client.get(reverse('scenarios:fight_state', kwargs={'scenario_id': self.scenario.id})).json()

    def test_manage_page_has_fight_tab(self):
        r = self.client.get(reverse('scenarios:manage', kwargs={'scenario_id': self.scenario.id}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Fight')
        self.assertContains(r, 'Add to fight')

    def test_fight_start_and_add_participants_sorted_by_dex(self):
        self.client.post(reverse('scenarios:fight_start', kwargs={'scenario_id': self.scenario.id}))
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_a.id})
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_b.id})
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.npc.id})

        state = self._state()
        self.assertTrue(state['active'])
        self.assertEqual([p['character_id'] for p in state['participants']], [self.char_b.id, self.npc.id, self.char_a.id])

    def test_prepared_weapon_doubles_dex_and_resorts(self):
        self.client.post(reverse('scenarios:fight_start', kwargs={'scenario_id': self.scenario.id}))
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_a.id})
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_b.id})

        state = self._state()
        participant_for_a = next(p for p in state['participants'] if p['character_id'] == self.char_a.id)
        self.client.post(
            reverse('scenarios:fight_set_prepared', kwargs={'scenario_id': self.scenario.id, 'participant_id': participant_for_a['participant_id']}),
            {'is_prepared': '1'},
        )

        state = self._state()
        self.assertEqual(state['participants'][0]['character_id'], self.char_a.id)
        self.assertEqual(state['participants'][0]['dex_effective'], self.char_a.dexterity * 2)

    def test_fight_end_clears_all_participants(self):
        self.client.post(reverse('scenarios:fight_start', kwargs={'scenario_id': self.scenario.id}))
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_a.id})
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_b.id})
        self.assertTrue(FightParticipant.objects.exists())

        self.client.post(reverse('scenarios:fight_end', kwargs={'scenario_id': self.scenario.id}))
        self.assertFalse(FightParticipant.objects.exists())
        self.assertFalse(FightEncounter.objects.filter(scenario=self.scenario, is_active=True).exists())

    def test_fight_round_counter_advances(self):
        self.client.post(reverse('scenarios:fight_start', kwargs={'scenario_id': self.scenario.id}))
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_a.id})
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_b.id})

        self.client.post(reverse('scenarios:fight_advance_turn', kwargs={'scenario_id': self.scenario.id}))
        state = self._state()
        self.assertEqual(state['round_number'], 2)

        self.client.post(reverse('scenarios:fight_advance_turn', kwargs={'scenario_id': self.scenario.id}))
        state = self._state()
        self.assertEqual(state['round_number'], 3)

    def test_fight_round_counter_reset(self):
        self.client.post(reverse('scenarios:fight_start', kwargs={'scenario_id': self.scenario.id}))
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_a.id})
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_b.id})
        self.client.post(reverse('scenarios:fight_advance_turn', kwargs={'scenario_id': self.scenario.id}))

        self.client.post(reverse('scenarios:fight_reset_turns', kwargs={'scenario_id': self.scenario.id}))
        state = self._state()
        self.assertEqual(state['round_number'], 1)

    def test_fight_cards_show_build_and_bonus_damage_boxes(self):
        self.client.post(reverse('scenarios:fight_start', kwargs={'scenario_id': self.scenario.id}))
        self.client.post(reverse('scenarios:fight_add_participant', kwargs={'scenario_id': self.scenario.id}), {'character_id': self.char_a.id})

        state = self._state()
        self.assertTrue(state['participants'])
        card_html = state['participants'][0]['card_html']
        self.assertIn('Build', card_html)
        self.assertIn('Bonus Damage', card_html)


# ===========================================================================
# XVI. FIGHT ENCOUNTER TESTS
# ===========================================================================

class FightEncounterTest(TestCase):

    def setUp(self):
        self.keeper = make_user('kf', is_keeper=True)
        self.scenario = make_scenario(self.keeper)
        self.client.force_login(self.keeper)

    def test_fight_page_loads_no_encounter(self):
        r = self.client.get(
            reverse('scenarios:fight', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'No Active Encounter')

    def test_post_starts_encounter(self):
        self.client.post(
            reverse('scenarios:fight', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertTrue(
            FightEncounter.objects.filter(scenario=self.scenario, is_active=True).exists()
        )

    def test_fight_page_shows_active_encounter(self):
        FightEncounter.objects.create(scenario=self.scenario)
        r = self.client.get(
            reverse('scenarios:fight', kwargs={'scenario_id': self.scenario.id})
        )
        self.assertContains(r, 'Round')
