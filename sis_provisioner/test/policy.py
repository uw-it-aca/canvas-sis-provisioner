from django.test import TestCase
from django.conf import settings
from sis_provisioner.policy import UserPolicy, UserPolicyException


valid_domains = ['gmail.com', 'google.com', 'googlemail.com']


class GmailPolicyTest(TestCase):
    def test_valid_domains(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=valid_domains):

            default_user = "johnsmith"

            invalid_domains = [
                "abc.com"
                "",
            ]

            policy = UserPolicy()

            for domain in valid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertEquals(policy.valid_gmail_id(user), user, "Valid user: %s" % user)

            for domain in invalid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)

    def test_valid_user(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=valid_domains):

            default_user = "johnsmith@gmail.com"

            valid_users = [
                "JohnSmith@gmail.com",
                "johnsmith@GMail.com",
                "john.smith@gmail.com",
                "john.smith+canvas@gmail.com",
                "john.smith+abc+canvas+@gmail.com",
                ".john.smith@gmail.com",
            ]

            invalid_users = [
                "john@smith@gmail.com",
                "+johnsmith@gmail.com",
                "+@gmail.com",
                ".@gmail.com",
                "@gmail.com",
            ]

            policy = UserPolicy()

            self.assertEquals(policy.valid_gmail_id(default_user), default_user, "Default user is not changed")

            for user in valid_users:
                self.assertEquals(policy.valid_gmail_id(user), default_user, "Valid user: %s" % user)

            for user in invalid_users:
                self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)

        with self.settings(LOGIN_DOMAIN_WHITELIST = []):
            policy = UserPolicy()
            self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)
