# Copyright 2023 UW-IT, University of Washington
# SPDX-License-Identifier: Apache-2.0


from django.test import TestCase, override_settings
from uw_pws import PWS
from uw_pws.util import fdao_pws_override
from uw_gws.utilities import fdao_gws_override
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.user import *
from sis_provisioner.exceptions import (
    UserPolicyException, MissingLoginIdException, InvalidLoginIdException,
    TemporaryNetidException)


class InvalidPerson(object):
    pass


@fdao_pws_override
@fdao_gws_override
class IsGroupMemberTest(TestCase):
    def test_is_group_member(self):
        self.assertEquals(
            is_group_member('u_acadev_unittest', 'javerage'), True)
        self.assertEquals(
            is_group_member('u_acadev_unittest', 'eight'), True)
        self.assertEquals(
            is_group_member('u_acadev_unittest', 'baverage'), False)
        self.assertEquals(
            is_group_member('u_acadev_unittest', 'joe@gmail.com'), False)


@fdao_pws_override
@fdao_gws_override
class IsGroupAdminTest(TestCase):
    def test_is_group_admin(self):
        self.assertEquals(
            is_group_admin('u_acadev_unittest', 'javerage'), True)
        self.assertEquals(
            is_group_admin('u_acadev_unittest', 'eight'), False)
        self.assertEquals(
            is_group_admin('u_acadev_unittest', 'baverage'), False)
        self.assertEquals(
            is_group_admin('u_acadev_unittest', 'joe@gmail.com'), False)


@fdao_pws_override
@fdao_gws_override
class UserPolicyTest(TestCase):
    @override_settings(ALLOWED_CANVAS_LOGIN_USERS='u_acadev_unittest')
    def test_can_access_canvas(self):
        self.assertEqual(can_access_canvas('javerage'), True)
        self.assertEqual(can_access_canvas('joe@gmail.com'), True)
        self.assertRaisesRegex(UserPolicyException, "UWNetID not permitted$",
                               can_access_canvas, 'baverage')

    def test_valid_canvas_user_id(self):
        self.assertEquals(valid_canvas_user_id(12345), None)
        self.assertEquals(valid_canvas_user_id('12345'), None)
        self.assertEquals(valid_canvas_user_id(0), None)
        self.assertEquals(valid_canvas_user_id(1111111111), None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, 'abc')
        self.assertRaises(UserPolicyException, valid_canvas_user_id, '1234z')

    @override_settings(ALLOWED_LOGIN_DOMAINS=['gmail.com'])
    def test_user_sis_id(self):
        user = PWS().get_person_by_netid('javerage')
        self.assertEquals(
            user_sis_id(user), '9136CCB8F66711D5BE060004AC494FFE')

        user = get_person_by_gmail_id('john.smith@gmail.com')
        self.assertEquals(user_sis_id(user), 'johnsmith@gmail.com')

    @override_settings(ALLOWED_LOGIN_DOMAINS=['gmail.com'])
    def test_user_email(self):
        user = PWS().get_person_by_netid('javerage')
        self.assertEquals(user_email(user), 'javerage@uw.edu')

        # non-personal netid
        user = PWS().get_entity_by_netid('somalt')
        self.assertEquals(user_email(user), 'somalt@uw.edu')

        user = get_person_by_gmail_id('john.smith@gmail.com')
        self.assertEquals(user_email(user), 'john.smith@gmail.com')

        user = PWS().get_entity_by_netid('somalt')
        user.uwnetid = None
        self.assertRaises(UserPolicyException, user_email, user)

        user = InvalidPerson()
        self.assertRaises(UserPolicyException, user_email, user)

    @override_settings(ALLOWED_LOGIN_DOMAINS=['gmail.com'])
    def test_user_fullname(self):
        user = PWS().get_person_by_netid('javerage')
        name = user_fullname(user)
        self.assertEquals(len(name), 2)
        self.assertEquals(name[0], 'Jamesy')
        self.assertEquals(name[1], 'McJamesy')

        user = PWS().get_person_by_regid('8BD26A286A7D11D5A4AE0004AC494FFE')
        name = user_fullname(user)
        self.assertEquals(len(name), 2)
        self.assertEquals(name[0], 'BILL AVERAGE')
        self.assertEquals(name[1], 'TEACHER')

        # non-personal netid
        user = PWS().get_entity_by_netid('somalt')
        name = user_fullname(user)
        self.assertEquals(len(name), 1)
        self.assertEquals(name[0], user.display_name)

        user = get_person_by_gmail_id('john.smith@gmail.com')
        name = user_fullname(user)
        self.assertEquals(len(name), 1)
        self.assertEquals(name[0], 'john.smith')

        user = InvalidPerson()
        self.assertRaises(UserPolicyException, user_fullname, user)


