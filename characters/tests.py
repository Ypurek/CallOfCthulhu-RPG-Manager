"""
Comprehensive test suite for the characters app.

Coverage:
  - Model unit tests (calculations, __str__, boundary values)
  - Helper-function unit tests (_to_int, _derive_secondary_stats, etc.)
  - View tests with equivalence partitions and boundary checks
  - State-transition integration tests:
      • Create template → load template → save as character
      • Create character → edit wizard → verify changelog
      • Import JSON → verify draft → save character
"""

import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from characters.models import (
    Character,
    CharacterChangeLog,
    CharacterItem,
    CharacterSkill,
    CharacterTemplate,
    NPCTemplate,
    CharacterWeapon,
    Item,
    Skill,
    Weapon,
)
from characters.views import (
    DEFAULT_UNARMED_WEAPON_NAME,
    DEFAULT_UNARMED_WEAPON_DAMAGE,
    NPC_TEMPLATE_WIZARD_META_KEY,
    NPC_WIZARD_SESSION_KEY,
    TEMPLATE_WIZARD_META_KEY,
    WIZARD_SESSION_KEY,
    _derive_secondary_stats,
    _to_int,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def make_character(owner, **kwargs):
    """Return a minimal saved Character using sane defaults."""
    defaults = dict(
        character_type='PC',
        is_alive=True,
        name='Test Character',
        strength=50, constitution=50, dexterity=50,
        intelligence=50, power=50, size=50,
        appearance=50, education=50,
        hp_current=10, hp_max=10,
        mp_current=10, mp_max=10,
        sanity_current=50, sanity_max=50, sanity_start=50,
        luck=50, movement=8, build=0, damage_bonus='0', cash=0,
    )
    defaults.update(kwargs)
    return Character.objects.create(owner=owner, **defaults)


def make_skills():
    """Return a dict of commonly needed Skill objects."""
    own_lang = Skill.objects.create(name='Own Language', category='language', base_value=0, description='Native language.')
    dodge = Skill.objects.create(name='Dodge', category='general', base_value=0, description='Dodge attacks.')
    brawl = Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='Brawl.')
    track = Skill.objects.create(name='Track', category='general', base_value=10, description='Track.')
    mythos = Skill.objects.create(name='Cthulhu Mythos', category='general', base_value=0, description='Mythos.')
    return {'own_language': own_lang, 'dodge': dodge, 'brawl': brawl, 'track': track, 'mythos': mythos}


# ===========================================================================
# I. MODEL UNIT TESTS
# ===========================================================================

class CharacterHpMpCalculationTests(TestCase):
    """Character.calculate_hp_max / calculate_mp_max boundary values."""

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')

    # EP: (STR+CON) // 10 — valid range 0..200 → 0..20
    def test_hp_max_typical(self):
        c = make_character(self.player, strength=60, constitution=55)
        self.assertEqual(c.calculate_hp_max(), 11)

    def test_hp_max_minimum_zero_stats(self):
        c = make_character(self.player, strength=0, constitution=0)
        self.assertEqual(c.calculate_hp_max(), 0)

    def test_hp_max_maximum_stats(self):
        c = make_character(self.player, strength=100, constitution=100)
        self.assertEqual(c.calculate_hp_max(), 20)

    def test_hp_max_boundary_9(self):
        # 49+50 = 99 → 9
        c = make_character(self.player, strength=49, constitution=50)
        self.assertEqual(c.calculate_hp_max(), 9)

    def test_hp_max_boundary_10(self):
        # 50+50 = 100 → 10
        c = make_character(self.player, strength=50, constitution=50)
        self.assertEqual(c.calculate_hp_max(), 10)

    def test_mp_max_typical(self):
        c = make_character(self.player, power=50)
        self.assertEqual(c.calculate_mp_max(), 10)

    def test_mp_max_zero_power(self):
        c = make_character(self.player, power=0)
        self.assertEqual(c.calculate_mp_max(), 0)

    def test_mp_max_max_power(self):
        c = make_character(self.player, power=100)
        self.assertEqual(c.calculate_mp_max(), 20)

    # Boundary: POW=4 → 0, POW=5 → 1
    def test_mp_max_boundary_4(self):
        c = make_character(self.player, power=4)
        self.assertEqual(c.calculate_mp_max(), 0)

    def test_mp_max_boundary_5(self):
        c = make_character(self.player, power=5)
        self.assertEqual(c.calculate_mp_max(), 1)


class CharacterBuildAndDamageBonusTests(TestCase):
    """Boundary values for calculate_build (transitions at 65, 85, 125, 165)."""

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')

    def _build(self, str_, siz):
        return make_character(self.player, strength=str_, size=siz).calculate_build()

    def test_build_minus2_below_65(self):
        self.assertEqual(self._build(32, 32), -2)   # total 64

    def test_build_minus1_at_65(self):
        self.assertEqual(self._build(33, 32), -1)   # total 65

    def test_build_minus1_at_84(self):
        self.assertEqual(self._build(42, 42), -1)   # total 84

    def test_build_zero_at_85(self):
        self.assertEqual(self._build(43, 42), 0)    # total 85

    def test_build_zero_at_124(self):
        self.assertEqual(self._build(62, 62), 0)    # total 124

    def test_build_plus1_at_125(self):
        self.assertEqual(self._build(63, 62), 1)    # total 125

    def test_build_plus1_at_164(self):
        self.assertEqual(self._build(82, 82), 1)    # total 164

    def test_build_plus2_at_165(self):
        self.assertEqual(self._build(83, 82), 2)    # total 165

    def test_damage_bonus_minus2(self):
        c = make_character(self.player, strength=32, size=32)
        self.assertEqual(c.calculate_damage_bonus(), '-2')

    def test_damage_bonus_minus1(self):
        c = make_character(self.player, strength=33, size=32)
        self.assertEqual(c.calculate_damage_bonus(), '-1')

    def test_damage_bonus_zero(self):
        c = make_character(self.player, strength=50, size=50)
        self.assertEqual(c.calculate_damage_bonus(), '0')

    def test_damage_bonus_1d4(self):
        c = make_character(self.player, strength=63, size=62)
        self.assertEqual(c.calculate_damage_bonus(), '1D4')

    def test_damage_bonus_1d6(self):
        c = make_character(self.player, strength=83, size=82)
        self.assertEqual(c.calculate_damage_bonus(), '1D6')


class CharacterStrTests(TestCase):
    """Character.__str__ and is_alive flag."""

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')

    def test_str_alive(self):
        c = make_character(self.player, name='Bob', is_alive=True)
        self.assertEqual(str(c), 'Bob (Alive)')

    def test_str_dead(self):
        c = make_character(self.player, name='Bob', is_alive=False)
        self.assertEqual(str(c), 'Bob (Dead)')


class SkillModelTests(TestCase):

    def test_str(self):
        skill = Skill.objects.create(name='Listen', category='general', base_value=20, description='')
        self.assertEqual(str(skill), 'Listen')

    def test_unique_name_constraint(self):
        Skill.objects.create(name='Spot Hidden', category='general', base_value=25, description='')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Skill.objects.create(name='Spot Hidden', category='general', base_value=25, description='')


class CharacterTemplateModelTests(TestCase):

    def setUp(self):
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')

    def test_str(self):
        t = CharacterTemplate.objects.create(name='My Template', payload={}, created_by=self.keeper)
        self.assertEqual(str(t), 'My Template')

    def test_default_ordering_by_name(self):
        CharacterTemplate.objects.create(name='Zed', payload={})
        CharacterTemplate.objects.create(name='Alpha', payload={})
        names = list(CharacterTemplate.objects.values_list('name', flat=True))
        self.assertEqual(names, sorted(names))

    def test_payload_is_json_field(self):
        payload = {'character_info': {'name': 'X'}, 'skills': {'Track': 25}}
        t = CharacterTemplate.objects.create(name='JSON Test', payload=payload)
        t.refresh_from_db()
        self.assertEqual(t.payload['skills']['Track'], 25)


