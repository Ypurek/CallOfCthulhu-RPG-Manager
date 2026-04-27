import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from characters.models import (
	Character,
	CharacterItem,
	CharacterSkill,
	CharacterTemplate,
	CharacterWeapon,
	Item,
	Skill,
	Weapon,
)
from characters.views import DEFAULT_UNARMED_WEAPON_NAME, WIZARD_SESSION_KEY


class CharacterCreateWizardTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.player = user_model.objects.create_user(username='player', password='secret', role='PLAYER')
		self.keeper = user_model.objects.create_user(username='keeper', password='secret', role='KEEPER')

		self.skill_own_language = Skill.objects.create(
			name='Own Language',
			category='language',
			base_value=0,
			description='Native language skill.',
		)
		self.skill_track = Skill.objects.create(
			name='Track',
			category='general',
			base_value=10,
			description='Track people and creatures.',
		)
		self.skill_brawl = Skill.objects.create(
			name='Fighting (Brawl)',
			category='combat',
			base_value=25,
			description='Close combat without a weapon.',
		)

		self.weapon = Weapon.objects.create(name='Knife', skill_name='Fighting (Brawl)', damage='1D4')
		self.item = Item.objects.create(name='Flashlight', description='Useful light source.')

	def test_create_page_access_for_player_and_keeper(self):
		self.client.login(username='player', password='secret')
		response = self.client.get(reverse('characters:create'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'id="import-json-trigger"', html=False)

		self.client.login(username='keeper', password='secret')
		response = self.client.get(reverse('characters:create'))
		self.assertEqual(response.status_code, 200)

	def test_stats_step_contains_clickable_stat_descriptions(self):
		self.client.login(username='player', password='secret')
		response = self.client.get(reverse('characters:create') + '?step=stats')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'showWizardStatModal(\'STR\'', html=False)
		self.assertContains(response, 'id="wizardStatModal"', html=False)

	def test_wizard_creates_character_with_relations(self):
		self.client.login(username='player', password='secret')

		self.client.post(reverse('characters:create'), {
			'step': 'basic',
			'action': 'next',
			'name': 'Investigator',
			'description': 'Ready for eldritch mysteries.',
			'occupation': 'Journalist',
		})

		self.client.post(reverse('characters:create'), {
			'step': 'stats',
			'action': 'next',
			'strength': 60,
			'constitution': 55,
			'dexterity': 50,
			'intelligence': 70,
			'power': 65,
			'size': 45,
			'appearance': 40,
			'education': 80,
			'luck': 50,
		})

		self.client.post(reverse('characters:create'), {
			'step': 'skills',
			'action': 'next',
			f'skill_{self.skill_track.id}': 45,
			f'skill_{self.skill_brawl.id}': 60,
		})

		self.client.post(reverse('characters:create'), {
			'step': 'inventory',
			'action': 'next',
			'weapons_json': json.dumps([
				{
					'weapon_id': self.weapon.id,
					'name': self.weapon.name,
					'skill_id': self.skill_brawl.id,
					'skill_name': self.skill_brawl.name,
					'is_prepared': True,
					'damage': '1D4',
				}
			]),
			'items_json': json.dumps([
				{
					'item_id': self.item.id,
					'quantity': 2,
				}
			]),
		})

		response = self.client.post(reverse('characters:create'), {
			'step': 'review',
			'action': 'save',
		})

		self.assertEqual(response.status_code, 302)
		character = Character.objects.get(name='Investigator')
		self.assertEqual(character.owner, self.player)
		self.assertTrue(CharacterSkill.objects.filter(character=character, skill=self.skill_track, value=45).exists())
		self.assertTrue(CharacterSkill.objects.filter(character=character, skill=self.skill_own_language, value=80).exists())
		self.assertTrue(CharacterSkill.objects.filter(character=character, skill=self.skill_brawl, value=60).exists())
		self.assertTrue(CharacterWeapon.objects.filter(character=character, weapon__name=self.weapon.name, is_prepared=True, skill_value=60).exists())
		self.assertTrue(CharacterWeapon.objects.filter(character=character, weapon__name=DEFAULT_UNARMED_WEAPON_NAME, skill_value=60).exists())
		self.assertTrue(CharacterItem.objects.filter(character=character, item=self.item, quantity=2).exists())
		self.assertEqual(character.hp_max, 11)
		self.assertEqual(character.mp_max, 13)

	def test_default_unarmed_weapon_is_added_even_if_not_posted(self):
		self.client.login(username='player', password='secret')

		self.client.post(reverse('characters:create'), {
			'step': 'basic',
			'action': 'next',
			'name': 'Bare Hands',
			'occupation': 'Boxer',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'stats',
			'action': 'next',
			'strength': 50,
			'constitution': 50,
			'dexterity': 50,
			'intelligence': 50,
			'power': 50,
			'size': 50,
			'appearance': 50,
			'education': 50,
			'luck': 50,
		})
		self.client.post(reverse('characters:create'), {
			'step': 'skills',
			'action': 'next',
			f'skill_{self.skill_track.id}': 10,
			f'skill_{self.skill_brawl.id}': 55,
		})
		self.client.post(reverse('characters:create'), {
			'step': 'inventory',
			'action': 'next',
			'weapons_json': '[]',
			'items_json': '[]',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'review',
			'action': 'save',
		})

		character = Character.objects.get(name='Bare Hands')
		self.assertTrue(CharacterWeapon.objects.filter(character=character, weapon__name=DEFAULT_UNARMED_WEAPON_NAME, skill_value=55).exists())

	def test_export_then_import_restores_draft(self):
		self.client.login(username='player', password='secret')
		self.client.post(reverse('characters:create'), {
			'step': 'basic',
			'action': 'next',
			'name': 'Imported Hero',
			'description': 'Roundtrip test.',
		})

		export_response = self.client.get(reverse('characters:create_export_json'))
		self.assertEqual(export_response.status_code, 200)
		self.assertEqual(export_response['Content-Type'], 'application/json')

		payload = json.loads(export_response.content.decode('utf-8'))
		self.assertEqual(payload['character_info']['name'], 'Imported Hero')

		self.client.post(reverse('characters:create'), {'step': 'basic', 'action': 'reset'})

		uploaded = SimpleUploadedFile(
			'character_draft.json',
			json.dumps(payload).encode('utf-8'),
			content_type='application/json',
		)
		self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})

		response = self.client.get(reverse('characters:create'))
		self.assertContains(response, 'Imported Hero')

	def test_imported_custom_language_skill_is_editable_and_persisted(self):
		self.client.login(username='player', password='secret')

		payload = {
			'character_info': {
				'name': 'Egyptologist',
				'occupation': 'Scholar',
				'age': 33,
			},
			'characteristics': {
				'STR': 40,
				'CON': 50,
				'DEX': 60,
				'INT': 70,
				'APP': 55,
				'POW': 65,
				'SIZ': 45,
				'EDU': 80,
				'Luck': 35,
			},
			'skills': {
				'Language_Egyptian_Hieroglyphs': 50,
				'Track': 25,
			},
		}

		uploaded = SimpleUploadedFile(
			'egyptologist.json',
			json.dumps(payload).encode('utf-8'),
			content_type='application/json',
		)
		self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})

		response = self.client.get(reverse('characters:create') + '?step=skills')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Egyptian Hieroglyphs')
		self.assertNotContains(response, 'for="skill_Dodge"', html=False)

		session = self.client.session
		custom_skills = session[WIZARD_SESSION_KEY]['custom_skills']
		custom_skill_id = next(iter(custom_skills.keys()))
		self.assertEqual(custom_skills[custom_skill_id]['category'], 'language')

		self.client.post(reverse('characters:create'), {
			'step': 'skills',
			'action': 'next',
			'custom_skills_json': json.dumps(custom_skills),
			f'skill_{self.skill_track.id}': 35,
			f'skill_{self.skill_brawl.id}': 45,
			f'skill_{custom_skill_id}': 65,
		})
		self.client.post(reverse('characters:create'), {
			'step': 'inventory',
			'action': 'next',
			'weapons_json': '[]',
			'items_json': '[]',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'review',
			'action': 'save',
		})

		character = Character.objects.get(name='Egyptologist')
		egyptian_skill = Skill.objects.get(name='Egyptian Hieroglyphs')
		self.assertEqual(egyptian_skill.category, 'language')
		self.assertTrue(CharacterSkill.objects.filter(character=character, skill=egyptian_skill, value=65).exists())

		response = self.client.get(reverse('characters:edit_wizard', args=[character.id]) + '?step=skills')
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Egyptian Hieroglyphs')

	def test_custom_skill_added_to_one_character_does_not_show_by_default_for_another(self):
		self.client.login(username='player', password='secret')

		self.client.post(reverse('characters:create'), {
			'step': 'basic',
			'action': 'next',
			'name': 'First Investigator',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'stats',
			'action': 'next',
			'strength': 40,
			'constitution': 50,
			'dexterity': 60,
			'intelligence': 70,
			'power': 50,
			'size': 50,
			'appearance': 50,
			'education': 70,
			'luck': 40,
		})
		self.client.post(reverse('characters:create'), {
			'step': 'skills',
			'action': 'next',
			'custom_skills_json': json.dumps({
				'-1': {
					'name': 'Egyptian Hieroglyphs',
					'category': 'language',
					'base_value': 1,
					'description': 'Custom skill: Egyptian Hieroglyphs',
				}
			}),
			f'skill_{self.skill_track.id}': 25,
			f'skill_{self.skill_brawl.id}': 45,
			'skill_-1': 20,
		})
		self.client.post(reverse('characters:create'), {
			'step': 'inventory',
			'action': 'next',
			'weapons_json': '[]',
			'items_json': '[]',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'review',
			'action': 'save',
		})

		self.client.post(reverse('characters:create'), {'step': 'basic', 'action': 'reset'})
		response = self.client.get(reverse('characters:create') + '?step=skills')
		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, 'Egyptian Hieroglyphs')

	def test_custom_skill_can_be_renamed_before_save(self):
		self.client.login(username='player', password='secret')

		self.client.post(reverse('characters:create'), {
			'step': 'basic',
			'action': 'next',
			'name': 'Scholar of Dust',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'stats',
			'action': 'next',
			'strength': 40,
			'constitution': 50,
			'dexterity': 60,
			'intelligence': 75,
			'power': 55,
			'size': 50,
			'appearance': 45,
			'education': 80,
			'luck': 50,
		})

		initial_custom_skills = {
			'-1': {
				'name': 'Egiptian',
				'category': 'language',
				'base_value': 1,
				'description': 'Custom skill: Egiptian',
			}
		}
		self.client.post(reverse('characters:create'), {
			'step': 'skills',
			'action': 'next',
			'custom_skills_json': json.dumps(initial_custom_skills),
			f'skill_{self.skill_track.id}': 30,
			f'skill_{self.skill_brawl.id}': 40,
			'skill_-1': 20,
		})

		renamed_custom_skills = {
			'-1': {
				'name': 'Egyptian',
				'category': 'language',
				'base_value': 1,
				'description': 'Custom skill: Egyptian',
			}
		}
		self.client.post(reverse('characters:create'), {
			'step': 'skills',
			'action': 'next',
			'custom_skills_json': json.dumps(renamed_custom_skills),
			f'skill_{self.skill_track.id}': 30,
			f'skill_{self.skill_brawl.id}': 40,
			'skill_-1': 20,
		})
		self.client.post(reverse('characters:create'), {
			'step': 'inventory',
			'action': 'next',
			'weapons_json': '[]',
			'items_json': '[]',
		})
		self.client.post(reverse('characters:create'), {
			'step': 'review',
			'action': 'save',
		})

		character = Character.objects.get(name='Scholar of Dust')
		self.assertTrue(CharacterSkill.objects.filter(character=character, skill__name='Egyptian', value=20).exists())
		self.assertFalse(CharacterSkill.objects.filter(character=character, skill__name='Egiptian').exists())

	def test_character_can_be_deleted_via_confirmed_post(self):
		self.client.login(username='player', password='secret')
		character = Character.objects.create(
			owner=self.player,
			character_type='PC',
			is_alive=True,
			name='Doomed Investigator',
			strength=50,
			constitution=50,
			dexterity=50,
			intelligence=50,
			power=50,
			size=50,
			appearance=50,
			education=50,
			hp_current=10,
			hp_max=10,
			mp_current=10,
			mp_max=10,
			sanity_current=50,
			sanity_max=50,
			sanity_start=50,
			luck=50,
			movement=8,
			build=0,
			damage_bonus='0',
			cash=0,
		)

		response = self.client.post(reverse('characters:delete', args=[character.id]))
		self.assertRedirects(response, reverse('characters:list'))
		self.assertFalse(Character.objects.filter(id=character.id).exists())


