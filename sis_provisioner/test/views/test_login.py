from django.test import TestCase, override_settings
from sis_provisioner.views.login import LoginValidationView


class LoginViewTest(TestCase):
    @override_settings(ADD_USER_DOMAIN_WHITELIST=['test.edu', 'test.old.edu'])
    def test_strip_domain(self):
        self.assertEqual(
            LoginValidationView.strip_domain('javerage'), 'javerage')
        self.assertEqual(
            LoginValidationView.strip_domain('javerage@test.edu'), 'javerage')
        self.assertEqual(
            LoginValidationView.strip_domain('javerage@test.old.edu'),
            'javerage')
        self.assertEqual(
            LoginValidationView.strip_domain('javerage@test.com'),
            'javerage@test.com')
