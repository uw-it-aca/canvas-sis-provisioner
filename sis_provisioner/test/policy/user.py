from django.test import TestCase
from sis_provisioner.dao.user import *
from sis_provisioner.exceptions import UserPolicyException,\
    MissingLoginIdException, InvalidLoginIdException,\
    TemporaryNetidException


class UserPolicyTest(TestCase):
    def test_valid_canvas_user_id(self):
        self.assertEquals(valid_canvas_user_id(12345), None)
        self.assertEquals(valid_canvas_user_id('12345'), None)
        self.assertEquals(valid_canvas_user_id(0), None)
        self.assertEquals(valid_canvas_user_id(1111111111), None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, 'abc')
        self.assertRaises(UserPolicyException, valid_canvas_user_id, '1234z')

    def test_user_email(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = get_person_by_netid('javerage')
            self.assertEquals(user_email(user), 'javerage@uw.edu')

            user = get_person_by_gmail_id('john.smith@gmail.com')
            self.assertEquals(user_email(user), 'john.smith@gmail.com')

    def test_user_fullname(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = get_person_by_netid('javerage')
            user.display_name = None
            self.assertEquals(user_fullname(user), 'James Student')

            user.display_name = 'Johnny S'
            self.assertEquals(user_fullname(user), user.display_name)

            user = get_person_by_gmail_id('john.smith@gmail.com')
            self.assertEquals(user_fullname(user), 'john.smith')

class NetidPolicyTest(TestCase):
    def test_get_person_by_netid(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            self.assertEquals(get_person_by_netid('javerage').uwnetid, 'javerage')

    def test_valid_netid(self):
        # Valid
        self.assertEquals(valid_net_id('javerage'), None)
        self.assertEquals(valid_net_id('sadm_javerage'), None)
        self.assertEquals(valid_net_id('a_canvas_application'), None)
        self.assertEquals(valid_net_id('j1234567890'), None)

        # Invalid
        self.assertRaises(MissingLoginIdException, valid_net_id, None)
        self.assertRaises(MissingLoginIdException, valid_net_id, '')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'wire1234')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'event1234')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'lib1234')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'css1234')
        self.assertRaises(InvalidLoginIdException, valid_net_id, '1abcdef')
        self.assertRaises(InvalidLoginIdException, valid_net_id, 'j123456789012345')
        self.assertRaises(UserPolicyException, valid_net_id, 'j123456789012345')

    def test_valid_admin_netid(self):
        # Valid
        self.assertEquals(valid_admin_net_id('sadm_javerage'), None)
        self.assertEquals(valid_admin_net_id('wadm_javerage'), None)

        # Invalid
        self.assertRaises(InvalidLoginIdException, valid_admin_net_id, 'javerage')

    def test_valid_application_netid(self):
        # Valid
        self.assertEquals(valid_application_net_id('a_canvas_application'), None)

        # Invalid
        self.assertRaises(UserPolicyException, valid_application_net_id, 'javerage')

    def test_nonpersonal_netid(self):
        with self.settings(
                NONPERSONAL_NETID_EXCEPTION_GROUP='u_acadev_unittest',
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File'):

            # Valid
            self.assertEquals(valid_nonpersonal_net_id('a_canvas_application'), None)
            self.assertEquals(valid_nonpersonal_net_id('wadm_javerage'), None)
            self.assertEquals(valid_nonpersonal_net_id('javerage'), None)

            # Invalid
            self.assertRaises(InvalidLoginIdException, valid_nonpersonal_net_id, 'canvas')

    def test_valid_canvas_user_id(self):
        self.assertEquals(valid_canvas_user_id(12345), None)
        self.assertEquals(valid_canvas_user_id('12345'), None)
        self.assertEquals(valid_canvas_user_id(0), None)
        self.assertEquals(valid_canvas_user_id(1111111111), None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, 'abc')
        self.assertRaises(UserPolicyException, valid_canvas_user_id, '1234z')


class RegidPolicyTest(TestCase):
    def test_get_person_by_regid(self):
        with self.settings(
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            user = get_person_by_regid('9136CCB8F66711D5BE060004AC494FFE')
            self.assertEquals(user.uwregid, '9136CCB8F66711D5BE060004AC494FFE')

    def test_valid_regid(self):
        # Valid
        self.assertEquals(valid_reg_id('9136CCB8F66711D5BE060004AC494FFE'), None)

        # Invalid
        self.assertRaises(InvalidLoginIdException, valid_reg_id, '9136CCB8F66711D5BE060004AC494FF')
        self.assertRaises(InvalidLoginIdException, valid_reg_id, '9136CCB8F66711D5BE060004AC494FFEE')
        self.assertRaises(InvalidLoginIdException, valid_reg_id, 'javerage')
        self.assertRaises(UserPolicyException, valid_reg_id, 'javerage')


class GmailPolicyTest(TestCase):
    valid_domains = ['gmail.com', 'google.com', 'googlemail.com']
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

    def test_get_person_by_gmail_id(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

            default_user = "johnsmith@gmail.com"

            for user in self.valid_users:
                self.assertEquals(get_person_by_gmail_id(user).sis_user_id, default_user)

            for user in self.invalid_users:
                self.assertRaises(UserPolicyException, get_person_by_gmail_id, user)

    def test_valid_domains(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

            default_user = "johnsmith"

            invalid_domains = [
                "abc.com"
                    "",
            ]

            for domain in self.valid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertEquals(valid_gmail_id(user), user, "Valid user: %s" % user)

            for domain in invalid_domains:
                user = "%s@%s" % (default_user, domain)
                self.assertRaises(InvalidLoginIdException, valid_gmail_id, user)

    def test_valid_user(self):
        with self.settings(
                LOGIN_DOMAIN_WHITELIST=self.valid_domains):

            default_user = "johnsmith@gmail.com"

            self.assertEquals(valid_gmail_id(default_user), default_user, "Default user is not changed")

            for user in self.valid_users:
                self.assertEquals(valid_gmail_id(user), default_user, "Valid user: %s" % user)

            for user in self.invalid_users:
                self.assertRaises(UserPolicyException, valid_gmail_id, user)

        with self.settings(LOGIN_DOMAIN_WHITELIST = []):
            self.assertRaises(UserPolicyException, valid_gmail_id, user)