class UserRoleTests(TestCase):

    def test_player_is_player(self):
        u = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.assertTrue(u.is_player())
        self.assertFalse(u.is_keeper())

    def test_keeper_is_keeper(self):
        u = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.assertTrue(u.is_keeper())
        self.assertFalse(u.is_player())

    def test_default_role_is_player(self):
        u = User.objects.create_user(username='d', password='x')
        self.assertTrue(u.is_player())


# ===========================================================================
# II. HELPER FUNCTION UNIT TESTS
# ===========================================================================

class ToIntHelperTests(TestCase):
    """Boundary and equivalence tests for _to_int."""

    def test_normal_integer_string(self):
        self.assertEqual(_to_int('42'), 42)

    def test_none_returns_default(self):
        self.assertEqual(_to_int(None, default=7), 7)

    def test_empty_string_returns_default(self):
        self.assertEqual(_to_int('', default=5), 5)

    def test_non_numeric_string_returns_default(self):
        self.assertEqual(_to_int('abc', default=3), 3)

    def test_minimum_clamp(self):
        self.assertEqual(_to_int(-10, minimum=0), 0)

    def test_maximum_clamp(self):
        self.assertEqual(_to_int(200, maximum=100), 100)

    def test_minimum_and_maximum_both_clamped(self):
        self.assertEqual(_to_int(-5, minimum=0, maximum=100), 0)
        self.assertEqual(_to_int(150, minimum=0, maximum=100), 100)

    def test_value_within_range_unchanged(self):
        self.assertEqual(_to_int(50, minimum=0, maximum=100), 50)

    def test_at_minimum_boundary(self):
        self.assertEqual(_to_int(0, minimum=0, maximum=100), 0)

    def test_at_maximum_boundary(self):
        self.assertEqual(_to_int(100, minimum=0, maximum=100), 100)

    def test_float_string_returns_default(self):
        # int('3.5') raises ValueError → returns default
        self.assertEqual(_to_int('3.5', default=0), 0)

    def test_integer_passed_directly(self):
        self.assertEqual(_to_int(99), 99)

    def test_negative_integer_no_clamp(self):
        self.assertEqual(_to_int(-50), -50)


class DeriveSecondaryStatsTests(TestCase):
    """Boundary values for _derive_secondary_stats."""

    def _stats(self, str_=50, con=50, pow_=50):
        return {'strength': str_, 'constitution': con, 'power': pow_,
                'dexterity': 50, 'intelligence': 50, 'size': 50,
                'appearance': 50, 'education': 50, 'luck': 50}

    def test_typical_values(self):
        result = _derive_secondary_stats(self._stats(60, 55, 65))
        self.assertEqual(result['hp_max'], 11)
        self.assertEqual(result['mp_max'], 13)
        self.assertEqual(result['sanity_max'], 99)

    def test_hp_min_is_1_when_stats_are_zero(self):
        result = _derive_secondary_stats({'strength': 0, 'constitution': 0, 'power': 0})
        self.assertEqual(result['hp_max'], 1)

    def test_mp_min_is_1_when_power_zero(self):
        result = _derive_secondary_stats({'strength': 50, 'constitution': 50, 'power': 0})
        self.assertEqual(result['mp_max'], 1)

    def test_sanity_reduced_by_cthulhu_mythos(self):
        result = _derive_secondary_stats(self._stats(), cthulhu_mythos=20)
        self.assertEqual(result['sanity_max'], 79)

    def test_sanity_zero_at_max_mythos(self):
        result = _derive_secondary_stats(self._stats(), cthulhu_mythos=99)
        self.assertEqual(result['sanity_max'], 0)

    def test_hp_current_equals_hp_max_initial(self):
        result = _derive_secondary_stats(self._stats())
        self.assertEqual(result['hp_current'], result['hp_max'])

    def test_mp_current_equals_mp_max_initial(self):
        result = _derive_secondary_stats(self._stats())
        self.assertEqual(result['mp_current'], result['mp_max'])

    def test_sanity_start_equals_sanity_max(self):
        result = _derive_secondary_stats(self._stats())
        self.assertEqual(result['sanity_start'], result['sanity_max'])

    def test_maximum_stats_gives_correct_hp(self):
        result = _derive_secondary_stats(self._stats(100, 100, 100))
        self.assertEqual(result['hp_max'], 20)
        self.assertEqual(result['mp_max'], 20)


# ===========================================================================
# III. VIEW TESTS
# ===========================================================================

class CharacterListViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.other = User.objects.create_user(username='o', password='x', role='PLAYER')
        self.alive = make_character(self.player, name='Alive', is_alive=True)
        self.dead = make_character(self.player, name='Dead', is_alive=False)
        self.other_char = make_character(self.other, name='Other')

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('characters:list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response['Location'])

    def test_only_own_alive_pcs_shown(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:list'))
        chars = list(response.context['characters'])
        self.assertIn(self.alive, chars)
        self.assertNotIn(self.dead, chars)
        self.assertNotIn(self.other_char, chars)

    def test_empty_list_for_new_user(self):
        new_user = User.objects.create_user(username='n', password='x', role='PLAYER')
        self.client.login(username='n', password='x')
        response = self.client.get(reverse('characters:list'))
        self.assertQuerySetEqual(response.context['characters'], [])


class CharacterDetailViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.other = User.objects.create_user(username='o', password='x', role='PLAYER')
        self.char = make_character(self.player, name='Hero')

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('characters:detail', args=[self.char.id]))
        self.assertEqual(response.status_code, 302)

    def test_owner_can_view(self):
        self.client.login(username='p', password='x')
        self.assertEqual(self.client.get(reverse('characters:detail', args=[self.char.id])).status_code, 200)

    def test_other_user_gets_404(self):
        self.client.login(username='o', password='x')
        self.assertEqual(self.client.get(reverse('characters:detail', args=[self.char.id])).status_code, 404)

    def test_post_saves_player_notes(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:detail', args=[self.char.id]), {'player_notes': 'My note'})
        self.char.refresh_from_db()
        self.assertEqual(self.char.player_notes, 'My note')

    def test_post_strips_whitespace_from_notes(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:detail', args=[self.char.id]), {'player_notes': '  spaces  '})
        self.char.refresh_from_db()
        self.assertEqual(self.char.player_notes, 'spaces')

    def test_post_empty_notes_clears_field(self):
        self.char.player_notes = 'old note'
        self.char.save()
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:detail', args=[self.char.id]), {'player_notes': ''})
        self.char.refresh_from_db()
        self.assertEqual(self.char.player_notes, '')

    def test_post_redirects_after_save(self):
        self.client.login(username='p', password='x')
        response = self.client.post(
            reverse('characters:detail', args=[self.char.id]), {'player_notes': 'x'})
        self.assertRedirects(response, reverse('characters:detail', args=[self.char.id]))


class CharacterDeleteViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.other = User.objects.create_user(username='o', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.char = make_character(self.player)

    def test_owner_can_delete(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:delete', args=[self.char.id]))
        self.assertFalse(Character.objects.filter(id=self.char.id).exists())

    def test_keeper_can_delete_any_character(self):
        self.client.login(username='k', password='x')
        self.client.post(reverse('characters:delete', args=[self.char.id]))
        self.assertFalse(Character.objects.filter(id=self.char.id).exists())

    def test_non_owner_cannot_delete(self):
        self.client.login(username='o', password='x')
        self.client.post(reverse('characters:delete', args=[self.char.id]))
        self.assertTrue(Character.objects.filter(id=self.char.id).exists())

    def test_get_does_not_delete(self):
        self.client.login(username='p', password='x')
        self.client.get(reverse('characters:delete', args=[self.char.id]))
        self.assertTrue(Character.objects.filter(id=self.char.id).exists())

    def test_delete_non_existent_returns_404(self):
        self.client.login(username='p', password='x')
        response = self.client.post(reverse('characters:delete', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_delete_redirects_to_list(self):
        self.client.login(username='p', password='x')
        response = self.client.post(reverse('characters:delete', args=[self.char.id]))
        self.assertRedirects(response, reverse('characters:list'))


class CharacterEditAjaxTests(TestCase):
    """AJAX variant of character_edit: stat update + add_skill."""

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.other = User.objects.create_user(username='o', password='x', role='PLAYER')
        self.char = make_character(self.player, strength=50)

    def _ajax(self, payload):
        return self.client.post(
            reverse('characters:edit', args=[self.char.id]),
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_owner_can_update_stat(self):
        self.client.login(username='p', password='x')
        self._ajax({'stat': 'strength', 'value': 70})
        self.char.refresh_from_db()
        self.assertEqual(self.char.strength, 70)

    def test_keeper_can_update_stat(self):
        keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.client.login(username='k', password='x')
        response = self._ajax({'stat': 'strength', 'value': 60})
        self.assertJSONEqual(response.content, {'success': True})

    def test_other_user_redirected_on_get(self):
        self.client.login(username='o', password='x')
        response = self.client.get(reverse('characters:edit', args=[self.char.id]))
        self.assertEqual(response.status_code, 302)

    def test_add_skill_creates_and_attaches(self):
        self.client.login(username='p', password='x')
        self._ajax({'action': 'add_skill', 'skill_name': 'Surfing', 'skill_value': 30})
        self.assertTrue(CharacterSkill.objects.filter(character=self.char, skill__name='Surfing', value=30).exists())

    def test_add_skill_without_name_returns_error(self):
        self.client.login(username='p', password='x')
        response = self._ajax({'action': 'add_skill', 'skill_name': '', 'skill_value': 30})
        self.assertFalse(json.loads(response.content)['success'])

    def test_add_skill_value_above_100_clamped(self):
        self.client.login(username='p', password='x')
        self._ajax({'action': 'add_skill', 'skill_name': 'Juggling', 'skill_value': 150})
        val = CharacterSkill.objects.get(character=self.char, skill__name='Juggling').value
        self.assertLessEqual(val, 100)

    def test_add_skill_value_below_0_clamped(self):
        self.client.login(username='p', password='x')
        self._ajax({'action': 'add_skill', 'skill_name': 'Juggling', 'skill_value': -5})
        val = CharacterSkill.objects.get(character=self.char, skill__name='Juggling').value
        self.assertGreaterEqual(val, 0)

    def test_add_skill_at_boundary_0(self):
        self.client.login(username='p', password='x')
        self._ajax({'action': 'add_skill', 'skill_name': 'Tai Chi', 'skill_value': 0})
        val = CharacterSkill.objects.get(character=self.char, skill__name='Tai Chi').value
        self.assertEqual(val, 0)

    def test_add_skill_at_boundary_100(self):
        self.client.login(username='p', password='x')
        self._ajax({'action': 'add_skill', 'skill_name': 'Master Art', 'skill_value': 100})
        val = CharacterSkill.objects.get(character=self.char, skill__name='Master Art').value
        self.assertEqual(val, 100)


class CharacterCemeteryViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.alive = make_character(self.player, name='Alive', is_alive=True)
        self.dead = make_character(self.player, name='Dead', is_alive=False)

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('characters:cemetery'))
        self.assertEqual(response.status_code, 302)

    def test_cemetery_shows_only_dead(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:cemetery'))
        chars = list(response.context['characters'])
        self.assertIn(self.dead, chars)
        self.assertNotIn(self.alive, chars)

    def test_empty_cemetery_for_user_with_no_dead(self):
        new_user = User.objects.create_user(username='n', password='x', role='PLAYER')
        self.client.login(username='n', password='x')
        response = self.client.get(reverse('characters:cemetery'))
        self.assertQuerySetEqual(response.context['characters'], [])


# ===========================================================================
# IV. TEMPLATE VIEW TESTS
# ===========================================================================

class CharacterTemplatesListViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.t1 = CharacterTemplate.objects.create(
            name='Scholar',
            payload={
                'character_info': {'name': 'Scholar', 'occupation': 'Professor', 'age': 40},
                'characteristics': {'STR': 40, 'CON': 50, 'DEX': 45, 'INT': 75,
                                    'APP': 50, 'POW': 60, 'SIZ': 50, 'EDU': 80, 'Luck': 55},
                'skills': {'Track': 30},
                'weapons': [],
                'inventory': [],
            },
        )

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('characters:templates'))
        self.assertEqual(response.status_code, 302)

    def test_player_can_view_templates(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:templates'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.t1.id, [t['id'] for t in response.context['templates']])

    def test_can_manage_templates_false_for_player(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:templates'))
        self.assertFalse(response.context['can_manage_templates'])

    def test_can_manage_templates_true_for_keeper(self):
        self.client.login(username='k', password='x')
        response = self.client.get(reverse('characters:templates'))
        self.assertTrue(response.context['can_manage_templates'])

    def test_empty_template_list_shown_gracefully(self):
        CharacterTemplate.objects.all().delete()
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:templates'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['templates'], [])


class TemplateDeleteViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.admin = User.objects.create_user(username='a', password='x', role='KEEPER',
                                              is_superuser=True, is_staff=True)
        self.template = CharacterTemplate.objects.create(
            name='Test Template',
            payload={'character_info': {'name': 'T'}, 'characteristics': {}, 'skills': {}},
        )

    def test_keeper_can_delete(self):
        self.client.login(username='k', password='x')
        self.client.post(reverse('characters:template_delete', args=[self.template.id]))
        self.assertFalse(CharacterTemplate.objects.filter(id=self.template.id).exists())

    def test_admin_can_delete(self):
        self.client.login(username='a', password='x')
        self.client.post(reverse('characters:template_delete', args=[self.template.id]))
        self.assertFalse(CharacterTemplate.objects.filter(id=self.template.id).exists())

    def test_player_cannot_delete(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:template_delete', args=[self.template.id]))
        self.assertTrue(CharacterTemplate.objects.filter(id=self.template.id).exists())

    def test_get_does_not_delete(self):
        self.client.login(username='k', password='x')
        self.client.get(reverse('characters:template_delete', args=[self.template.id]))
        self.assertTrue(CharacterTemplate.objects.filter(id=self.template.id).exists())

    def test_nonexistent_template_redirects_with_error(self):
        """template_delete returns 302 redirect with an error message for missing templates."""
        self.client.login(username='k', password='x')
        response = self.client.post(reverse('characters:template_delete', args=[99999]))
        self.assertRedirects(response, reverse('characters:templates'))

    def test_delete_redirects_to_templates(self):
        self.client.login(username='k', password='x')
        response = self.client.post(reverse('characters:template_delete', args=[self.template.id]))
        self.assertRedirects(response, reverse('characters:templates'))


class TemplateCreateWizardViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')

    def test_player_cannot_start_template_creation(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:template_create'))
        self.assertRedirects(response, reverse('characters:templates'))

    def test_keeper_redirected_to_wizard(self):
        self.client.login(username='k', password='x')
        response = self.client.get(reverse('characters:template_create'))
        self.assertRedirects(response, reverse('characters:create'))

    def test_keeper_session_has_create_meta(self):
        self.client.login(username='k', password='x')
        self.client.get(reverse('characters:template_create'))
        session = self.client.session
        self.assertIn(TEMPLATE_WIZARD_META_KEY, session)
        self.assertEqual(session[TEMPLATE_WIZARD_META_KEY]['mode'], 'create')

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('characters:template_create'))
        self.assertEqual(response.status_code, 302)


class TemplateEditWizardViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.template = CharacterTemplate.objects.create(
            name='Edit Me',
            payload={
                'character_info': {'name': 'Edit Me', 'occupation': '', 'age': ''},
                'characteristics': {'STR': 50, 'CON': 50, 'DEX': 50, 'INT': 50,
                                    'APP': 50, 'POW': 50, 'SIZ': 50, 'EDU': 50, 'Luck': 50},
                'skills': {},
                'weapons': [],
                'inventory': [],
            },
        )

    def test_player_cannot_start_edit(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:template_edit', args=[self.template.id]))
        self.assertRedirects(response, reverse('characters:templates'))

    def test_keeper_redirected_to_wizard(self):
        self.client.login(username='k', password='x')
        response = self.client.get(reverse('characters:template_edit', args=[self.template.id]))
        self.assertRedirects(response, reverse('characters:create'))

    def test_session_has_edit_meta_with_correct_id(self):
        self.client.login(username='k', password='x')
        self.client.get(reverse('characters:template_edit', args=[self.template.id]))
        session = self.client.session
        self.assertEqual(session[TEMPLATE_WIZARD_META_KEY]['mode'], 'edit')
        self.assertEqual(session[TEMPLATE_WIZARD_META_KEY]['template_id'], self.template.id)

    def test_nonexistent_template_redirects_with_error(self):
        self.client.login(username='k', password='x')
        response = self.client.get(reverse('characters:template_edit', args=[99999]))
        self.assertRedirects(response, reverse('characters:templates'))


class UseTemplateViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='')
        self.template = CharacterTemplate.objects.create(
            name='Quick Character',
            payload={
                'character_info': {'name': 'Quick Character', 'occupation': 'Artist', 'age': 28},
                'characteristics': {'STR': 50, 'CON': 55, 'DEX': 60, 'INT': 65,
                                    'APP': 70, 'POW': 50, 'SIZ': 50, 'EDU': 60, 'Luck': 45},
                'skills': {'Track': 20},
                'weapons': [],
                'inventory': [],
            },
        )

    def test_get_redirects_without_loading(self):
        self.client.login(username='p', password='x')
        self.client.get(reverse('characters:use_template', args=[self.template.id]))
        self.assertNotIn(WIZARD_SESSION_KEY, self.client.session)

    def test_post_loads_template_into_draft(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:use_template', args=[self.template.id]))
        draft = self.client.session[WIZARD_SESSION_KEY]
        self.assertEqual(draft['basic']['name'], 'Quick Character')
        self.assertEqual(draft['basic']['occupation'], 'Artist')
        self.assertEqual(draft['stats']['strength'], 50)
        self.assertEqual(draft['step'], 'basic')

    def test_post_redirects_to_create(self):
        self.client.login(username='p', password='x')
        response = self.client.post(reverse('characters:use_template', args=[self.template.id]))
        self.assertRedirects(response, reverse('characters:create'))

    def test_nonexistent_template_returns_404(self):
        self.client.login(username='p', password='x')
        response = self.client.post(reverse('characters:use_template', args=[99999]))
        self.assertEqual(response.status_code, 404)

    def test_unauthenticated_redirects(self):
        response = self.client.post(reverse('characters:use_template', args=[self.template.id]))
        self.assertEqual(response.status_code, 302)


class NPCTemplateViewTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p_npc', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k_npc', password='x', role='KEEPER')
        Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='')
        self.template = NPCTemplate.objects.create(
            name='Dock Guard',
            payload={
                'character_info': {'name': 'Dock Guard', 'occupation': 'Guard', 'age': 34},
                'characteristics': {'STR': 60, 'CON': 55, 'DEX': 45, 'INT': 40,
                                    'APP': 35, 'POW': 50, 'SIZ': 60, 'EDU': 45, 'Luck': 40},
                'skills': {'Fighting_Brawl': 45},
                'weapons': [],
                'inventory': [],
            },
        )

    def test_player_cannot_view_npc_templates(self):
        self.client.login(username='p_npc', password='x')
        response = self.client.get(reverse('characters:npc_templates'))
        self.assertRedirects(response, reverse('characters:templates'))

    def test_keeper_can_view_npc_templates(self):
        self.client.login(username='k_npc', password='x')
        response = self.client.get(reverse('characters:npc_templates'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.template.id, [t['id'] for t in response.context['templates']])

    def test_npc_create_wizard_bootstrap_sets_session(self):
        self.client.login(username='k_npc', password='x')
        response = self.client.get(reverse('characters:npc_template_create'))
        self.assertRedirects(response, reverse('characters:npc_create'))
        self.assertIn(NPC_WIZARD_SESSION_KEY, self.client.session)
        self.assertEqual(self.client.session[NPC_TEMPLATE_WIZARD_META_KEY]['mode'], 'create')

    def test_keeper_can_load_npc_template_into_wizard(self):
        self.client.login(username='k_npc', password='x')
        response = self.client.post(reverse('characters:npc_use_template', args=[self.template.id]))
        self.assertRedirects(response, reverse('characters:npc_create'))
        draft = self.client.session[NPC_WIZARD_SESSION_KEY]
        self.assertEqual(draft['basic']['name'], 'Dock Guard')
        self.assertEqual(draft['stats']['strength'], 60)

    def test_npc_next_moves_to_step_two_not_back_to_basic(self):
        self.client.login(username='k_npc', password='x')
        self.client.get(reverse('characters:npc_template_create'))
        response = self.client.post(reverse('characters:npc_create'), {
            'step': 'basic',
            'action': 'next',
            'name': 'Step Test NPC',
            'description': 'x',
            'occupation': 'Guard',
            'age': '30',
        })
        self.assertRedirects(response, reverse('characters:npc_create'))
        draft = self.client.session[NPC_WIZARD_SESSION_KEY]
        self.assertEqual(draft['step'], 'stats')

    def test_npc_review_adjust_hp_mp_saved_to_payload_status(self):
        self.client.login(username='k_npc', password='x')
        self.client.get(reverse('characters:npc_template_create'))
        self.client.post(reverse('characters:npc_create'), {
            'step': 'stats',
            'action': 'next',
            'strength': 60,
            'constitution': 40,
            'dexterity': 50,
            'intelligence': 50,
            'power': 60,
            'size': 50,
            'appearance': 50,
            'education': 50,
            'luck': 50,
        })
        response = self.client.post(reverse('characters:npc_create'), {
            'step': 'review',
            'action': 'save',
            'adjust_hp': '-2',
            'adjust_mp': '-3',
            'adjust_sanity': '0',
            'adjust_luck': '0',
        })
        self.assertRedirects(response, reverse('characters:npc_templates'))
        template = NPCTemplate.objects.exclude(id=self.template.id).latest('id')
        self.assertEqual(template.payload['status']['HP']['max'], 10)
        self.assertEqual(template.payload['status']['HP']['current'], 8)
        self.assertEqual(template.payload['status']['MP']['max'], 12)
        self.assertEqual(template.payload['status']['MP']['current'], 9)

    def test_nonexistent_npc_template_delete_redirects(self):
        self.client.login(username='k_npc', password='x')
        response = self.client.post(reverse('characters:npc_template_delete', args=[99999]))
        self.assertRedirects(response, reverse('characters:npc_templates'))

    def test_keeper_can_save_npc_template_from_wizard(self):
        self.client.login(username='k_npc', password='x')
        self.client.get(reverse('characters:npc_template_create'))
        response = self.client.post(reverse('characters:npc_create'), {'step': 'review', 'action': 'save'})
        self.assertRedirects(response, reverse('characters:npc_templates'))
        self.assertEqual(NPCTemplate.objects.count(), 2)


# ===========================================================================
# V. WIZARD CREATE TESTS (boundary + equivalence partitions)
# ===========================================================================

class CharacterCreateWizardTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='player', password='secret', role='PLAYER')
        self.keeper = User.objects.create_user(username='keeper', password='secret', role='KEEPER')
        self.skill_own_language = Skill.objects.create(
            name='Own Language', category='language', base_value=0, description='Native language skill.')
        self.skill_track = Skill.objects.create(
            name='Track', category='general', base_value=10, description='Track people and creatures.')
        self.skill_brawl = Skill.objects.create(
            name='Fighting (Brawl)', category='combat', base_value=25, description='Close combat.')
        self.weapon = Weapon.objects.create(name='Knife', skill_name='Fighting (Brawl)', damage='1D4')
        self.item = Item.objects.create(name='Flashlight', description='Useful light source.')

    # ── helpers ──

    def _post_basic(self, name='Investigator', occupation='Journalist', age=''):
        return self.client.post(reverse('characters:create'), {
            'step': 'basic', 'action': 'next',
            'name': name, 'description': 'Desc.', 'occupation': occupation, 'age': age,
        })

    def _post_stats(self, **overrides):
        stats = dict(strength=60, constitution=55, dexterity=50, intelligence=70,
                     power=65, size=45, appearance=40, education=80, luck=50)
        stats.update(overrides)
        return self.client.post(reverse('characters:create'), {'step': 'stats', 'action': 'next', **stats})

    def _post_skills(self, **extra):
        data = {'step': 'skills', 'action': 'next',
                f'skill_{self.skill_track.id}': 45, f'skill_{self.skill_brawl.id}': 60}
        data.update(extra)
        return self.client.post(reverse('characters:create'), data)

    def _post_inventory(self, weapons=None, items=None):
        return self.client.post(reverse('characters:create'), {
            'step': 'inventory', 'action': 'next',
            'weapons_json': json.dumps(weapons or []),
            'items_json': json.dumps(items or []),
        })

    def _post_save(self):
        return self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})

    # ── access ──

    def test_unauthenticated_redirects(self):
        response = self.client.get(reverse('characters:create'))
        self.assertEqual(response.status_code, 302)

    def test_create_page_accessible_to_player_and_keeper(self):
        for username in ('player', 'keeper'):
            self.client.login(username=username, password='secret')
            self.assertEqual(self.client.get(reverse('characters:create')).status_code, 200)

    def test_stats_step_renders_modal_triggers(self):
        self.client.login(username='player', password='secret')
        response = self.client.get(reverse('characters:create') + '?step=stats')
        self.assertContains(response, "showWizardStatModal('STR'", html=False)

    def test_inventory_step_weapon_modal_has_no_prepared_checkbox(self):
        self.client.login(username='player', password='secret')
        response = self.client.get(reverse('characters:create') + '?step=inventory')
        self.assertContains(response, 'id="weaponModal"', html=False)
        self.assertNotContains(response, 'id="weapon-prepared"', html=False)

    # ── full happy path ──

    def test_full_creation_stores_character_and_relations(self):
        self.client.login(username='player', password='secret')
        self._post_basic()
        self._post_stats()
        self._post_skills()
        self._post_inventory(
            weapons=[{'weapon_id': self.weapon.id, 'name': 'Knife',
                      'skill_id': self.skill_brawl.id, 'skill_name': 'Fighting (Brawl)',
                      'is_prepared': True, 'damage': '1D4'}],
            items=[{'item_id': self.item.id, 'quantity': 2}],
        )
        response = self._post_save()
        self.assertEqual(response.status_code, 302)
        c = Character.objects.get(name='Investigator')
        self.assertEqual(c.owner, self.player)
        self.assertTrue(CharacterSkill.objects.filter(character=c, skill=self.skill_track, value=45).exists())
        self.assertTrue(CharacterSkill.objects.filter(character=c, skill=self.skill_own_language, value=80).exists())
        self.assertTrue(CharacterWeapon.objects.filter(character=c, weapon__name='Knife', is_prepared=True).exists())
        self.assertTrue(CharacterWeapon.objects.filter(character=c, weapon__name=DEFAULT_UNARMED_WEAPON_NAME).exists())
        self.assertTrue(CharacterItem.objects.filter(character=c, item=self.item, quantity=2).exists())
        self.assertEqual(c.hp_max, 11)
        self.assertEqual(c.mp_max, 13)

    # ── boundary: stats ──

    def test_stat_below_0_clamped(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='ZeroStat')
        self._post_stats(strength=-99)
        self._post_skills()
        self._post_inventory()
        self._post_save()
        self.assertEqual(Character.objects.get(name='ZeroStat').strength, 0)

    def test_stat_above_100_clamped(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='MaxStat')
        self._post_stats(strength=999)
        self._post_skills()
        self._post_inventory()
        self._post_save()
        self.assertEqual(Character.objects.get(name='MaxStat').strength, 100)

    def test_stats_at_boundary_0(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='BndMin')
        self._post_stats(strength=0, constitution=0, power=0)
        self._post_skills()
        self._post_inventory()
        self._post_save()
        c = Character.objects.get(name='BndMin')
        self.assertEqual(c.strength, 0)
        self.assertEqual(c.hp_max, 1)    # floor of 1

    def test_stats_at_boundary_100(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='BndMax')
        self._post_stats(strength=100, constitution=100, power=100)
        self._post_skills()
        self._post_inventory()
        self._post_save()
        c = Character.objects.get(name='BndMax')
        self.assertEqual(c.strength, 100)
        self.assertEqual(c.hp_max, 20)
        self.assertEqual(c.mp_max, 20)

    # ── boundary: age ──

    def test_age_missing_stores_none(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='NoAge', age='')
        self._post_stats(); self._post_skills(); self._post_inventory(); self._post_save()
        self.assertIsNone(Character.objects.get(name='NoAge').age)

    def test_age_stored_correctly(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='Aged', age='35')
        self._post_stats(); self._post_skills(); self._post_inventory(); self._post_save()
        self.assertEqual(Character.objects.get(name='Aged').age, 35)

    # ── unarmed always present ──

    def test_unarmed_weapon_always_added(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='NoWeapons')
        self._post_stats(); self._post_skills(); self._post_inventory(); self._post_save()
        c = Character.objects.get(name='NoWeapons')
        self.assertTrue(CharacterWeapon.objects.filter(character=c, weapon__name=DEFAULT_UNARMED_WEAPON_NAME).exists())

    # ── reset ──

    def test_reset_clears_draft(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='WillBeReset')
        self.client.post(reverse('characters:create'), {'step': 'basic', 'action': 'reset'})
        self.assertNotIn(WIZARD_SESSION_KEY, self.client.session)

    # ── skill boundaries ──

    def test_skill_value_clamped_above_100(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='HiSkill')
        self._post_stats()
        self.client.post(reverse('characters:create'), {
            'step': 'skills', 'action': 'next',
            f'skill_{self.skill_track.id}': 200,
            f'skill_{self.skill_brawl.id}': 25,
        })
        self._post_inventory(); self._post_save()
        c = Character.objects.get(name='HiSkill')
        self.assertTrue(CharacterSkill.objects.filter(character=c, skill=self.skill_track, value=100).exists())

    def test_skill_value_clamped_below_0(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='LoSkill')
        self._post_stats()
        self.client.post(reverse('characters:create'), {
            'step': 'skills', 'action': 'next',
            f'skill_{self.skill_track.id}': -50,
            f'skill_{self.skill_brawl.id}': 25,
        })
        self._post_inventory(); self._post_save()
        c = Character.objects.get(name='LoSkill')
        self.assertTrue(CharacterSkill.objects.filter(character=c, skill=self.skill_track, value=0).exists())

    # ── custom skills ──

    def test_custom_language_skill_persisted(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='Egyptologist')
        self._post_stats()
        self.client.post(reverse('characters:create'), {
            'step': 'skills', 'action': 'next',
            'custom_skills_json': json.dumps({
                '-1': {'name': 'Egyptian Hieroglyphs', 'category': 'language',
                       'base_value': 1, 'description': 'Custom skill: Egyptian Hieroglyphs'}
            }),
            f'skill_{self.skill_track.id}': 20,
            f'skill_{self.skill_brawl.id}': 25,
            'skill_-1': 55,
        })
        self._post_inventory(); self._post_save()
        c = Character.objects.get(name='Egyptologist')
        self.assertTrue(CharacterSkill.objects.filter(character=c, skill__name='Egyptian Hieroglyphs', value=55).exists())

    def test_custom_skill_isolation_between_characters(self):
        """After saving character A with a custom skill and resetting the wizard,
        the *session draft* has no custom skills for the next character.
        (The persisted Skill record is excluded server-side; this test verifies
        the draft isolation, i.e. no stale custom-skill keys in the new session.)
        """
        self.client.login(username='player', password='secret')
        self._post_basic(name='Char A')
        self._post_stats()
        self.client.post(reverse('characters:create'), {
            'step': 'skills', 'action': 'next',
            'custom_skills_json': json.dumps({
                '-1': {'name': 'UniqueXyzkSkillForTest', 'category': 'general', 'base_value': 1,
                       'description': 'Custom skill: UniqueXyzkSkillForTest'}
            }),
            f'skill_{self.skill_track.id}': 10,
            f'skill_{self.skill_brawl.id}': 25,
            'skill_-1': 20,
        })
        self._post_inventory()
        self._post_save()
        # Reset the wizard draft
        self.client.post(reverse('characters:create'), {'step': 'basic', 'action': 'reset'})
        # After reset, draft is gone from session
        self.assertNotIn(WIZARD_SESSION_KEY, self.client.session)
        # GET the skills step to bootstrap a fresh draft
        self.client.get(reverse('characters:create') + '?step=skills')
        # The new draft must not carry over any custom skills from Char A
        draft = self.client.session.get(WIZARD_SESSION_KEY, {})
        self.assertEqual(draft.get('custom_skills', {}), {})

    def test_custom_skill_can_be_renamed_before_save(self):
        self.client.login(username='player', password='secret')
        self._post_basic(name='Scholar of Dust')
        self._post_stats(strength=40, constitution=50, dexterity=60, intelligence=75,
                         power=55, size=50, appearance=45, education=80, luck=50)
        for name in ('Egiptian', 'Egyptian'):
            self.client.post(reverse('characters:create'), {
                'step': 'skills', 'action': 'next',
                'custom_skills_json': json.dumps({
                    '-1': {'name': name, 'category': 'language',
                           'base_value': 1, 'description': f'Custom skill: {name}'}
                }),
                f'skill_{self.skill_track.id}': 30, f'skill_{self.skill_brawl.id}': 40,
                'skill_-1': 20,
            })
        self._post_inventory(); self._post_save()
        c = Character.objects.get(name='Scholar of Dust')
        self.assertTrue(CharacterSkill.objects.filter(character=c, skill__name='Egyptian', value=20).exists())
        self.assertFalse(CharacterSkill.objects.filter(character=c, skill__name='Egiptian').exists())

    # ── item import display fix ──

    def test_imported_known_item_has_name_in_draft(self):
        self.client.login(username='player', password='secret')
        payload = {
            'character_info': {'name': 'Item Tester', 'occupation': '', 'age': ''},
            'characteristics': {'STR': 50, 'CON': 50, 'DEX': 50, 'INT': 50,
                                 'APP': 50, 'POW': 50, 'SIZ': 50, 'EDU': 50, 'Luck': 50},
            'skills': {}, 'weapons': [], 'inventory': ['Flashlight'],
        }
        uploaded = SimpleUploadedFile('t.json', json.dumps(payload).encode(), content_type='application/json')
        self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})
        draft = self.client.session[WIZARD_SESSION_KEY]
        items = draft['inventory']['items']
        self.assertTrue(items)
        name = items[0].get('name') or items[0].get('custom_name') or ''
        self.assertEqual(name, 'Flashlight')

    def test_imported_unknown_item_stored_as_custom(self):
        self.client.login(username='player', password='secret')
        payload = {
            'character_info': {'name': 'X', 'occupation': '', 'age': ''},
            'characteristics': {'STR': 50, 'CON': 50, 'DEX': 50, 'INT': 50,
                                 'APP': 50, 'POW': 50, 'SIZ': 50, 'EDU': 50, 'Luck': 50},
            'skills': {}, 'weapons': [], 'inventory': ['Ancient Tome'],
        }
        uploaded = SimpleUploadedFile('t.json', json.dumps(payload).encode(), content_type='application/json')
        self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})
        draft = self.client.session[WIZARD_SESSION_KEY]
        names = [i.get('name') or i.get('custom_name', '') for i in draft['inventory']['items']]
        self.assertIn('Ancient Tome', names)

    def test_imported_item_with_quantity_suffix_parsed(self):
        self.client.login(username='player', password='secret')
        payload = {
            'character_info': {'name': 'Qty Test', 'occupation': '', 'age': ''},
            'characteristics': {'STR': 50, 'CON': 50, 'DEX': 50, 'INT': 50,
                                 'APP': 50, 'POW': 50, 'SIZ': 50, 'EDU': 50, 'Luck': 50},
            'skills': {}, 'weapons': [], 'inventory': ['Rope x3'],
        }
        uploaded = SimpleUploadedFile('t.json', json.dumps(payload).encode(), content_type='application/json')
        self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})
        draft = self.client.session[WIZARD_SESSION_KEY]
        rope = next(
            (i for i in draft['inventory']['items']
             if (i.get('name') or i.get('custom_name', '')) == 'Rope'),
            None,
        )
        self.assertIsNotNone(rope)
        self.assertEqual(rope['quantity'], 3)


# ===========================================================================
# VI. IMPORT / EXPORT TESTS
# ===========================================================================

class CharacterImportExportTests(TestCase):

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='')
        Skill.objects.create(name='Own Language', category='language', base_value=0, description='')

    def test_export_returns_json_attachment(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:create_export_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_export_contains_required_keys(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:create'), {
            'step': 'basic', 'action': 'next', 'name': 'ExportHero', 'occupation': 'Sailor'})
        data = json.loads(self.client.get(reverse('characters:create_export_json')).content)
        for key in ('character_info', 'characteristics', 'skills'):
            self.assertIn(key, data)
        self.assertEqual(data['character_info']['name'], 'ExportHero')

    def test_import_invalid_json_shows_error(self):
        self.client.login(username='p', password='x')
        bad = SimpleUploadedFile('bad.json', b'not json', content_type='application/json')
        response = self.client.post(reverse('characters:create_import_json'), {'json_file': bad}, follow=True)
        self.assertContains(response, 'Invalid JSON file')

    def test_import_without_file_shows_error(self):
        self.client.login(username='p', password='x')
        response = self.client.post(reverse('characters:create_import_json'), {}, follow=True)
        self.assertContains(response, 'Please choose a JSON file')

    def test_export_then_import_roundtrip(self):
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:create'), {
            'step': 'basic', 'action': 'next', 'name': 'Roundtrip Hero'})
        payload = json.loads(self.client.get(reverse('characters:create_export_json')).content)
        self.client.post(reverse('characters:create'), {'step': 'basic', 'action': 'reset'})
        uploaded = SimpleUploadedFile('rt.json', json.dumps(payload).encode(), content_type='application/json')
        self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})
        self.assertContains(self.client.get(reverse('characters:create')), 'Roundtrip Hero')

    def test_import_ventwort_character(self):
        """Simulate importing docs/characters/ventwort_evbery.json payload."""
        self.client.login(username='p', password='x')
        Skill.objects.create(name='Library Use', category='general', base_value=20, description='')
        Skill.objects.create(name='Persuade', category='general', base_value=15, description='')
        payload = {
            'character_info': {
                'name': 'Вентворт Ейвбері', 'occupation': 'Професор лінгвістики', 'age': 58},
            'characteristics': {
                'STR': 50, 'CON': 60, 'DEX': 40, 'INT': 70,
                'APP': 50, 'POW': 60, 'SIZ': 50, 'EDU': 80, 'Luck': 60,
            },
            'skills': {'Library_Use': 60, 'Persuade': 60},
            'weapons': [],
            'inventory': ['Перова ручка й олівці', 'Блокнот'],
        }
        uploaded = SimpleUploadedFile('vent.json', json.dumps(payload).encode(), content_type='application/json')
        self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})
        draft = self.client.session[WIZARD_SESSION_KEY]
        self.assertEqual(draft['basic']['name'], 'Вентворт Ейвбері')
        self.assertEqual(draft['stats']['strength'], 50)
        self.assertEqual(draft['stats']['education'], 80)
        for item in draft['inventory']['items']:
            self.assertTrue(item.get('name') or item.get('custom_name'), f'Item missing name: {item}')

    def test_import_get_redirects_to_create(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:create_import_json'))
        self.assertRedirects(response, reverse('characters:create'))

    def test_export_get_from_edit_wizard(self):
        player = User.objects.create_user(username='p2', password='x', role='PLAYER')
        char = make_character(player, name='ExportChar')
        self.client.login(username='p2', password='x')
        response = self.client.get(reverse('characters:edit_wizard_export', args=[char.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])


# ===========================================================================
# VII. STATE TRANSITION TESTS
# ===========================================================================

class TemplateToCharacterStateTransitionTests(TestCase):
    """
    Full pipeline:
      Keeper creates template → Player loads template → Player saves character
      → Verify character fields match template values
    """

    def setUp(self):
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        Skill.objects.create(name='Own Language', category='language', base_value=0, description='')
        Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='')
        Skill.objects.create(name='Spot Hidden', category='general', base_value=25, description='')

    def _keeper_creates_template(self, name='Brave Scholar'):
        self.client.login(username='k', password='x')
        self.client.get(reverse('characters:template_create'))
        self.client.post(reverse('characters:create'), {
            'step': 'basic', 'action': 'next',
            'name': name, 'occupation': 'Professor', 'age': '50', 'description': 'Brave.',
        })
        self.client.post(reverse('characters:create'), {
            'step': 'stats', 'action': 'next',
            'strength': 40, 'constitution': 50, 'dexterity': 45, 'intelligence': 75,
            'power': 60, 'size': 50, 'appearance': 55, 'education': 80, 'luck': 55,
        })
        self.client.post(reverse('characters:create'), {
            'step': 'skills', 'action': 'next',
            f'skill_{Skill.objects.get(name="Spot Hidden").id}': 60,
            f'skill_{Skill.objects.get(name="Fighting (Brawl)").id}': 30,
        })
        self.client.post(reverse('characters:create'), {
            'step': 'inventory', 'action': 'next',
            'weapons_json': '[]', 'items_json': '[]',
        })
        self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        return CharacterTemplate.objects.get(name=name)

    def test_keeper_creates_template_stored_in_db(self):
        t = self._keeper_creates_template()
        self.assertIsNotNone(t)
        self.assertEqual(t.payload['character_info']['occupation'], 'Professor')

    def test_player_loads_template_populates_draft(self):
        t = self._keeper_creates_template()
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:use_template', args=[t.id]))
        draft = self.client.session[WIZARD_SESSION_KEY]
        self.assertEqual(draft['basic']['occupation'], 'Professor')
        self.assertEqual(draft['stats']['intelligence'], 75)

    def test_player_saves_character_from_template(self):
        t = self._keeper_creates_template()
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:use_template', args=[t.id]))
        self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        c = Character.objects.filter(owner=self.player, name='Brave Scholar').first()
        self.assertIsNotNone(c)
        self.assertEqual(c.intelligence, 75)
        self.assertEqual(c.education, 80)
        self.assertEqual(c.occupation, 'Professor')

    def test_template_not_deleted_after_player_uses_it(self):
        t = self._keeper_creates_template()
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:use_template', args=[t.id]))
        self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        self.assertTrue(CharacterTemplate.objects.filter(id=t.id).exists())

    def test_multiple_players_can_create_from_same_template(self):
        t = self._keeper_creates_template()
        player2 = User.objects.create_user(username='p2', password='x', role='PLAYER')
        for username in ('p', 'p2'):
            self.client.login(username=username, password='x')
            self.client.post(reverse('characters:use_template', args=[t.id]))
            self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        self.assertEqual(Character.objects.filter(name='Brave Scholar').count(), 2)

    def test_player_can_customise_after_loading_template(self):
        t = self._keeper_creates_template()
        self.client.login(username='p', password='x')
        self.client.post(reverse('characters:use_template', args=[t.id]))
        # Override name on basic step
        self.client.post(reverse('characters:create'), {
            'step': 'basic', 'action': 'next',
            'name': 'Personalised Scholar', 'occupation': 'Student', 'age': '22', 'description': '',
        })
        self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        self.assertTrue(Character.objects.filter(owner=self.player, name='Personalised Scholar').exists())
        self.assertFalse(Character.objects.filter(owner=self.player, name='Brave Scholar').exists())


class TemplateEditStateTransitionTests(TestCase):
    """Keeper edits an existing template via wizard and persists changes."""

    def setUp(self):
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='')
        self.template = CharacterTemplate.objects.create(
            name='Old Name',
            payload={
                'character_info': {'name': 'Old Name', 'occupation': 'Sailor', 'age': '30'},
                'characteristics': {'STR': 50, 'CON': 50, 'DEX': 50, 'INT': 50,
                                    'APP': 50, 'POW': 50, 'SIZ': 50, 'EDU': 50, 'Luck': 50},
                'skills': {},
                'weapons': [],
                'description': 'Old description.',
                'inventory': [],
            },
        )

    def test_keeper_edit_updates_template_name_and_payload(self):
        self.client.login(username='k', password='x')
        self.client.get(reverse('characters:template_edit', args=[self.template.id]))
        self.client.post(reverse('characters:create'), {
            'step': 'basic', 'action': 'next',
            'name': 'New Name', 'occupation': 'Pilot', 'age': '40', 'description': 'New desc.',
        })
        self.client.post(reverse('characters:create'), {
            'step': 'stats', 'action': 'next',
            'strength': 60, 'constitution': 60, 'dexterity': 50, 'intelligence': 60,
            'power': 55, 'size': 55, 'appearance': 50, 'education': 70, 'luck': 50,
        })
        brawl = Skill.objects.get(name='Fighting (Brawl)')
        self.client.post(reverse('characters:create'), {
            'step': 'skills', 'action': 'next', f'skill_{brawl.id}': 30,
        })
        self.client.post(reverse('characters:create'), {
            'step': 'inventory', 'action': 'next', 'weapons_json': '[]', 'items_json': '[]',
        })
        self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        self.template.refresh_from_db()
        self.assertEqual(self.template.name, 'New Name')
        self.assertEqual(self.template.payload['character_info']['occupation'], 'Pilot')

    def test_edit_does_not_create_duplicate_template(self):
        count_before = CharacterTemplate.objects.count()
        self.client.login(username='k', password='x')
        self.client.get(reverse('characters:template_edit', args=[self.template.id]))
        brawl = Skill.objects.get(name='Fighting (Brawl)')
        for step, data in [
            ('basic', {'name': 'Edited', 'occupation': 'Cook', 'age': '', 'description': ''}),
            ('stats', {'strength': 50, 'constitution': 50, 'dexterity': 50, 'intelligence': 50,
                       'power': 50, 'size': 50, 'appearance': 50, 'education': 50, 'luck': 50}),
            ('skills', {f'skill_{brawl.id}': 25}),
            ('inventory', {'weapons_json': '[]', 'items_json': '[]'}),
        ]:
            self.client.post(reverse('characters:create'), {'step': step, 'action': 'next', **data})
        self.client.post(reverse('characters:create'), {'step': 'review', 'action': 'save'})
        self.assertEqual(CharacterTemplate.objects.count(), count_before)


