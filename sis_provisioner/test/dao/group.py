from django.test import TestCase
from django.conf import settings
from restclients.exceptions import DataFailureException
from sis_provisioner.dao.group import * 
from sis_provisioner.exceptions import GroupPolicyException,\
    GroupNotFoundException
from datetime import datetime, timedelta


class GroupPolicyTest(TestCase):
    def test_valid_group(self):
        with self.settings(
                UW_GROUP_BLACKLIST=['uw_student', 'uw_staff']):

            # Valid
            self.assertEquals(valid_group_id('u_javerage_test'), None)
            self.assertEquals(valid_group_id('uw_faculty'), None)

            # Invalid
            self.assertRaises(GroupPolicyException, valid_group_id, None)
            self.assertRaises(GroupPolicyException, valid_group_id, '')
            self.assertRaises(GroupPolicyException, valid_group_id, 12345)
            self.assertRaises(GroupPolicyException, valid_group_id, '1')
            self.assertRaises(GroupPolicyException, valid_group_id, 'uw_student')
            self.assertRaises(GroupPolicyException, valid_group_id, 'uw_staff')


class GroupModifiedTest(TestCase):
    def test_modified_group(self):
        with self.settings(
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            mtime = datetime.now()
            self.assertEquals(is_modified_group('u_does_not_exist', mtime), True)

            mtime = datetime(2000, 10, 10, 0, 0, 0)
            self.assertEquals(is_modified_group('u_acadev_tester', mtime), True)

            mtime = datetime(2020, 10, 10, 0, 0, 0)
            self.assertEquals(is_modified_group('u_acadev_tester', mtime), False)


class SISImportMembersTest(TestCase):
    def test_sis_import_members(self):
        with self.settings(
                SIS_IMPORT_GROUPS=['u_acadev_unittest', 'u_acadev_tester'],
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            members = get_sis_import_members()

            self.assertEquals(len(members), 5)

        with self.settings(
                SIS_IMPORT_GROUPS=['u_does_not_exist'],
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            self.assertRaises(DataFailureException, get_sis_import_members)


class IsMemberTest(TestCase):
    def test_is_member(self):
        with self.settings(
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            self.assertEquals(is_member('u_acadev_unittest', 'javerage'), True)
            self.assertEquals(is_member('u_acadev_unittest', 'eight'), True)
            self.assertEquals(is_member('u_acadev_unittest', 'baverage'), False)
            self.assertEquals(is_member('u_acadev_unittest', 'joe@gmail.com'), False)


class EffectiveMemberTest(TestCase):
    def test_effective_members(self):
        with self.settings(
                UW_GROUP_BLACKLIST=['uw_student', 'uw_staff'],
                RESTCLIENTS_GWS_DAO_CLASS='restclients.dao_implementation.gws.File',
                RESTCLIENTS_PWS_DAO_CLASS='restclients.dao_implementation.pws.File'):

            (valid_members, invalid_members, member_groups) = get_effective_members('u_acadev_unittest')

            self.assertEquals(len(valid_members), 2)
            self.assertEquals(len(invalid_members), 0)
            self.assertEquals(len(member_groups), 0)

            (valid_members, invalid_members, member_groups) = get_effective_members('u_acadev_unittest', 'javerage')  # Using act_as

            self.assertEquals(len(valid_members), 2)
            self.assertEquals(len(invalid_members), 0)
            self.assertEquals(len(member_groups), 0)

            self.assertRaises(GroupNotFoundException, get_effective_members, 'u_acadev_fake')