class CharacterTemplateDeleteTests(TestCase):
	def setUp(self):
		user_model = get_user_model()
		self.player = user_model.objects.create_user(username='tpl_player', password='secret', role='PLAYER')
		self.keeper = user_model.objects.create_user(username='tpl_keeper', password='secret', role='KEEPER')
		self.admin = user_model.objects.create_user(
			username='tpl_admin',
			password='secret',
			role='KEEPER',
			is_superuser=True,
			is_staff=True,
		)
		self.template = CharacterTemplate.objects.create(
			name='Test Template',
			payload={'character_info': {'name': 'Temp Name'}, 'characteristics': {}, 'skills': {}},
		)

	def test_keeper_can_delete_template(self):
		self.client.login(username='tpl_keeper', password='secret')
		response = self.client.post(reverse('characters:template_delete', args=[self.template.id]))

		self.assertRedirects(response, reverse('characters:templates'))
		self.assertFalse(CharacterTemplate.objects.filter(id=self.template.id).exists())

	def test_admin_can_delete_template(self):
		self.client.login(username='tpl_admin', password='secret')
		response = self.client.post(reverse('characters:template_delete', args=[self.template.id]))

		self.assertRedirects(response, reverse('characters:templates'))
		self.assertFalse(CharacterTemplate.objects.filter(id=self.template.id).exists())

	def test_player_cannot_delete_template(self):
		self.client.login(username='tpl_player', password='secret')
		response = self.client.post(reverse('characters:template_delete', args=[self.template.id]))

		self.assertRedirects(response, reverse('characters:templates'))
		self.assertTrue(CharacterTemplate.objects.filter(id=self.template.id).exists())

	def test_get_request_does_not_delete_template(self):
		self.client.login(username='tpl_keeper', password='secret')
		response = self.client.get(reverse('characters:template_delete', args=[self.template.id]))

		self.assertRedirects(response, reverse('characters:templates'))
		self.assertTrue(CharacterTemplate.objects.filter(id=self.template.id).exists())


