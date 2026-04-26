import json

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from characters.models import (
	Character,
	CharacterItem,
	CharacterSkill,
	CharacterWeapon,
	Item,
	Skill,
	Weapon,
)
from characters.views import DEFAULT_UNARMED_WEAPON_NAME


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

		self.client.login(username='keeper', password='secret')
		response = self.client.get(reverse('characters:create'))
		self.assertEqual(response.status_code, 200)

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
		self.assertEqual(payload['basic']['name'], 'Imported Hero')

		self.client.post(reverse('characters:create'), {'step': 'basic', 'action': 'reset'})

		uploaded = SimpleUploadedFile(
			'character_draft.json',
			json.dumps(payload).encode('utf-8'),
			content_type='application/json',
		)
		self.client.post(reverse('characters:create_import_json'), {'json_file': uploaded})

		response = self.client.get(reverse('characters:create'))
		self.assertContains(response, 'Imported Hero')
