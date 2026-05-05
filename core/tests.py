from django.test import TestCase
from django.urls import reverse

from core.models import User


class UserModelTest(TestCase):
    def setUp(self):
        self.player = User.objects.create_user(username='player', password='pass', role=User.Role.PLAYER)
        self.keeper = User.objects.create_user(username='keeper', password='pass', role=User.Role.KEEPER)

    def test_default_role_is_player(self):
        user = User.objects.create_user(username='newuser', password='pass')
        self.assertEqual(user.role, User.Role.PLAYER)

    def test_is_player(self):
        self.assertTrue(self.player.is_player())
        self.assertFalse(self.player.is_keeper())

    def test_is_keeper(self):
        self.assertTrue(self.keeper.is_keeper())
        self.assertFalse(self.keeper.is_player())


class AuthViewsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')

    def test_home_view(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)

    def test_login_view_get(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'testpass123'})
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_failure(self):
        response = self.client.post(reverse('login'), {'username': 'testuser', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)

    def test_register_view_get(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_player(self):
        response = self.client.post(reverse('register'), {
            'username': 'newplayer',
            'password1': 'complexpass123!',
            'password2': 'complexpass123!',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newplayer')
        self.assertEqual(user.role, User.Role.PLAYER)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_dashboard_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('profile'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('profile')}")

    def test_profile_page_accessible_when_logged_in(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')

    def test_profile_password_change_success(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile'), {
            'old_password': 'testpass123',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        self.assertRedirects(response, reverse('profile'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass456'))

    def test_profile_password_change_keeps_session_active(self):
        self.client.login(username='testuser', password='testpass123')
        self.client.post(reverse('profile'), {
            'old_password': 'testpass123',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_profile_password_change_rejects_wrong_old_password(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('profile'), {
            'old_password': 'wrongpass',
            'new_password1': 'newpass456',
            'new_password2': 'newpass456',
        })
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('testpass123'))

    def test_authenticated_nav_shows_profile_and_hides_settings(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, reverse('profile'))
        self.assertNotContains(response, '>Settings<')

    def test_logout(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