class CharacterEditWizardStateTransitionTests(TestCase):
    """Create character → edit via wizard → verify changes and changelog."""

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        self.keeper = User.objects.create_user(username='k', password='x', role='KEEPER')
        self.skill_brawl = Skill.objects.create(
            name='Fighting (Brawl)', category='combat', base_value=25, description='')
        self.char = make_character(
            self.player, name='Original Name', occupation='Soldier',
            strength=50, constitution=50, dexterity=50, intelligence=50,
            power=50, size=50, appearance=50, education=50,
        )

    def _edit_url(self):
        return reverse('characters:edit_wizard', args=[self.char.id])

    def _run_edit(self, name, occupation, strength):
        self.client.post(self._edit_url(), {
            'step': 'basic', 'action': 'next',
            'name': name, 'occupation': occupation, 'description': '', 'age': '',
        })
        self.client.post(self._edit_url(), {
            'step': 'stats', 'action': 'next',
            'strength': strength, 'constitution': 50, 'dexterity': 50, 'intelligence': 50,
            'power': 50, 'size': 50, 'appearance': 50, 'education': 50, 'luck': 50,
        })
        self.client.post(self._edit_url(), {
            'step': 'skills', 'action': 'next',
            f'skill_{self.skill_brawl.id}': 25,
        })
        self.client.post(self._edit_url(), {
            'step': 'inventory', 'action': 'next', 'weapons_json': '[]', 'items_json': '[]',
        })
        return self.client.post(self._edit_url(), {'step': 'review', 'action': 'save'})

    def test_owner_can_edit_character(self):
        self.client.login(username='p', password='x')
        response = self._run_edit('Updated Name', 'Artist', 70)
        self.assertRedirects(response, reverse('characters:detail', args=[self.char.id]))
        self.char.refresh_from_db()
        self.assertEqual(self.char.name, 'Updated Name')
        self.assertEqual(self.char.occupation, 'Artist')
        self.assertEqual(self.char.strength, 70)

    def test_non_owner_non_keeper_blocked(self):
        other = User.objects.create_user(username='o', password='x', role='PLAYER')
        self.client.login(username='o', password='x')
        response = self.client.get(self._edit_url())
        self.assertEqual(response.status_code, 302)

    def test_keeper_can_edit_any_character(self):
        self.client.login(username='k', password='x')
        self._run_edit('KeeperEdited', 'Wizard', 65)
        self.char.refresh_from_db()
        self.assertEqual(self.char.name, 'KeeperEdited')

    def test_changelog_entry_created_on_change(self):
        self.client.login(username='p', password='x')
        self._run_edit('Changed', 'Painter', 55)
        self.assertTrue(CharacterChangeLog.objects.filter(character=self.char).exists())

    def test_no_changelog_when_nothing_changed(self):
        # Pre-populate every skill the wizard computes so the diff sees 0 changes.
        own_lang = Skill.objects.create(
            name='Own Language', category='language', base_value=0, description='Native.')
        track = Skill.objects.create(
            name='Track', category='general', base_value=10, description='Track.')
        CharacterSkill.objects.create(character=self.char, skill=self.skill_brawl, value=25)
        CharacterSkill.objects.create(character=self.char, skill=own_lang, value=50)  # EDU=50
        CharacterSkill.objects.create(character=self.char, skill=track, value=10)
        unarmed, _ = Weapon.objects.get_or_create(
            name=DEFAULT_UNARMED_WEAPON_NAME,
            defaults={'skill_name': 'Fighting (Brawl)', 'damage': DEFAULT_UNARMED_WEAPON_DAMAGE},
        )
        CharacterWeapon.objects.create(
            character=self.char, weapon=unarmed, skill_value=25, is_prepared=False)
        self.client.login(username='p', password='x')
        # Edit with values identical to current state → no log entry expected.
        self._run_edit('Original Name', 'Soldier', 50)
        self.assertFalse(CharacterChangeLog.objects.filter(character=self.char).exists())

    def test_reset_clears_edit_draft(self):
        self.client.login(username='p', password='x')
        self.client.post(self._edit_url(), {
            'step': 'basic', 'action': 'next', 'name': 'Temp', 'occupation': '', 'description': '', 'age': '',
        })
        self.client.post(self._edit_url(), {'action': 'reset', 'step': 'basic'})
        from characters.views import _edit_session_key
        self.assertNotIn(_edit_session_key(self.char.id), self.client.session)

    def test_stat_boundary_100_after_edit(self):
        self.client.login(username='p', password='x')
        self._run_edit('MaxStr', 'Soldier', 100)
        self.char.refresh_from_db()
        self.assertEqual(self.char.strength, 100)

    def test_stat_boundary_0_after_edit(self):
        self.client.login(username='p', password='x')
        self._run_edit('MinStr', 'Soldier', 0)
        self.char.refresh_from_db()
        self.assertEqual(self.char.strength, 0)


