from django.test import TestCase
from django.conf import settings
from restclients_core.exceptions import DataFailureException
from sis_provisioner.dao.group import *
from sis_provisioner.exceptions import (
    GroupPolicyException, GroupNotFoundException)
from datetime import datetime, timedelta
from uw_gws.utilities import fdao_gws_override
from uw_pws.util import fdao_pws_override


@fdao_gws_override
@fdao_pws_override
class GroupPolicyTest(TestCase):
    def test_valid_group(self):
        with self.settings(UW_GROUP_BLACKLIST=['uw_student', 'uw_staff']):
            # Valid
            self.assertEquals(valid_group_id('u_javerage_test'), None)
            self.assertEquals(valid_group_id('uw_faculty'), None)

            # Invalid
            self.assertRaises(GroupPolicyException, valid_group_id, None)
            self.assertRaises(GroupPolicyException, valid_group_id, '')
            self.assertRaises(GroupPolicyException, valid_group_id, '1')
            self.assertRaises(GroupPolicyException, valid_group_id, 'uw_student')
            self.assertRaises(GroupPolicyException, valid_group_id, 'uw_staff')


@fdao_gws_override
@fdao_pws_override
class GroupModifiedTest(TestCase):
    def test_modified_group(self):
        mtime = datetime.now()
        self.assertEquals(is_modified_group('u_does_not_exist', mtime), True)

        mtime = datetime(2000, 10, 10, 0, 0, 0)
        self.assertEquals(is_modified_group('u_acadev_tester', mtime), True)

        mtime = datetime(2020, 10, 10, 0, 0, 0)
        self.assertEquals(is_modified_group('u_acadev_tester', mtime), False)


@fdao_gws_override
@fdao_pws_override
class SISImportMembersTest(TestCase):
    def test_sis_import_members(self):
        with self.settings(
                SIS_IMPORT_GROUPS=['u_acadev_unittest', 'u_acadev_tester']):

            members = get_sis_import_members()

            self.assertEquals(len(members), 5)

        with self.settings(SIS_IMPORT_GROUPS=['u_does_not_exist']):
            self.assertRaises(DataFailureException, get_sis_import_members)


@fdao_gws_override
@fdao_pws_override
class EffectiveMemberTest(TestCase):
    def test_effective_members(self):
        with self.settings(UW_GROUP_BLACKLIST=['uw_student', 'uw_staff']):
            (valid_members, invalid_members, member_groups) = get_effective_members('u_acadev_unittest')

            self.assertEquals(len(valid_members), 2)
            self.assertEquals(len(invalid_members), 0)
            self.assertEquals(len(member_groups), 0)

            (valid_members, invalid_members, member_groups) = get_effective_members('u_acadev_unittest', 'javerage')  # Using act_as

            self.assertEquals(len(valid_members), 2)
            self.assertEquals(len(invalid_members), 0)
            self.assertEquals(len(member_groups), 0)

            self.assertRaises(GroupNotFoundException, get_effective_members, 'u_acadev_fake')
