from django.test import TestCase
from django.conf import settings
from sis_provisioner.policy import UserPolicy, UserPolicyException


class NetidPolicyTest(TestCase):
    def test_valid_netid(self):
        policy = UserPolicy()

        # Valid
        self.assertEquals(policy.valid_net_id('javerage'), None)
        self.assertEquals(policy.valid_net_id('sadm_javerage'), None)
        self.assertEquals(policy.valid_net_id('a_canvas_application'), None)
        self.assertEquals(policy.valid_net_id('j1234567890'), None)

        # Invalid
        self.assertRaises(UserPolicyException, policy.valid_net_id, None)
        self.assertRaises(UserPolicyException, policy.valid_net_id, '')
        self.assertRaises(UserPolicyException, policy.valid_net_id, 'wire1234')
        self.assertRaises(UserPolicyException, policy.valid_net_id, 'event1234')
        self.assertRaises(UserPolicyException, policy.valid_net_id, 'lib1234')
        self.assertRaises(UserPolicyException, policy.valid_net_id, 'css1234')
        self.assertRaises(UserPolicyException, policy.valid_net_id, '1abcdef')
        self.assertRaises(UserPolicyException, policy.valid_net_id, 'j123456789012345')

    def test_valid_admin_netid(self):
        policy = UserPolicy()

        # Valid
        self.assertEquals(policy.valid_admin_net_id('sadm_javerage'), None)
        self.assertEquals(policy.valid_admin_net_id('wadm_javerage'), None)

        # Invalid
        self.assertRaises(UserPolicyException, policy.valid_admin_net_id, 'javerage')

    def test_valid_application_netid(self):
        policy = UserPolicy()

        # Valid
        self.assertEquals(policy.valid_application_net_id('a_canvas_application'), None)

        # Invalid
        self.assertRaises(UserPolicyException, policy.valid_application_net_id, 'javerage')

    def test_nonpersonal_netid(self):
        with self.settings(
                NONPERSONAL_NETID_EXCEPTION_GROUP='u_acadev_unittest',
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File'):
            policy = UserPolicy()

            # Valid
            self.assertEquals(policy.valid_nonpersonal_net_id('a_canvas_application'), None)
            self.assertEquals(policy.valid_nonpersonal_net_id('wadm_javerage'), None)
            self.assertEquals(policy.valid_nonpersonal_net_id('javerage'), None)

            # Invalid
            self.assertRaises(UserPolicyException, policy.valid_nonpersonal_net_id, 'canvas')


class RegidPolicyTest(TestCase):
    def test_valid_regid(self):
        policy = UserPolicy()

        # Valid
        self.assertEquals(policy.valid_reg_id('9136CCB8F66711D5BE060004AC494FFE'), None)

        # Invalid
        self.assertRaises(UserPolicyException, policy.valid_reg_id, '9136CCB8F66711D5BE060004AC494FF')
        self.assertRaises(UserPolicyException, policy.valid_reg_id, '9136CCB8F66711D5BE060004AC494FFEE')
        self.assertRaises(UserPolicyException, policy.valid_reg_id, 'javerage')


class GmailPolicyTest(TestCase):
    valid_domains = ['gmail.com', 'google.com', 'googlemail.com']

    def test_valid_domains(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

            default_user = "johnsmith"

            invalid_domains = [
                "abc.com"
                "",
            ]

            policy = UserPolicy()

            for domain in self.valid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertEquals(policy.valid_gmail_id(user), user, "Valid user: %s" % user)

            for domain in invalid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertRaises(UserPolicyException, policy.valid_gmail_id, user)

    def test_valid_user(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

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