@fdao_pws_override
@fdao_gws_override
class NetidPolicyTest(TestCase):
    @override_settings(NONPERSONAL_NETID_EXCEPTION_GROUP='u_acadev_unittest')
    def test_get_person_by_netid(self):
        self.assertEquals(get_person_by_netid('javerage').uwnetid, 'javerage')
        self.assertRaises(
            DataFailureException, get_person_by_netid, 'a_canvas_application')
        self.assertRaises(
            InvalidLoginIdException, get_person_by_netid, 'canvas')

    @override_settings(NONPERSONAL_NETID_EXCEPTION_GROUP=None)
    def test_get_test_entity_by_netid(self):
        self.assertRaises(
            InvalidLoginIdException, get_person_by_netid, 'javerage')

    def test_valid_netid(self):
        # Valid
        self.assertEquals(valid_net_id('javerage'), None)
        self.assertEquals(valid_net_id('sadm_javerage'), None)
        self.assertEquals(valid_net_id('a_canvas_application'), None)
        self.assertEquals(valid_net_id('j1234567890'), None)
        self.assertEquals(valid_net_id('css1234'), None)

        # Invalid
        self.assertRaises(MissingLoginIdException, valid_net_id, None)
        self.assertRaises(MissingLoginIdException, valid_net_id, '')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'wire12345')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'event1234')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'lib12345')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'lawlib1234')
        self.assertRaises(TemporaryNetidException, valid_net_id, 'uwctc1234')
        self.assertRaises(InvalidLoginIdException, valid_net_id, '1abcdef')

    def test_valid_admin_netid(self):
        # Valid
        self.assertEquals(valid_admin_net_id('sadm_javerage'), None)
        self.assertEquals(valid_admin_net_id('wadm_javerage'), None)

        # Invalid
        self.assertRaises(
            InvalidLoginIdException, valid_admin_net_id, 'javerage')

    def test_valid_application_netid(self):
        # Valid
        self.assertEquals(
            valid_application_net_id('a_canvas_application'), None)

        # Invalid
        self.assertRaises(
            UserPolicyException, valid_application_net_id, 'javerage')

    @override_settings(NONPERSONAL_NETID_EXCEPTION_GROUP='u_acadev_unittest')
    def test_nonpersonal_netid(self):
        # Valid
        self.assertEquals(
            valid_nonpersonal_net_id('a_canvas_application'), None)
        self.assertEquals(valid_nonpersonal_net_id('wadm_javerage'), None)
        self.assertEquals(valid_nonpersonal_net_id('javerage'), None)

        # Invalid
        self.assertRaises(
            InvalidLoginIdException, valid_nonpersonal_net_id, 'canvas')

    @override_settings(NONPERSONAL_NETID_EXCEPTION_GROUP='')
    def test_nonpersonal_netid_no_group(self):
        self.assertRaises(
            InvalidLoginIdException, valid_nonpersonal_net_id, 'canvas')

    def test_valid_canvas_user_id(self):
        self.assertEquals(valid_canvas_user_id(12345), None)
        self.assertEquals(valid_canvas_user_id('12345'), None)
        self.assertEquals(valid_canvas_user_id(0), None)
        self.assertEquals(valid_canvas_user_id(1111111111), None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, None)
        self.assertRaises(UserPolicyException, valid_canvas_user_id, 'abc')
        self.assertRaises(UserPolicyException, valid_canvas_user_id, '1234z')


@fdao_pws_override
@fdao_gws_override
class RegidPolicyTest(TestCase):
    @override_settings(NONPERSONAL_NETID_EXCEPTION_GROUP='u_acadev_unittest')
    def test_get_person_by_regid(self):
        user = get_person_by_regid('9136CCB8F66711D5BE060004AC494FFE')
        self.assertEquals(user.uwregid, '9136CCB8F66711D5BE060004AC494FFE')

        self.assertRaises(
            DataFailureException, get_person_by_regid,
            '9136CCB8F66711D5BE060004AC494FFF')

    @override_settings(NONPERSONAL_NETID_EXCEPTION_GROUP=None)
    def test_get_test_entity_by_regid(self):
        self.assertRaises(
            UserPolicyException, get_person_by_regid,
            '9136CCB8F66711D5BE060004AC494FFE')

    def test_valid_regid(self):
        # Valid
        self.assertEquals(
            valid_reg_id('9136CCB8F66711D5BE060004AC494FFE'), None)

        # Invalid
        self.assertRaises(
            InvalidLoginIdException, valid_reg_id,
            '9136CCB8F66711D5BE060004AC494FF')
        self.assertRaises(
            InvalidLoginIdException, valid_reg_id,
            '9136CCB8F66711D5BE060004AC494FFEE')
        self.assertRaises(InvalidLoginIdException, valid_reg_id, 'javerage')
        self.assertRaises(UserPolicyException, valid_reg_id, 'javerage')


@fdao_pws_override
@fdao_gws_override
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

    @override_settings(ALLOWED_LOGIN_DOMAINS=valid_domains)
    def test_get_person_by_gmail_id(self):
        default_user = "johnsmith@gmail.com"

        for user in self.valid_users:
            self.assertEquals(
                get_person_by_gmail_id(user).sis_user_id, default_user)

        for user in self.invalid_users:
            self.assertRaises(
                UserPolicyException, get_person_by_gmail_id, user)

    @override_settings(ALLOWED_LOGIN_DOMAINS=valid_domains)
    def test_valid_domains(self):
        default_user = "johnsmith"

        invalid_domains = [
            "abc.com"
            "",
        ]

        for domain in self.valid_domains:
            user = "%s@%s" % (default_user, domain)
            self.assertEquals(
                valid_gmail_id(user), user, "Valid user: {}".format(user))

        for domain in invalid_domains:
            user = "%s@%s" % (default_user, domain)
            self.assertRaises(
                InvalidLoginIdException, valid_gmail_id, user)

    @override_settings(ALLOWED_LOGIN_DOMAINS=valid_domains)
    def test_valid_user(self):
        default_user = "johnsmith@gmail.com"

        self.assertEquals(
            valid_gmail_id(default_user), default_user,
            "Default user is not changed")

        for user in self.valid_users:
            self.assertEquals(
                valid_gmail_id(user), default_user,
                "Valid user: {}".format(user))

        for user in self.invalid_users:
            self.assertRaises(UserPolicyException, valid_gmail_id, user)

    @override_settings(ALLOWED_LOGIN_DOMAINS=[])
    def test_valid_user_no_domains(self):
        for user in self.valid_users:
            self.assertRaises(UserPolicyException, valid_gmail_id, user)
