from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class IndexViewTests(TestCase):
    def test_anonymous_user_sees_login_entry_point(self):
        response = self.client.get(reverse('index'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sistema ERP')
        self.assertContains(response, reverse('login'))
        self.assertNotContains(response, 'index.html')
        self.assertNotContains(response, 'portfolio-details.html')
        self.assertNotContains(response, 'forms/contact.php')

    def test_authenticated_user_is_redirected_to_dashboard(self):
        user = get_user_model().objects.create_user(
            username='index_user',
            password='secret123',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('index'))

        self.assertRedirects(response, reverse('erp:dashboard'), fetch_redirect_response=False)