class CharacterEditWizardImportExportTests(TestCase):
    """Edit-wizard import / export sub-views."""

    def setUp(self):
        self.player = User.objects.create_user(username='p', password='x', role='PLAYER')
        Skill.objects.create(name='Fighting (Brawl)', category='combat', base_value=25, description='')
        self.char = make_character(self.player, name='Export Me')

    def test_export_returns_json(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:edit_wizard_export', args=[self.char.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response['Content-Type'])

    def test_import_updates_edit_draft(self):
        self.client.login(username='p', password='x')
        payload = {
            'character_info': {'name': 'Import Replacement', 'occupation': 'Cook', 'age': '25'},
            'characteristics': {'STR': 55, 'CON': 55, 'DEX': 55, 'INT': 55,
                                 'APP': 55, 'POW': 55, 'SIZ': 55, 'EDU': 55, 'Luck': 55},
            'skills': {}, 'weapons': [], 'inventory': [],
        }
        uploaded = SimpleUploadedFile('imp.json', json.dumps(payload).encode(), content_type='application/json')
        self.client.post(reverse('characters:edit_wizard_import', args=[self.char.id]), {'json_file': uploaded})
        from characters.views import _edit_session_key
        draft = self.client.session[_edit_session_key(self.char.id)]
        self.assertEqual(draft['basic']['name'], 'Import Replacement')

    def test_import_invalid_json_shows_error(self):
        self.client.login(username='p', password='x')
        bad = SimpleUploadedFile('bad.json', b'{bad}', content_type='application/json')
        response = self.client.post(
            reverse('characters:edit_wizard_import', args=[self.char.id]),
            {'json_file': bad}, follow=True,
        )
        self.assertContains(response, 'Invalid JSON file')

    def test_import_get_redirects(self):
        self.client.login(username='p', password='x')
        response = self.client.get(reverse('characters:edit_wizard_import', args=[self.char.id]))
        self.assertRedirects(response, reverse('characters:edit_wizard', args=[self.char.id]))








